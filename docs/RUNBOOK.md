# AutoClipper Local Runbook

## Prerequisites

1. **Python 3.11+** installed
2. **FFmpeg** installed and in PATH
3. **yt-dlp** installed (`pip install yt-dlp`)
4. **GPU** (recommended for WhisperX and tracking)

## Install Dependencies

```bash
cd C:\Users\sal\OneDrive\Desktop\repos\autoclipper
pip install -r requirements.txt
```

## Configure Environment

```bash
copy .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_actual_key_here
GUMLOOP_API_KEY=your_gumloop_key
RENDER_WORKER_URL=http://localhost:8000
```

## Run End-to-End Locally

### Option 1: Test Individual Components

#### 1. Test URL Validation
```bash
cd orchestrator\node_scripts
python validate_url.py "{\"video_url\": \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\", \"job_id\": \"test-001\"}"
```

#### 2. Test Download + Extract
```bash
python download_extract.py "{\"video_url\": \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\", \"job_id\": \"test-001\"}"
```

#### 3. Test WhisperX Transcription
```bash
python whisperx_transcribe.py "{\"audio_uri\": \"file:///tmp/audio.wav\", \"video_url\": \"...\", \"duration_sec\": 120, \"job_id\": \"test-001\"}"
```

#### 4. Test Visual Tracking
```bash
python visual_tracking.py "{\"video_uri\": \"file:///tmp/video.mp4\", \"video_url\": \"...\", \"width\": 1920, \"height\": 1080, \"job_id\": \"test-001\"}"
```

#### 5. Test Model Router
```bash
python model_router.py "{\"transcript_uri\": \"file:///tmp/transcript.json\", \"duration_sec\": 120, \"job_id\": \"test-001\"}"
```

#### 6. Test Clip Selection (Gemini)
```bash
python llm_select_clips.py "{\"transcript_uri\": \"file:///tmp/transcript.json\", \"duration_sec\": 120, \"strategy\": \"gemini_fallback\", \"job_id\": \"test-001\"}"
```

#### 7. Test EDL Validation
```bash
python json_validate_edl.py "{\"raw_edl_json\": \"{...}\", \"duration_sec\": 120, \"transcript_uri\": \"file:///tmp/transcript.json\", \"job_id\": \"test-001\"}"
```

### Option 2: Run Full Pipeline

#### 1. Start Render Worker
```bash
cd render
python worker.py
```

#### 2. Start API Server
```bash
cd api
python job_controller.py
```

#### 3. Trigger Job
```bash
curl -X POST http://localhost:8080/jobs \
  -H "Content-Type: application/json" \
  -d "{\"video_url\": \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\"}"
```

#### 4. Check Status
```bash
curl http://localhost:8080/jobs/{job_id}
```

### Option 3: Gumloop Workflow

1. Navigate to Gumloop dashboard
2. Import `orchestrator/gumloop_flow.json`
3. Configure environment variables
4. Trigger workflow with video URL

## Troubleshooting

### WhisperX GPU Issues
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Use CPU if needed (slower)
# Edit perception/whisperx_runner.py: device="cpu"
```

### FFmpeg Not Found
```bash
# Windows: Add to PATH or install via chocolatey
choco install ffmpeg

# Verify
ffmpeg -version
```

### Cache Cleanup
```bash
# Remove old cache files
python -c "from utils.cache import CacheManager; CacheManager().cleanup_expired()"
```

### View Logs
```bash
# Logs are in /tmp/logs/{job_id}.jsonl
type C:\tmp\logs\test-001.jsonl
```

## Expected Duration

For a 10-minute video:
- Download: ~30s
- Transcription: ~2-3 min (GPU) / ~10 min (CPU)
- Tracking: ~1-2 min (GPU)
- Clip Selection: ~20s
- Rendering (3 clips): ~2-3 min

**Total: ~6-10 minutes**

## Output

Completed job returns:
```json
{
  "job_id": "...",
  "status": "completed",
  "clips": [
    {
      "clip_id": "clip_001",
      "mp4_url": "file:///tmp/...",
      "score": 0.92
    }
  ],
  "metadata": {
    "strategy_used": "gumloop_llm",
    "model_used": "gumloop_best_reasoning"
  }
}
```
