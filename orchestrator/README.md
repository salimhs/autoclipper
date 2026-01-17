# Gumloop Orchestration

## Workflow Overview

AutoClipper uses an 11-node Gumloop workflow with **dynamic model routing** and **validation/repair pipeline**.

### Workflow Nodes

1. **URL Validation** - Verify URL and detect platform
2. **Download + Extract** - Download video, extract audio
3a. **WhisperX Transcription** (parallel) - Word-level transcription with caching
3b. **Visual Tracking** (parallel) - Face detection + crop path generation with caching
3c. **Model Router** - Choose Gumloop LLM vs Gemini fallback
4. **LLM Clip Selection** - Generate EDL using selected model
4b. **Validate EDL** - Schema + constraint validation
4c. **Repair EDL** (conditional) - Fix invalid EDL if validation fails
5. **Merge Render Recipe** - Combine EDL + transcripts + crop paths
6. **Dispatch GPU Render** - Webhook to render worker
7. **Collect Results** - Poll and return final clips

### Model Routing Logic

**node_3c** dynamically selects:
- **Gumloop LLM** (default): Transcript < 80K tokens - faster, cheaper
- **Gemini fallback**: Transcript ≥ 80K tokens - long context support

### Validation & Repair

**node_4b** validates EDL against:
- JSON schema (`schemas/edl.json`)
- Timestamp bounds (0 ≤ t ≤ duration)
- Clip length (15-90s)
- No overlaps
- Minimum transcription quality (0.75 confidence)

If invalid → **node_4c** repairs using LLM with strict instructions.

## Node Scripts

All scripts in `node_scripts/`:

| Script | Purpose |
|--------|---------|
| `validate_url.py` | URL validation + platform detection |
| `download_extract.py` | yt-dlp download + ffmpeg audio extract |
| `whisperx_transcribe.py` | WhisperX with caching |
| `visual_tracking.py` | MediaPipe tracking + One Euro smoothing |
| `model_router.py` | Route to Gumloop vs Gemini |
| `llm_select_clips.py` | Clip selection (Gemini fallback) |
| `json_validate_edl.py` | EDL validation |
| `json_repair_edl.py` | EDL repair |
| `merge_render_recipe.py` | Combine all data sources |

## Import to Gumloop

1. Navigate to Gumloop dashboard
2. Click "Import Workflow"
3. Upload `gumloop_flow.json`
4. Configure node scripts:
   - Upload each `.py` file as custom code
   - Ensure dependencies installed (`requirements.txt`)
5. Set environment variables:
   - `GEMINI_API_KEY` (for fallback)
   - `RENDER_WORKER_URL`
6. Test with sample video

## Environment Variables

Required in Gumloop:
```
GEMINI_API_KEY=your_key_here
RENDER_WORKER_URL=https://your-render-worker.com
```

Optional:
```
CACHE_TTL_DAYS=7
MIN_CONFIDENCE=0.75
MAX_CLIPS=10
```

## Testing Locally

See `docs/RUNBOOK.md` for detailed local testing instructions.

Quick test of individual nodes:
```bash
cd orchestrator/node_scripts
python validate_url.py '{"video_url": "https://youtube.com/watch?v=...", "job_id": "test"}'
```

## Production Optimizations

- **Caching**: Transcripts/tracking cached for 7 days (saves GPU $$$)
- **Retry logic**: Exponential backoff on transient failures
- **Structured logging**: JSON logs to `/tmp/logs/{job_id}.jsonl`
- **Quality filtering**: Rejects low-confidence transcriptions
- **Overlap detection**: Prevents LLM from selecting overlapping clips

## Monitoring

Check logs:
```bash
# View job log
cat /tmp/logs/{job_id}.jsonl | jq .

# Filter errors
cat /tmp/logs/{job_id}.jsonl | jq 'select(.level=="ERROR")'

# View timing data
cat /tmp/logs/{job_id}.jsonl | jq 'select(.level=="TIMING")'
```
