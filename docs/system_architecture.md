# AutoClipper System Architecture

## Four-Plane Architecture

### Control Plane
- API service (`/api/job_controller.py`)
- Job state storage (`/api/status_store.py`)
- Gumloop workflow trigger

### Intelligence Plane
- Gemini clip selection (`/ai/clip_selector.py`)
- Deterministic EDL generation
- JSON validation and repair

### Perception Plane
- WhisperX transcription (`/perception/whisperx_runner.py`)
- Visual tracking (`/perception/tracking.py`)
- Crop path planning

### Execution Plane
- GPU render workers (`/render/worker.py`)
- FFmpeg-based rendering (`/render/ffmpeg_templates.py`)

## Data Flow

```
Video URL → Download → [Transcribe || Track] → Gemini EDL → Merge Recipe → Render → Clips
```

## Communication Protocol

- **JSON** for all structured data
- **Storage URIs** for large artifacts
- **Webhooks** for async notifications

## Schemas

- `transcript.json` - WhisperX output
- `edl.json` - Edit Decision List
- `render_recipe.json` - Complete render instructions
- `tracking.json` - Visual tracking data
