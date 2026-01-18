"""
GPU render worker API.
Stateless service for rendering clips from render recipes.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import os
from pathlib import Path
import tempfile
import asyncio
from concurrent.futures import ProcessPoolExecutor

from ffmpeg_templates import FFmpegRenderer


app = FastAPI(title="AutoClipper Render Worker")

# In-memory job store (replace with Redis in production)
job_store: Dict[str, Dict[str, Any]] = {}

executor = ProcessPoolExecutor(max_workers=4)


class RenderRecipe(BaseModel):
    video_uri: str
    clips: List[Dict[str, Any]]


class RenderRequest(BaseModel):
    render_recipe: RenderRecipe
    job_id: str


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
    Create a new render job based on a recipe.
    Matches Gumloop Node #12 expectation.
    """
    # Use provided job_id or generate one
    job_id = request.job_id
    
    job_store[job_id] = {
        "status": "pending",
        "recipe": request.render_recipe.dict(),
        "clips": [],
        "progress": 0.0
    }
    
    # Start async rendering
    asyncio.create_task(process_render_job(job_id, request.render_recipe))
    
    # Use environment variable for base URL (supports production deployment)
    base_url = os.environ.get("RENDER_WORKER_URL", "http://localhost:8000")
    
    return {
        "render_task_id": job_id,
        "status_url": f"{base_url.rstrip('/')}/status/{job_id}"
    }


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


async def process_render_job(job_id: str, recipe: RenderRecipe):
    """Process render job asynchronously."""
    from utils.output_manager import OutputManager
    
    job = job_store[job_id]
    job["status"] = "processing"
    
    try:
        total_clips = len(recipe.clips)
        rendered_clips = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, clip_data in enumerate(recipe.clips):
                # Render single clip
                output_path = Path(temp_dir) / f"{clip_data['clip_id']}.mp4"
                
                loop = asyncio.get_event_loop()
                video_path = recipe.video_uri.replace("file://", "")
                await loop.run_in_executor(
                    executor,
                    FFmpegRenderer.render_clip,
                    video_path,
                    str(output_path),
                    clip_data['start_sec'],
                    clip_data['end_sec'],
                    clip_data.get('crop_paths', []), # Use crop_paths from recipe
                    clip_data.get('words', []),      # Use words from recipe
                    temp_dir
                )
                
                # Temporary result
                rendered_clips.append({
                    "clip_id": clip_data['clip_id'],
                    "mp4_url": f"file://{output_path}",
                    "score": clip_data.get('score', 0.0)
                })
                
                job["progress"] = (i + 1) / total_clips
            
            # Save to permanent storage using OutputManager
            output_mgr = OutputManager()
            saved_results = output_mgr.save_job_results(
                job_id=job_id,
                video_url=recipe.video_uri,
                clips=rendered_clips,
                metadata={
                    "total_clips": len(rendered_clips),
                    "render_timestamp": str(asyncio.get_event_loop().time())
                }
            )
            
            # Update job with permanent paths
            job["clips"] = saved_results["clips"]
            job["job_dir"] = saved_results["job_dir"]
            job["manifest_path"] = saved_results["manifest_path"]
        
        job["status"] = "completed"
        job["progress"] = 1.0
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job["status"] = "failed"
        job["error"] = str(e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
