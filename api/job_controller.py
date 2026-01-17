"""
Job management API for AutoClipper.
Triggers Gumloop workflows and tracks job state.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import uuid
import requests
from datetime import datetime

from status_store import StatusStore


app = FastAPI(title="AutoClipper API")
status_store = StatusStore()


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
    progress: Optional[str] = None
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
        video_url=str(request.video_url),
        webhook_url=str(request.webhook_url) if request.webhook_url else None
    )
    
    # Trigger Gumloop workflow
    try:
        # Replace with actual Gumloop API endpoint
        gumloop_response = requests.post(
            "https://api.gumloop.com/v1/workflows/{workflow_id}/trigger",
            json={
                "job_id": job_id,
                "video_url": str(request.video_url)
            },
            headers={
                "Authorization": "Bearer {GUMLOOP_API_KEY}"
            }
        )
        gumloop_response.raise_for_status()
        
        status_store.update_job(job_id, status="processing", progress="url_validation")
        
    except Exception as e:
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
    
    return JobStatusResponse(**job)


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
        clips=clips,
        error=error
    )
    
    # Trigger user webhook if configured
    job = status_store.get_job(job_id)
    if job.get("webhook_url") and status in ["completed", "failed"]:
        try:
            requests.post(job["webhook_url"], json=job)
        except:
            pass
    
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
