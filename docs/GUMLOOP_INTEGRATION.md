# Gumloop Integration Guide

## Services Architecture

Gumloop orchestrates AutoClipper by calling these HTTP endpoints:

1. **POST /api/download** - Download video and extract audio
2. **POST /api/transcribe** - WhisperX transcription
3. **POST /api/track** - Visual face tracking
4. **POST /api/select-clips** - LLM clip selection
5. **POST /api/repair-edl** - EDL repair if validation fails
6. **Existing render worker** - GPU rendering (port 8000)

## Running Locally

### Start Services

**Option A: Manual**
```bash
# Terminal 1
python api/gumloop_gateway.py

# Terminal 2
python render/worker.py
```

**Option B: Script (Linux/Mac)**
```bash
chmod +x scripts/start_services.sh
./scripts/start_services.sh
```

**Option C: Windows PowerShell**
```powershell
# Terminal 1
python api/gumloop_gateway.py

# Terminal 2
python render/worker.py
```

### Expose to Internet (for Gumloop)

Since Gumloop is cloud-based, it needs public URLs to reach your local machine:

```bash
# Terminal 3 - Expose Gateway
ngrok http 8001

# Terminal 4 - Expose Render Worker
ngrok http 8000
```

Copy the ngrok URLs (e.g., `https://abc123.ngrok-free.app`)

### Configure Gumloop

1. Go to your Gumloop workflow settings
2. Add environment variables:
   ```
   GATEWAY_URL=https://your-ngrok-url-for-8001.ngrok-free.app
   RENDER_WORKER_URL=https://your-ngrok-url-for-8000.ngrok-free.app
   GEMINI_API_KEY=your_actual_key
   ```
3. Update each custom node to call the gateway endpoints
4. Test the workflow

## API Endpoints

### 1. Download Video
```bash
curl -X POST http://localhost:8001/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=...",
    "job_id": "test_001"
  }'
```

**Response:**
```json
{
  "video_uri": "file:///tmp/...",
  "audio_uri": "file:///tmp/...",
  "duration_sec": 120.5,
  "fps": 30.0,
  "width": 1920,
  "height": 1080
}
```

### 2. Transcribe Audio
```bash
curl -X POST http://localhost:8001/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "audio_uri": "file:///tmp/audio.wav",
    "video_url": "https://youtube.com/...",
    "duration_sec": 120.5,
    "job_id": "test_001"
  }'
```

### 3. Track Video
```bash
curl -X POST http://localhost:8001/api/track \
  -H "Content-Type: application/json" \
  -d '{
    "video_uri": "file:///tmp/video.mp4",
    "video_url": "https://youtube.com/...",
    "width": 1920,
    "height": 1080,
    "job_id": "test_001"
  }'
```

### 4. Select Clips
```bash
curl -X POST http://localhost:8001/api/select-clips \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": {...},
    "duration_sec": 120.5,
    "strategy": "gemini_fallback",
    "job_id": "test_001"
  }'
```

### 5. Repair EDL
```bash
curl -X POST http://localhost:8001/api/repair-edl \
  -H "Content-Type: application/json" \
  -d '{
    "raw_edl_json": "{...}",
    "validation_error": "Clips overlap...",
    "duration_seconds": 120.5,
    "strategy": "gemini_fallback",
    "job_id": "test_001"
  }'
```

### 6. Health Check
```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "autoclipper-gateway"
}
```

## Testing

### Quick Health Check
```bash
# Gateway
curl http://localhost:8001/health

# Render Worker
curl http://localhost:8000/docs
```

### Full Integration Test
```bash
# 1. Download
DOWNLOAD_RESPONSE=$(curl -s -X POST http://localhost:8001/api/download \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ", "job_id": "test_001"}')

echo $DOWNLOAD_RESPONSE

# 2. Extract URIs and continue with transcribe, track, etc.
```

## Troubleshooting

### "Connection Refused"
- Ensure services are running: `ps aux | grep python`
- Check ports: `netstat -ano | findstr :8001` (Windows) or `lsof -i :8001` (Mac/Linux)

### "Module Not Found"
- Install dependencies: `pip install -r requirements.txt`
- Check Python path in imports

### "File Not Found" (file:// URIs)
- Temp files are cleaned up automatically
- For debugging, check `/tmp/autoclipper_*` directories

### ngrok Issues
- Free tier has session limits
- Use `ngrok http 8001 --log=stdout` for debugging
- Alternative: Deploy to cloud (Modal, RunPod, AWS Lambda)

## Production Deployment

For production, replace ngrok with:

1. **Deploy Gateway to Cloud**
   ```bash
   # Example: Deploy to Modal
   modal deploy api/gumloop_gateway.py
   ```

2. **Update Gumloop Environment**
   ```
   GATEWAY_URL=https://your-production-gateway.com
   RENDER_WORKER_URL=https://your-production-worker.com
   ```

3. **Use Cloud Storage**
   - Replace `file://` URIs with S3/GCS URLs
   - Update OutputManager to upload instead of local save

## Architecture Diagram

```
Gumloop Cloud
     ↓
  [ngrok tunnel]
     ↓
Gateway (port 8001)
     ↓
  ┌──────────────────┐
  │  Business Logic  │
  ├──────────────────┤
  │ • ai/            │
  │ • perception/    │
  │ • utils/         │
  └──────────────────┘
     ↓
Render Worker (port 8000)
     ↓
outputs/ folder
```

## Key Notes

- Gateway runs on **port 8001**
- Render worker runs on **port 8000**
- All file paths use `file://` prefix
- Caching enabled for transcripts and tracking
- Structured logging to `/tmp/logs/{job_id}.jsonl`
- Automatic retry with exponential backoff
