# Stage: builder - builds wheels for heavy deps
FROM python:3.11-slim AS builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential gcc git curl ca-certificates \
      ffmpeg libgl1 libglib2.0-0 pkg-config libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt requirements-runtime.txt
COPY requirements-worker.txt requirements-worker.txt

RUN python -m pip install --upgrade pip wheel setuptools && \
    pip wheel --wheel-dir=/wheels -r requirements-runtime.txt --no-cache-dir --prefer-binary && \
    pip wheel --wheel-dir=/wheels -r requirements-worker.txt --no-cache-dir --prefer-binary || true

# Stage: runtime - API only
FROM python:3.11-slim AS runtime

RUN useradd --create-home --no-log-init appuser
WORKDIR /app

COPY requirements-runtime.txt requirements-runtime.txt
COPY . /app

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-runtime.txt

ENV PYTHONPATH=/app
USER appuser
EXPOSE 8081
CMD uvicorn api.gumloop_gateway:app --host 0.0.0.0 --port ${PORT:-8081}
