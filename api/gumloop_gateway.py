"""
Gumloop Gateway API - HTTP wrapper for AutoClipper services.
Exposes existing business logic as REST endpoints for Gumloop orchestration.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
from fractions import Fraction

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing modules (lazy-loaded heavy dependencies in functions)
from ai.llm_provider import get_provider
from utils.logger import StructuredLogger
from utils.cache import CacheManager
from utils.retry import retry_with_backoff
# Heavy ML imports moved inside endpoints to support slim deployments


app = FastAPI(title="AutoClipper Gumloop Gateway", version="1.0.0")


# ============================================================================
# Pydantic Models
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
    confidence_average: float


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
    strategy: str
    job_id: str

class ClipSelectionResponse(BaseModel):
    edl: Dict[str, Any]


class RepairRequest(BaseModel):
    raw_edl_json: str
    validation_error: str
    duration_sec: float
    repair_strategy: str
    job_id: str

class RepairResponse(BaseModel):
    repaired_edl_json: str


# ============================================================================
# Endpoints
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
    from perception.whisperx_runner import WhisperXRunner
    
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
            confidence_average=1.0
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
            confidence_average=avg_confidence
        )
        
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/track", response_model=TrackingResponse)
async def track_video(request: TrackingRequest):
    """Track faces and generate crop paths using MediaPipe."""
    from perception.tracking import VisualTracker
    
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
    
    try:
        from ai.llm_provider import get_provider
        # Get appropriate provider
        provider = get_provider(request.strategy)
    except Exception as e:
        logger.error("LLM Provider initialization failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"LLM Provider error: {str(e)}")
        
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
        
        return ClipSelectionResponse(edl=edl)
        
    except Exception as e:
        logger.error("Clip selection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/repair-edl", response_model=RepairResponse)
async def repair_edl(request: RepairRequest):
    """Repair invalid EDL JSON using LLM."""
    logger = StructuredLogger(request.job_id, "repair_edl")
    
    try:
        from ai.llm_provider import get_provider
        provider = get_provider(request.repair_strategy)
    except Exception as e:
        logger.error("LLM Provider initialization failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"LLM Provider error: {str(e)}")
        
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "autoclipper-gateway"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
