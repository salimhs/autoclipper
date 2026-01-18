"""
Job management API for AutoClipper.
Triggers Gumloop workflows and tracks job state.
"""

import os
import uuid
import requests
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from status_store import StatusStore

# Load environment variables
load_dotenv()

app = FastAPI(title="AutoClipper API")
status_store = StatusStore()

# Allow the frontend to call the API in hackathon/dev setups.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateJobRequest(BaseModel):
    video_url: HttpUrl
    webhook_url: Optional[HttpUrl] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    video_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    clips: Optional[list] = None
    error: Optional[str] = None


@app.post("/jobs", response_model=JobResponse)
async def create_job(request: CreateJobRequest):
    """
    Create new video processing job.
    Triggers Gumloop workflow.
    """
    job_id = str(uuid.uuid4())
    
    # Store initial job state
    status_store.create_job(
        job_id=job_id,
        payload={
            "video_url": str(request.video_url),
            "webhook_url": str(request.webhook_url) if request.webhook_url else None
        }
    )
    
    # Trigger Gumloop workflow
    try:
        workflow_id = os.getenv("GUMLOOP_WORKFLOW_ID")
        api_key = os.getenv("GUMLOOP_API_KEY")
        user_id = os.getenv("GUMLOOP_USER_ID")
        
        if not all([workflow_id, api_key, user_id]):
            raise ValueError("GUMLOOP_WORKFLOW_ID, GUMLOOP_API_KEY, or GUMLOOP_USER_ID not set in .env")

        # Use query parameters as seen in the user's provided trigger URL
        trigger_url = (
            f"https://api.gumloop.com/api/v1/start_pipeline"
            f"?api_key={api_key}"
            f"&user_id={user_id}"
            f"&saved_item_id={workflow_id}"
        )

        gumloop_response = requests.post(
            trigger_url,
            json={
                "video_url": str(request.video_url),
                "job_id": job_id
            },
            headers={
                "Content-Type": "application/json"
            },
            timeout=30
        )
        gumloop_response.raise_for_status()
        
        status_store.update_job(job_id, status="processing", progress=0.1)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error triggering Gumloop: {e}")
        status_store.update_job(job_id, status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {e}")
    
    return JobResponse(
        job_id=job_id,
        status="processing",
        created_at=datetime.utcnow().isoformat(),
        video_url=str(request.video_url)
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get current status of a job."""
    job = status_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Convert JobRecord to dict properly
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        clips=job.result.get("clips"),
        error=job.error
    )


@app.post("/webhooks/gumloop/{job_id}")
async def gumloop_webhook(job_id: str, payload: Dict[str, Any]):
    """
    Webhook endpoint for Gumloop to report progress and results.
    """
    status = payload.get("status")
    progress = payload.get("progress")
    clips = payload.get("clips")
    error = payload.get("error")
    
    status_store.update_job(
        job_id=job_id,
        status=status,
        progress=progress,
        result={"clips": clips} if clips else {},
        error=error
    )
    
    # Trigger user webhook if configured
    job = status_store.get_job(job_id)
    if job and job.payload.get("webhook_url") and status in ["completed", "failed"]:
        try:
            requests.post(job.payload["webhook_url"], json=status_store.as_dict(job))
        except:
            pass
    
    return {"status": "ok"}


# Serve the lightweight dashboard UI (static) from /.
# Moved to bottom to avoid intercepting /jobs routes
app.mount(
    "/",
    StaticFiles(directory="api/static", html=True),
    name="static",
)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
