# 🚀 Execution Checklist - AutoClipper

You've installed the requirements! Here's what you need to do next to execute the system.

## ✅ Pre-Flight Checklist

### 1. Create Your `.env` File
```bash
copy .env.example .env
```

Then edit `.env` and add your **Gemini API key**:
```
GEMINI_API_KEY=AIzaSyC...your_actual_key_here
```

**Get your Gemini API key**: https://makersuite.google.com/app/apikey

---

## 🎯 Execution Options

You have **3 ways** to run AutoClipper:

### **Option A: Quick Test with CLI** (Easiest)
```bash
# Start the services first
python api/gumloop_gateway.py
```

In another terminal:
```bash
python clipper.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### **Option B: Direct API Testing**
```bash
# Terminal 1: Start Gateway
python api/gumloop_gateway.py

# Terminal 2: Start Render Worker
python render/worker.py

# Terminal 3: Test
curl http://localhost:8001/health
```

### **Option C: Full Gumloop Integration**
1. Start both services:
   ```bash
   python api/gumloop_gateway.py  # Terminal 1
   python render/worker.py         # Terminal 2
   ```

2. Expose to internet with ngrok:
   ```bash
   ngrok http 8001  # Terminal 3
   ngrok http 8000  # Terminal 4
   ```

3. Import `orchestrator/gumloop_flow.json` to Gumloop
4. Add ngrok URLs to Gumloop environment variables
5. Run workflow in Gumloop

---

## 🧪 Quick Health Check

After starting the gateway:
```bash
curl http://localhost:8001/health
```

**Expected response:**
```json
{"status": "healthy", "service": "autoclipper-gateway"}
```

---

## 📋 What Each Service Does

| Service | Port | Purpose |
|---------|------|---------|
| **Gateway** | 8001 | HTTP wrapper for business logic (download, transcribe, track, clip selection) |
| **Render Worker** | 8000 | GPU rendering service (converts recipes to MP4 files) |

---

## 🎬 Full Execution Flow

```
1. Start Gateway (port 8001)
   ↓
2. Start Render Worker (port 8000)
   ↓
3. Submit video URL
   ↓
4. Gateway processes:
   - Downloads video
   - Transcribes audio (WhisperX)
   - Tracks faces (MediaPipe)
   - Selects clips (Gemini/Gumloop LLM)
   - Validates & repairs EDL
   ↓
5. Render Worker creates MP4 clips
   ↓
6. Clips saved to outputs/ folder
```

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: whisperx"
```bash
pip install git+https://github.com/m-bain/whisperX.git
```

### "Port already in use"
```bash
# Windows
netstat -ano | findstr :8001
taskkill /F /PID <PID>
```

### "GEMINI_API_KEY not found"
Make sure you created `.env` and added your API key.

---

## 📁 Where to Find Your Clips

Generated clips are automatically saved to:
```
C:\Users\sal\OneDrive\Desktop\repos\autoclipper\outputs\
```

Each job creates a timestamped folder with:
- `clip_001.mp4`, `clip_002.mp4`, etc.
- `manifest.json` (metadata)
- `README.md` (human-readable summary)

---

## 🎯 Recommended First Test

**Simplest way to verify everything works:**

```bash
# Terminal 1
python api/gumloop_gateway.py

# Wait for "Uvicorn running on http://0.0.0.0:8001"
# Then test health check in Terminal 2:
curl http://localhost:8001/health
```

If you see `{"status": "healthy", "service": "autoclipper-gateway"}`, you're ready to go! 🎉

---

## 📚 Documentation

- **Quick Start**: `QUICKSTART.md`
- **API Keys**: `docs/API_KEY_SETUP.md`
- **Gumloop Setup**: `docs/GUMLOOP_INTEGRATION.md`
- **Full Guide**: `docs/RUNBOOK.md`
