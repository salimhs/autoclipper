# Docker Build & Deployment Guide

## Overview

This project uses a multi-stage Dockerfile to reduce the final image size and separate runtime dependencies from heavy worker/perception dependencies.

## Image Variants

### Runtime Image (API Only)
- **Target**: `runtime` (default)
- **Purpose**: Lightweight API server for Railway deployment
- **Size**: ~200-300MB
- **Dependencies**: FastAPI, Uvicorn, Pydantic, and light API deps only
- **Note**: Heavy ML libraries (whisperX, mediapipe, opencv) are lazy-loaded and will fail if endpoints are called without them

### Builder Image
- **Target**: `builder`
- **Purpose**: Intermediate stage for building Python wheels
- **Contains**: Build tools, compilers, and all dependencies

## Building Images

### Build Runtime Image (for API deployment)
```bash
docker build --target runtime -t autoclipper:runtime .
```

### Build Full Image (for local development/worker)
To build an image with all dependencies including heavy ML libs:
```bash
# Create a worker Dockerfile or install worker deps in runtime
docker build -t autoclipper:full -f Dockerfile.worker .
```

Or manually install worker deps in runtime:
```dockerfile
FROM autoclipper:runtime
USER root
RUN pip install --no-cache-dir -r requirements-worker.txt
USER appuser
```

## Running Containers

### Run Runtime API
```bash
docker run -e PORT=8081 -p 8081:8081 autoclipper:runtime
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8081/health

# API documentation
curl http://localhost:8081/docs
```

## Railway Deployment

The runtime image is optimized for Railway deployment:

1. **Automatic Build**: Railway will build the Docker image from the Dockerfile
2. **Size**: Runtime image is <500MB (well under Railway's 4GB limit)
3. **PORT Variable**: Railway automatically sets the PORT environment variable
4. **Entry Point**: `uvicorn api.gumloop_gateway:app --host 0.0.0.0 --port ${PORT:-8081}`

### Manual Deploy to Railway
```bash
# Build and tag
docker build --target runtime -t ghcr.io/salimhs/autoclipper:latest .

# Push to GHCR (GitHub Container Registry)
docker push ghcr.io/salimhs/autoclipper:latest

# Deploy on Railway using the prebuilt image
```

## GitHub Actions CI/CD

The `.github/workflows/build-and-push.yml` workflow automatically:
1. Builds the Docker image on push to `main` or `fix/*` branches
2. Pushes the image to GitHub Container Registry (GHCR)
3. Tags images as `latest`

To use the prebuilt image:
```bash
docker pull ghcr.io/salimhs/autoclipper:latest
```

## Lazy Loading Architecture

Heavy ML dependencies are lazy-loaded to reduce startup time and memory:

- **WhisperX**: Imported inside `WhisperXRunner.load_model()` and `transcribe()`
- **MediaPipe**: Imported inside `VisualTracker.__init__()`
- **OpenCV**: Imported inside `VisualTracker.track_video()`

This allows the API to start without these libraries installed. If endpoints requiring them are called, they will fail with ImportError.

## File Structure

```
.dockerignore           # Excludes venv, cache, tests from build context
requirements-runtime.txt # Lightweight API dependencies
requirements-worker.txt  # Heavy ML/perception dependencies
Dockerfile              # Multi-stage build configuration
```

## Troubleshooting

### Build Fails with SSL Certificate Error
This is common in CI environments with SSL interception. The runtime stage now uses normal pip install (not --no-index) to avoid this issue.

### Import Errors at Runtime
If you see `ModuleNotFoundError` for whisperx, mediapipe, or cv2:
- These are expected if you're running the runtime image
- Install worker deps: `pip install -r requirements-worker.txt`
- Or use the full worker image variant

### Image Too Large for Railway
- Runtime image should be <500MB
- Check `.dockerignore` is excluding unnecessary files
- Verify multi-stage build is working (builder artifacts not in final image)

## Development

For local development with all dependencies:
```bash
# Install all deps
pip install -r requirements-runtime.txt
pip install -r requirements-worker.txt

# Or use docker-compose
docker-compose up
```
