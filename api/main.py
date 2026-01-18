"""
Unified API Entry Point for AutoClipper.
Combines job management (/jobs) and Gumloop gateway (/api) endpoints.
"""

import os
import uuid
import json
import tempfile
import subprocess
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from fractions import Fraction

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.status_store import StatusStore
from ai.llm_provider import get_provider
from utils.logger import StructuredLogger
from utils.cache import CacheManager
from utils.retry import retry_with_backoff

# Load environment variables
load_dotenv()

# Environment configuration
LLM_TOKEN_THRESHOLD = int(os.getenv("LLM_TOKEN_THRESHOLD", "80000"))
RENDER_WORKER_URL = os.getenv("RENDER_WORKER_URL", "http://localhost:8000")

app = FastAPI(title="AutoClipper Unified API", version="2.0.0")
status_store = StatusStore()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models - Job Management
# ============================================================================

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


# ============================================================================
# Pydantic Models - Gumloop Gateway Endpoints
# ============================================================================

class DownloadRequest(BaseModel):
    video_url: str
    job_id: str

class DownloadResponse(BaseModel):
    video_uri: str
    audio_uri: str
    duration_sec: float
    fps: float
    width: int
    height: int


class TranscribeRequest(BaseModel):
    audio_uri: str
    video_url: str
    duration_sec: float
    job_id: str

class TranscribeResponse(BaseModel):
    transcript_uri: str
    word_timeline_uri: str
    confidence: float  # Changed from confidence_average


class TrackingRequest(BaseModel):
    video_uri: str
    video_url: str
    width: int
    height: int
    job_id: str

class TrackingResponse(BaseModel):
    tracking_uri: str
    crop_paths_uri: str


class ClipSelectionRequest(BaseModel):
    transcript: Dict[str, Any]
    duration_sec: float
    strategy: Optional[str] = None  # Made optional for auto-detection
    job_id: str

class ClipSelectionResponse(BaseModel):
    raw_edl_json: str  # Changed from edl: Dict - return JSON string


class RepairRequest(BaseModel):
    raw_edl_json: str
    validation_error: str
    duration_sec: float
    repair_strategy: str
    job_id: str

class RepairResponse(BaseModel):
    repaired_edl_json: str


class ValidateEDLRequest(BaseModel):
    edl_json: str  # JSON string of EDL
    duration_sec: float
    job_id: str

class ValidateEDLResponse(BaseModel):
    valid: bool
    errors: List[str]
    edl: Optional[Dict[str, Any]] = None  # Parsed and validated EDL if valid


class MergeRecipeRequest(BaseModel):
    edl_json: str  # JSON string or dict
    word_timeline_uri: str
    crop_paths_uri: str
    video_uri: str
    job_id: str

class MergeRecipeResponse(BaseModel):
    render_recipe_uri: str


# ============================================================================
# Helper Functions
# ============================================================================

def estimate_token_count(text: str) -> int:
    """Rough token estimation: ~4 chars per token"""
    return len(text) // 4


def select_llm_strategy(transcript: Dict[str, Any], threshold: int = None) -> str:
    """Route to gumloop_llm if under threshold, else gemini_fallback"""
    if threshold is None:
        threshold = LLM_TOKEN_THRESHOLD
    
    full_text = " ".join(
        segment.get("text", "")
        for segment in transcript.get("segments", [])
    )
    token_count = estimate_token_count(full_text)
    
    if token_count < threshold:
        return "gumloop_llm"
    else:
        return "gemini_fallback"


# ============================================================================
# Job Management Endpoints
# ============================================================================

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


# ============================================================================
# Gumloop Gateway Endpoints
# ============================================================================

