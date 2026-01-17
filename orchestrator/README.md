# Gumloop Orchestration

## Workflow Definition

`gumloop_flow.json` defines the complete workflow with 7 nodes.

## Node Scripts

Located in `node_scripts/`:

- `validate_url.py` - URL validation
- `download_extract.py` - Video download and audio extraction
- `whisperx_transcribe.py` - Transcription
- `visual_tracking.py` - Face tracking
- `gemini_select_clips.py` - Clip selection
- `merge_render_recipe.py` - Recipe merging
- Nodes 6-7 use webhooks to render worker

## Import to Gumloop

1. Navigate to Gumloop dashboard
2. Click "Import Workflow"
3. Upload `gumloop_flow.json`
4. Configure node scripts as custom code blocks
5. Set environment variables
6. Test with sample video

## Environment Variables

Set in Gumloop workflow:

- `GEMINI_API_KEY`
- `RENDER_WORKER_URL`
- `STORAGE_BUCKET` (for production)

## Testing

Trigger workflow with:
```json
{
  "job_id": "test-123",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```
