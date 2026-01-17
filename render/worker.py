"""
GPU render worker API.
Stateless service for rendering clips from render recipes.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
from pathlib import Path
import tempfile
import asyncio
from concurrent.futures import ProcessPoolExecutor

from ffmpeg_templates import FFmpegRenderer


app = FastAPI(title="AutoClipper Render Worker")

# In-memory job store (replace with Redis in production)
job_store: Dict[str, Dict[str, Any]] = {}

executor = ProcessPoolExecutor(max_workers=4)


class RenderRequest(BaseModel):
    video_uri: str
    clips: List[Dict[str, Any]]


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[float] = None
    error: Optional[str] = None


class RenderResult(BaseModel):
    job_id: str
    clips: List[Dict[str, Any]]


@app.post("/render", response_model=Dict[str, str])
async def create_render_job(request: RenderRequest):
    """
    Create a new render job.
    
    Returns:
        {"job_id": "..."}
    """
    job_id = str(uuid.uuid4())
    
    job_store[job_id] = {
        "status": "pending",
        "request": request.dict(),
        "clips": [],
        "progress": 0.0
    }
    
    # Start async rendering
    asyncio.create_task(process_render_job(job_id, request))
    
    return {"job_id": job_id}


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a render job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress"),
        error=job.get("error")
    )


@app.get("/result/{job_id}", response_model=RenderResult)
async def get_job_result(job_id: str):
    """Get results of a completed render job."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {job['status']}")
    
    return RenderResult(
        job_id=job_id,
        clips=job["clips"]
    )


async def process_render_job(job_id: str, request: RenderRequest):
    """Process render job asynchronously."""
    job = job_store[job_id]
    job["status"] = "processing"
    
    try:
        total_clips = len(request.clips)
        rendered_clips = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, clip_data in enumerate(request.clips):
                # Render single clip
                output_path = Path(temp_dir) / f"{clip_data['clip_id']}.mp4"
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    executor,
                    FFmpegRenderer.render_clip,
                    request.video_uri,
                    str(output_path),
                    clip_data['start_sec'],
                    clip_data['end_sec'],
                    clip_data['crop_path'],
                    clip_data['subtitles'],
                    temp_dir
                )
                
                # In production: upload to storage and return URI
                # For now, return local path
                rendered_clips.append({
                    "clip_id": clip_data['clip_id'],
                    "mp4_url": str(output_path),
                    "score": clip_data.get('score', 0.0)
                })
                
                job["progress"] = (i + 1) / total_clips
        
        job["status"] = "completed"
        job["clips"] = rendered_clips
        job["progress"] = 1.0
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
