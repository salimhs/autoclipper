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
