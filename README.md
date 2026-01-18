# AutoClipper

AI-powered video repurposing platform that converts long-form videos into ranked vertical short clips with burned-in captions.

## Architecture

**Control Plane**: API service, job state storage, Gumloop workflow trigger  
**Intelligence Plane**: Gemini clip selection, deterministic EDL generation  
**Perception Plane**: WhisperX transcription, visual tracking, crop planning  
**Execution Plane**: GPU render workers, FFmpeg-based rendering

All components communicate via JSON + storage URIs.

## Components

- `/api` - Job management API
- `/orchestrator` - Gumloop workflow definitions
- `/ai` - Gemini prompts and clip selection logic
- `/perception` - WhisperX and visual tracking services
- `/render` - GPU render workers
- `/schemas` - Canonical JSON schemas

## Workflow

1. Validate URL
2. Download + extract audio
3. Transcribe + track (parallel)
4. Gemini EDL generation
5. Merge render recipe
6. Render clips
7. Return outputs

## Environment Variables

### Required
- `GUMLOOP_WORKFLOW_ID` - Your Gumloop workflow ID
- `GUMLOOP_API_KEY` - Your Gumloop API key
- `GUMLOOP_USER_ID` - Your Gumloop user ID
- `GEMINI_API_KEY` - Google Gemini API key (for fallback LLM)

### Optional
- `LLM_TOKEN_THRESHOLD` - Token count threshold for LLM routing (default: 80000)
- `RENDER_WORKER_URL` - URL of render worker service (default: http://localhost:8000)
- `PORT` - Server port (default: 8081)
