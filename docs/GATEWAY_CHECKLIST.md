# Gumloop Gateway - Validation Checklist

## ✅ Implementation Checklist

### Core Files
- [x] File `api/gumloop_gateway.py` exists
- [x] File contains all 6 endpoints (download, transcribe, track, select-clips, repair-edl, health)
- [x] All imports reference existing modules (perception, ai, utils)
- [x] Pydantic models defined for all request/response types
- [x] Port is 8001 in `uvicorn.run()`
- [x] Error handling uses `HTTPException`
- [x] Logging uses `StructuredLogger`
- [x] Caching uses `CacheManager`
- [x] File URIs use `file://` prefix
- [x] Temp directories use `tempfile.mkdtemp()` with job_id

### Configuration
- [x] `.env.example` updated with service URLs
- [x] Documentation created in `docs/GUMLOOP_INTEGRATION.md`
- [x] Startup script created in `scripts/start_services.sh`

### Dependencies
- [ ] **REQUIRED**: Install WhisperX
  ```bash
  pip install git+https://github.com/m-bain/whisperX.git
  ```
- [ ] Verify all requirements installed: `pip install -r requirements.txt`

## 🧪 Testing Commands

### 1. Health Check
```bash
# Start the gateway
python api/gumloop_gateway.py

# In another terminal, test health
curl http://localhost:8001/health
```

**Expected Response:**
```json
{"status": "healthy", "service": "autoclipper-gateway"}
```

### 2. Test Download Endpoint
```bash
curl -X POST http://localhost:8001/api/download \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "job_id": "test_001"}'
```

**Expected**: JSON with video_uri, audio_uri, duration_sec, fps, width, height

### 3. Check Logs
```bash
# View structured logs
cat /tmp/logs/test_001.jsonl
```

## 📋 Next Steps

1. **Install WhisperX** (required for transcription)
   ```bash
   pip install git+https://github.com/m-bain/whisperX.git
   ```

2. **Start Both Services**
   ```bash
   # Terminal 1
   python api/gumloop_gateway.py
   
   # Terminal 2
   python render/worker.py
   ```

3. **Expose via ngrok** (for Gumloop to reach your local machine)
   ```bash
   # Terminal 3
   ngrok http 8001
   
   # Terminal 4
   ngrok http 8000
   ```

4. **Configure Gumloop**
   - Add ngrok URLs to Gumloop environment variables
   - Update workflow nodes to call gateway endpoints
   - Test end-to-end

## 🔧 Troubleshooting

### WhisperX Not Found
```bash
pip install git+https://github.com/m-bain/whisperX.git
```

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8001
taskkill /F /PID <PID>

# Mac/Linux
lsof -i :8001
kill <PID>
```

### Import Errors
```bash
# Ensure you're in the project root
cd C:\Users\sal\OneDrive\Desktop\repos\autoclipper
python api/gumloop_gateway.py
```

## 📊 Service Architecture

```
Gumloop (Cloud)
      ↓
   [ngrok]
      ↓
Gateway :8001 ──→ Business Logic (ai/, perception/, utils/)
      ↓
Render Worker :8000
      ↓
  outputs/
```

## ✨ Key Features

- **Caching**: Transcripts and tracking cached for 7 days
- **Retry Logic**: Exponential backoff on failures
- **Structured Logging**: JSON logs to `/tmp/logs/`
- **File Management**: Automatic temp directory creation
- **Error Handling**: Proper HTTP status codes and error messages
