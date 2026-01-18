# Full ML deployment Dockerfile
FROM python:3.11-slim

ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --no-log-init appuser
WORKDIR /app

# Install ALL system dependencies needed for ML + video processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    git curl ca-certificates \
    ffmpeg \
    libgl1-mesa-glx libglib2.0-0 \
    libsm6 libxext6 libxrender-dev \
    pkg-config libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Copy requirements first for layer caching
COPY requirements-runtime.txt requirements-runtime.txt
COPY requirements-worker.txt requirements-worker.txt

# Install Python dependencies
RUN python -m pip install --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements-runtime.txt && \
    pip install --no-cache-dir -r requirements-worker.txt

# Copy application code
COPY . /app

ENV PYTHONPATH=/app
USER appuser
EXPOSE 8081
CMD ["/bin/sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8081}"]
