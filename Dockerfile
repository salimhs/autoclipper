# Use official Python slim image for a small footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-full.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=100 -r requirements-full.txt

# Copy the rest of the application code
COPY . .

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app

# Expose the port (Railway uses PORT environment variable)
EXPOSE 8081

# Command to run the Gumloop Gateway API using the shell to expand $PORT
CMD uvicorn api.gumloop_gateway:app --host 0.0.0.0 --port ${PORT:-8081}
