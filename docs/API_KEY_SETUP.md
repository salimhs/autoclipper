# Gumloop API Key Setup Guide

## Where to Add Your Gumloop API Key

### Option 1: Local Development (.env file)

1. **Create your `.env` file** (copy from template):
   ```bash
   copy .env.example .env
   ```

2. **Edit `.env` and add your actual keys**:
   ```
   GEMINI_API_KEY=AIzaSyC...your_actual_gemini_key
   GUMLOOP_API_KEY=gum_...your_actual_gumloop_key
   GUMLOOP_WORKFLOW_ID=wf_...your_workflow_id
   ```

3. **Get your Gumloop API key**:
   - Go to [Gumloop Settings](https://www.gumloop.com/settings/profile/credentials)
   - Click "Generate API Key"
   - Copy and paste into `.env`

### Option 2: Gumloop Workflow (Cloud)

When running in Gumloop's cloud environment:

1. **Open your workflow** in Gumloop
2. **Click the Settings/Gear icon** (⚙️)
3. **Go to "Environment Variables"** or "Secrets"
4. **Add these variables**:
   ```
   GEMINI_API_KEY=your_gemini_key
   GATEWAY_URL=https://your-ngrok-url.ngrok-free.app
   RENDER_WORKER_URL=https://your-other-ngrok-url.ngrok-free.app
   ```

**Note**: The Gumloop API key is NOT needed inside the workflow itself—it's only needed if you want to trigger workflows programmatically from outside Gumloop (e.g., from your CLI or API).

### Option 3: Programmatic Triggering (Optional)

If you want to trigger Gumloop workflows from your code:

**In `api/job_controller.py`** (already configured):
```python
# Line 77-86
gumloop_response = requests.post(
    f"https://api.gumloop.com/v1/workflows/{workflow_id}/trigger",
    json={
        "job_id": job_id,
        "video_url": str(request.video_url)
    },
    headers={
        "Authorization": f"Bearer {os.getenv('GUMLOOP_API_KEY')}"
    }
)
```

This reads `GUMLOOP_API_KEY` from your `.env` file automatically.

## Quick Setup Checklist

- [ ] Copy `.env.example` to `.env`
- [ ] Add your Gemini API key to `.env`
- [ ] Add your Gumloop API key to `.env` (if triggering programmatically)
- [ ] Add environment variables in Gumloop workflow settings
- [ ] Start services: `python api/gumloop_gateway.py`

## Getting Your API Keys

### Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

### Gumloop API Key
1. Go to [Gumloop Settings](https://www.gumloop.com/settings/profile/credentials)
2. Click "Generate API Key"
3. Copy the key

### Gumloop Workflow ID
1. Open your workflow in Gumloop
2. Look at the URL: `https://www.gumloop.com/pipeline?id=wf_abc123`
3. The workflow ID is `wf_abc123`

## Security Notes

- ✅ **DO**: Keep `.env` in `.gitignore` (already configured)
- ✅ **DO**: Use environment variables for all secrets
- ❌ **DON'T**: Commit API keys to Git
- ❌ **DON'T**: Share your `.env` file

## Testing Your Setup

```bash
# Check if environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GEMINI_API_KEY:', os.getenv('GEMINI_API_KEY')[:10] + '...')"
```

Expected output:
```
GEMINI_API_KEY: AIzaSyC...
```