@app.post("/api/download", response_model=DownloadResponse)
@retry_with_backoff(max_retries=3)
async def download_video(request: DownloadRequest):
    """Download video and extract audio using yt-dlp and ffmpeg."""
    logger = StructuredLogger(request.job_id, "download")
    logger.info("Starting download", url=request.video_url)
    
    temp_dir = tempfile.mkdtemp(prefix=f"autoclipper_{request.job_id}_")
    
    try:
        # Download with yt-dlp
        video_path = f"{temp_dir}/video.mp4"
        subprocess.run([
            'yt-dlp',
            '-f', 'best[ext=mp4]',
            '-o', video_path,
            request.video_url
        ], check=True, capture_output=True)
        
        # Extract audio with ffmpeg
        audio_path = f"{temp_dir}/audio.wav"
        subprocess.run([
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            audio_path
        ], check=True, capture_output=True)
        
        # Get metadata with ffprobe
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ], check=True, capture_output=True, text=True)
        
        metadata = json.loads(result.stdout)
        video_stream = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
        
        logger.info("Download complete", video_path=video_path)
        
        return DownloadResponse(
            video_uri=f"file://{video_path}",
            audio_uri=f"file://{audio_path}",
            duration_sec=float(metadata['format']['duration']),
            fps=float(Fraction(video_stream['r_frame_rate'])),
            width=int(video_stream['width']),
            height=int(video_stream['height'])
        )
        
    except Exception as e:
        logger.error("Download failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """Transcribe audio using WhisperX with caching."""
    logger = StructuredLogger(request.job_id, "transcribe")
    cache = CacheManager()
    
    # Check cache first
    cached = cache.get_transcript(request.video_url, request.duration_sec)
    if cached:
        logger.info("Using cached transcript")
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{request.job_id}_transcript_")
        transcript_path = f"{output_dir}/transcript.json"
        
        with open(transcript_path, 'w') as f:
            json.dump(cached, f)
        
        return TranscribeResponse(
            transcript_uri=f"file://{transcript_path}",
            word_timeline_uri=f"file://{transcript_path}",
            confidence=1.0
        )
    
    # Heavy ML import
    try:
        from perception.whisperx_runner import WhisperXRunner
    except ImportError:
        logger.error("WhisperX not installed. This endpoint requires the full ML environment.")
        raise HTTPException(status_code=501, detail="Transcription service not available on this deployment. Requires full ML environment.")

    audio_path = request.audio_uri.replace("file://", "")
    runner = WhisperXRunner()
    
    try:
        transcript = runner.transcribe(audio_path)
        
        # Calculate average confidence
        confidences = []
        for segment in transcript.get("segments", []):
            for word in segment.get("words", []):
                if "score" in word:
                    confidences.append(word["score"])
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Cache result
        cache.set_transcript(request.video_url, request.duration_sec, transcript)
        
        # Save to file
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{request.job_id}_transcript_")
        transcript_path = f"{output_dir}/transcript.json"
        
        with open(transcript_path, 'w') as f:
            json.dump(transcript, f)
        
        logger.info("Transcription complete", avg_confidence=avg_confidence)
        
        return TranscribeResponse(
            transcript_uri=f"file://{transcript_path}",
            word_timeline_uri=f"file://{transcript_path}",
            confidence=avg_confidence
        )
        
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/track", response_model=TrackingResponse)
async def track_video(request: TrackingRequest):
    """Track faces and generate crop paths using MediaPipe."""
    logger = StructuredLogger(request.job_id, "track")
    cache = CacheManager()
    
    # Check cache
    cache_key = request.width * request.height
    cached = cache.get_tracking(request.video_url, cache_key)
    if cached:
        logger.info("Using cached tracking data")
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{request.job_id}_tracking_")
        tracking_path = f"{output_dir}/tracking.json"
        crop_paths_path = f"{output_dir}/crop_paths.json"
        
        with open(tracking_path, 'w') as f:
            json.dump(cached["tracking"], f)
        with open(crop_paths_path, 'w') as f:
            json.dump(cached["crop_paths"], f)
        
        return TrackingResponse(
            tracking_uri=f"file://{tracking_path}",
            crop_paths_uri=f"file://{crop_paths_path}"
        )
    
    # Heavy ML import
    try:
        from perception.tracking import VisualTracker
    except ImportError:
        logger.error("MediaPipe not installed. This endpoint requires the full ML environment.")
        raise HTTPException(status_code=501, detail="Tracking service not available on this deployment. Requires full ML environment.")

    # Track with MediaPipe
    video_path = request.video_uri.replace("file://", "")
    tracker = VisualTracker()
    
    try:
        tracking_data = tracker.track_video(video_path)
        crop_paths = tracker.generate_crop_paths(
            tracking_data,
            source_width=request.width,
            source_height=request.height
        )
        
        # Cache combined data
        cache_data = {
            "tracking": tracking_data,
            "crop_paths": {"crop_path": crop_paths}
        }
        cache.set_tracking(request.video_url, cache_key, cache_data)
        
        # Save to files
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{request.job_id}_tracking_")
        tracking_path = f"{output_dir}/tracking.json"
        crop_paths_path = f"{output_dir}/crop_paths.json"
        
        with open(tracking_path, 'w') as f:
            json.dump(tracking_data, f)
        with open(crop_paths_path, 'w') as f:
            json.dump({"crop_path": crop_paths}, f)
        
        logger.info("Tracking complete", keyframes=len(crop_paths))
        
        return TrackingResponse(
            tracking_uri=f"file://{tracking_path}",
            crop_paths_uri=f"file://{crop_paths_path}"
        )
        
    except Exception as e:
        logger.error("Tracking failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/select-clips", response_model=ClipSelectionResponse)
async def select_clips(request: ClipSelectionRequest):
    """Select viral clips using LLM (Gumloop or Gemini)."""
    logger = StructuredLogger(request.job_id, "select_clips")
    
    # Auto-detect strategy if not provided
    strategy = request.strategy
    if strategy is None:
        strategy = select_llm_strategy(request.transcript)
        logger.info("Auto-selected LLM strategy", strategy=strategy)
    
    try:
        # Get appropriate provider
        provider = get_provider(strategy)
        
        # If gumloop_llm, raise helpful error
        if strategy == "gumloop_llm":
            raise NotImplementedError(
                "gumloop_llm strategy is not implemented in the API. "
                "This strategy is handled by Gumloop workflow nodes. "
                "Use strategy='gemini_fallback' or let the system auto-detect based on transcript length."
            )
        
        # Extract text from transcript
        full_text = " ".join(
            segment.get("text", "")
            for segment in request.transcript.get("segments", [])
        )
        
        # Generate EDL with constraints
        constraints = {
            "min_clip_length": 15,
            "max_clip_length": 90,
            "max_clips": 10,
            "require_strong_hook": True
        }
        
        edl = provider.generate_edl(full_text, request.duration_sec, constraints)
        
        logger.info("Clip selection complete", num_clips=len(edl.get("clips", [])))
        
        # Return as JSON string
        return ClipSelectionResponse(raw_edl_json=json.dumps(edl))
        
    except NotImplementedError as e:
        logger.error("Strategy not implemented", error=str(e))
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error("Clip selection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/repair-edl", response_model=RepairResponse)
async def repair_edl(request: RepairRequest):
    """Repair invalid EDL JSON using LLM."""
    logger = StructuredLogger(request.job_id, "repair_edl")
    
    try:
        provider = get_provider(request.repair_strategy)
        
        # Build repair instructions
        repair_prompt = f"""The following EDL JSON has validation errors:

{request.validation_error}

Original JSON:
{request.raw_edl_json}

Rules for repair:
1. Fix ONLY JSON syntax and field errors
2. Do NOT invent or change timestamps
3. Remove clips that violate constraints (too short, too long, overlapping)
4. Keep all valid clips unchanged
5. Ensure all timestamps are within 0-{request.duration_sec} seconds
6. Return ONLY valid JSON matching the EDL schema
"""
        
        repaired_edl = provider.repair_edl(repair_prompt, request.duration_sec)
        
        logger.info("EDL repaired successfully")
        
        return RepairResponse(
            repaired_edl_json=json.dumps(repaired_edl)
        )
        
    except Exception as e:
        logger.error("EDL repair failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate-edl", response_model=ValidateEDLResponse)
async def validate_edl(request: ValidateEDLRequest):
    """Validate EDL JSON against schema and constraints."""
    logger = StructuredLogger(request.job_id, "validate_edl")
    errors = []
    
    try:
        # Parse JSON
        try:
            edl = json.loads(request.edl_json)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
            return ValidateEDLResponse(valid=False, errors=errors)
        
        # Check clips array exists
        if "clips" not in edl:
            errors.append("Missing 'clips' array in EDL")
            return ValidateEDLResponse(valid=False, errors=errors)
        
        clips = edl["clips"]
        
        # Validate each clip
        for i, clip in enumerate(clips):
            # Required fields
            required_fields = ["clip_id", "start_sec", "end_sec", "title", "hook_text", "score"]
            for field in required_fields:
                if field not in clip:
                    errors.append(f"Clip {i}: missing required field '{field}'")
            
            if errors:
                continue  # Skip further validation for this clip
            
            # Duration constraints (15-90 seconds)
            duration = clip["end_sec"] - clip["start_sec"]
            if duration < 15:
                errors.append(f"Clip {i} ({clip['clip_id']}): duration {duration:.1f}s < 15s minimum")
            elif duration > 90:
                errors.append(f"Clip {i} ({clip['clip_id']}): duration {duration:.1f}s > 90s maximum")
            
            # Timestamp constraints
            if clip["start_sec"] < 0:
                errors.append(f"Clip {i} ({clip['clip_id']}): start_sec {clip['start_sec']} < 0")
            if clip["end_sec"] > request.duration_sec:
                errors.append(f"Clip {i} ({clip['clip_id']}): end_sec {clip['end_sec']} > video duration {request.duration_sec}")
            if clip["start_sec"] >= clip["end_sec"]:
                errors.append(f"Clip {i} ({clip['clip_id']}): start_sec >= end_sec")
            
            # Score constraints (0.0-1.0)
            if not (0.0 <= clip["score"] <= 1.0):
                errors.append(f"Clip {i} ({clip['clip_id']}): score {clip['score']} not in range [0.0, 1.0]")
        
        # Check for overlapping clips
        sorted_clips = sorted(clips, key=lambda c: c.get("start_sec", 0))
        for i in range(len(sorted_clips) - 1):
            clip1 = sorted_clips[i]
            clip2 = sorted_clips[i + 1]
            if "start_sec" in clip1 and "end_sec" in clip1 and "start_sec" in clip2:
                if clip1["end_sec"] > clip2["start_sec"]:
                    errors.append(
                        f"Overlapping clips: {clip1.get('clip_id', i)} "
                        f"({clip1['start_sec']}-{clip1['end_sec']}) and "
                        f"{clip2.get('clip_id', i+1)} ({clip2['start_sec']}-...)"
                    )
        
        valid = len(errors) == 0
        
        logger.info("EDL validation complete", valid=valid, num_errors=len(errors))
        
        return ValidateEDLResponse(
            valid=valid,
            errors=errors,
            edl=edl if valid else None
        )
        
    except Exception as e:
        logger.error("Validation failed", error=str(e))
        errors.append(f"Unexpected error: {str(e)}")
        return ValidateEDLResponse(valid=False, errors=errors)


@app.post("/api/merge-recipe", response_model=MergeRecipeResponse)
async def merge_recipe(request: MergeRecipeRequest):
    """Merge EDL + word_timeline + crop_paths into render recipe."""
    logger = StructuredLogger(request.job_id, "merge_recipe")
    
    try:
        # Parse EDL if it's a string
        if isinstance(request.edl_json, str):
            edl = json.loads(request.edl_json)
        else:
            edl = request.edl_json
        
        # Load word timeline
        word_timeline_path = request.word_timeline_uri.replace("file://", "")
        with open(word_timeline_path, 'r') as f:
            word_timeline = json.load(f)
        
        # Load crop paths
        crop_paths_path = request.crop_paths_uri.replace("file://", "")
        with open(crop_paths_path, 'r') as f:
            crop_paths_data = json.load(f)
        
        # Extract crop_path array (handle both formats)
        crop_path_keyframes = crop_paths_data.get("crop_path", [])
        
        # Build render recipe clips
        render_clips = []
        
        for clip in edl.get("clips", []):
            clip_start = clip["start_sec"]
            clip_end = clip["end_sec"]
            
            # Extract words for this clip's time range
            clip_words = []
            for segment in word_timeline.get("segments", []):
                for word in segment.get("words", []):
                    word_start = word.get("start", 0)
                    word_end = word.get("end", 0)
                    
                    # Check if word overlaps with clip
                    if word_end >= clip_start and word_start <= clip_end:
                        # Convert to 0-based (relative to clip start)
                        clip_words.append({
                            "start": max(0, word_start - clip_start),
                            "end": min(clip_end - clip_start, word_end - clip_start),
                            "text": word.get("word", "")
                        })
            
            # Extract crop_path keyframes for this clip's time range
            clip_crop_path = []
            for keyframe in crop_path_keyframes:
                kf_time = keyframe.get("t", 0)
                
                # Check if keyframe is in clip's time range
                if clip_start <= kf_time <= clip_end:
                    # Convert to 0-based (relative to clip start)
                    clip_crop_path.append({
                        "t": kf_time - clip_start,
                        "x": keyframe.get("x", 0),
                        "y": keyframe.get("y", 0),
                        "w": keyframe.get("w", 1080),
                        "h": keyframe.get("h", 1920)
                    })
            
            # Build clip entry
            render_clip = {
                "clip_id": clip["clip_id"],
                "start_sec": clip_start,
                "end_sec": clip_end,
                "crop_path": clip_crop_path,
                "subtitles": clip_words
            }
            
            render_clips.append(render_clip)
        
        # Build render recipe
        render_recipe = {
            "video_uri": request.video_uri,
            "clips": render_clips
        }
        
        # Save to temp file
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{request.job_id}_recipe_")
        recipe_path = f"{output_dir}/render_recipe.json"
        
        with open(recipe_path, 'w') as f:
            json.dump(render_recipe, f, indent=2)
        
        logger.info("Render recipe created", num_clips=len(render_clips), path=recipe_path)
        
        return MergeRecipeResponse(
            render_recipe_uri=f"file://{recipe_path}"
        )
        
    except Exception as e:
        logger.error("Recipe merge failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "autoclipper-unified-api", "version": "2.0.0"}


# ============================================================================
# Static File Serving - Must be last to avoid intercepting API routes
# ============================================================================

app.mount(
    "/",
    StaticFiles(directory="api/static", html=True),
    name="static",
)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
