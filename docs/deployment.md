# Deployment Guide

## Local Development

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start Render Worker
```bash
cd render
python worker.py
```

### 4. Start API Server
```bash
cd api
python job_controller.py
```

## Production Deployment

### Render Worker (Modal/RunPod)

**Modal**:
```python
import modal
stub = modal.Stub("autoclipper-render")

@stub.function(gpu="A10G", image=modal.Image.debian_slim().pip_install_from_requirements("requirements.txt"))
def render_clip(...):
    # See render/worker.py
```

**RunPod**:
- Deploy as serverless endpoint
- Use GPU instances (A4000+)
- Set 10-minute timeout

### API Service (Cloud Run / ECS)

**Docker**:
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY api/ /app/
CMD ["uvicorn", "job_controller:app", "--host", "0.0.0.0"]
```

### Gumloop Configuration

1. Import `orchestrator/gumloop_flow.json`
2. Configure node scripts
3. Set environment variables
4. Test workflow

## Required Services

- **GPU Compute**: Modal, RunPod, or Lambda Labs
- **Storage**: S3, GCS, or Azure Blob
- **Database**: Redis or PostgreSQL
- **API Keys**: Gemini API, Gumloop
