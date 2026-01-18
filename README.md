# AutoClipper

AI-powered video repurposing platform that converts long-form videos into ranked vertical short clips with burned-in captions.

**🚀 Live API**: `https://autoclipper-production.up.railway.app`

## Quick Start

### Prerequisites
- Python 3.10+
- Git

### Run Locally
```bash
# Clone the repository
git clone https://github.com/salimhs/autoclipper.git
cd autoclipper

# Install dependencies
pip install -r requirements-runtime.txt

# Set environment variables (copy .env.example to .env and fill in values)
cp .env.example .env

# Run the API server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8081
```

### Use the CLI
```bash
# Process a video using the cloud API
$env:CLI_BACKEND_URL="https://autoclipper-production.up.railway.app"
python clipper.py --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Gumloop Workflow                        │
│  (Orchestrates the pipeline, triggers API endpoints)        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   AutoClipper API (Railway)                  │
│  /api/download → /api/transcribe → /api/track               │
│  /api/select-clips → /api/validate-edl → /api/merge-recipe  │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Directory | Purpose |
|-----------|---------|
| `/api` | Unified FastAPI application exposing all endpoints |
| `/ai` | Gemini LLM prompts and clip selection logic |
| `/perception` | WhisperX transcription and MediaPipe visual tracking |
| `/render` | FFmpeg-based video rendering workers |
| `/utils` | Shared utilities (caching, logging, retry logic) |
| `/schemas` | JSON schema definitions for EDL, recipes, etc. |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/jobs` | POST | Create new processing job |
| `/jobs/{id}` | GET | Get job status |
| `/api/download` | POST | Download video + extract audio |
| `/api/transcribe` | POST | Transcribe audio with WhisperX |
| `/api/track` | POST | Visual tracking + crop paths |
| `/api/select-clips` | POST | AI clip selection (Gemini) |
| `/api/validate-edl` | POST | Validate EDL structure |
| `/api/repair-edl` | POST | AI-powered EDL repair |
| `/api/merge-recipe` | POST | Merge all data into render recipe |

## Workflow Pipeline

1. **Download** - Download video from URL, extract audio
2. **Transcribe** - WhisperX speech-to-text with word timestamps
3. **Track** - Face detection + crop path generation (parallel with transcribe)
4. **Select Clips** - Gemini AI identifies viral-worthy segments
5. **Validate** - Check EDL against duration constraints
6. **Repair** - Fix invalid EDL entries (if needed)
7. **Merge** - Combine transcript + tracking + EDL into render recipe
8. **Render** - Generate final vertical clips with captions

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `GUMLOOP_WORKFLOW_ID` | Your Gumloop workflow ID |
| `GUMLOOP_API_KEY` | Your Gumloop API key |
| `GUMLOOP_USER_ID` | Your Gumloop user ID |
| `GEMINI_API_KEY` | Google Gemini API key |

### Optional
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8081 | Server port |
| `LLM_TOKEN_THRESHOLD` | 80000 | Token threshold for LLM routing |
| `RENDER_WORKER_URL` | http://localhost:8000 | Render worker URL |

## Deployment

### Railway (Recommended)
The project is configured for Railway deployment via `railway.toml` and `Dockerfile`.

```bash
# Push to main branch - Railway auto-deploys
git push origin main
```

### Docker
```bash
# Build and run locally
docker build -t autoclipper .
docker run -p 8081:8081 --env-file .env autoclipper
```

## Project Structure

```
autoclipper/
├── api/
│   ├── main.py           # Unified API (all endpoints)
│   ├── job_controller.py # Job management (legacy, use main.py)
│   ├── status_store.py   # In-memory job state
│   └── static/           # Dashboard UI
├── ai/
│   ├── llm_provider.py   # LLM abstraction (Gemini)
│   └── gemini_prompts/   # Prompt templates
├── perception/
│   ├── whisperx_runner.py # Speech-to-text
│   └── tracking.py        # Face tracking + crop paths
├── render/
│   └── worker.py          # FFmpeg rendering
├── utils/
│   ├── cache.py          # Caching layer
│   ├── logger.py         # Structured logging
│   └── retry.py          # Retry decorator
├── clipper.py            # CLI tool
├── Dockerfile            # Railway deployment
└── requirements-*.txt    # Dependencies
```

## License

MIT

---

Built for McGill Hackathon 2026 - Gumloop Challenge 🏆
