# Quick Start Guide - Gumloop API Key Setup

## ✅ Changes Made

1. **Added WhisperX to requirements.txt**
   - Now includes: `git+https://github.com/m-bain/whisperX.git`
   - Also added `python-dotenv` for environment variable management

2. **Created API Key Setup Guide**
   - See: [`docs/API_KEY_SETUP.md`](file:///C:/Users/sal/OneDrive/Desktop/repos/autoclipper/docs/API_KEY_SETUP.md)

## 🔑 Where to Add Your Gumloop API Key

### For Local Development

1. **Create `.env` file** (if you haven't already):
   ```bash
   copy .env.example .env
   ```

2. **Edit `.env` and add your keys**:
   ```
   GEMINI_API_KEY=AIzaSyC...your_actual_key_here
   GUMLOOP_API_KEY=gum_...your_actual_key_here
   ```

3. **Get your Gumloop API key**:
   - Go to: https://www.gumloop.com/settings/profile/credentials
   - Click "Generate API Key"
   - Copy and paste into `.env`

### For Gumloop Workflow (Cloud)

When your workflow runs in Gumloop's cloud:

1. Open your workflow in Gumloop
2. Click the **Settings/Gear icon** (⚙️)
3. Go to **"Environment Variables"**
4. Add:
   ```
   GEMINI_API_KEY=your_gemini_key_here
   GATEWAY_URL=https://your-ngrok-url.ngrok-free.app
   RENDER_WORKER_URL=https://your-other-ngrok-url.ngrok-free.app
   ```

## 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: WhisperX installation may take a few minutes as it installs from GitHub.

## 🚀 Start Services

```bash
# Terminal 1 - Gateway
python api/gumloop_gateway.py

# Terminal 2 - Render Worker
python render/worker.py
```

## 🌐 Expose to Gumloop (ngrok)

```bash
# Terminal 3
ngrok http 8001

# Terminal 4
ngrok http 8000
```

Copy the ngrok URLs and add them to your Gumloop workflow environment variables.

## ✨ Test Your Setup

```bash
# Health check
curl http://localhost:8001/health
```

Expected response:
```json
{"status": "healthy", "service": "autoclipper-gateway"}
```

## 📚 Documentation

- **API Key Setup**: [`docs/API_KEY_SETUP.md`](file:///C:/Users/sal/OneDrive/Desktop/repos/autoclipper/docs/API_KEY_SETUP.md)
- **Gumloop Integration**: [`docs/GUMLOOP_INTEGRATION.md`](file:///C:/Users/sal/OneDrive/Desktop/repos/autoclipper/docs/GUMLOOP_INTEGRATION.md)
- **Gateway Checklist**: [`docs/GATEWAY_CHECKLIST.md`](file:///C:/Users/sal/OneDrive/Desktop/repos/autoclipper/docs/GATEWAY_CHECKLIST.md)
- **Main Runbook**: [`docs/RUNBOOK.md`](file:///C:/Users/sal/OneDrive/Desktop/repos/autoclipper/docs/RUNBOOK.md)

## 🔐 Important Notes

- **The Gumloop API key is OPTIONAL** - You only need it if you want to trigger workflows programmatically from outside Gumloop
- **Inside Gumloop workflows**, you don't need the Gumloop API key - just add your Gemini key and service URLs
- **Never commit `.env`** to Git (already in `.gitignore`)
