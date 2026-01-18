# Use official Python slim image for a small footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# Added build-essential and python3-dev for building packages from source
# Added libgl1 and libglib2.0-0 for opencv/mediapipe
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
COPY requirements.txt .

# Install Python dependencies
# Increased timeout for larger packages like torch/whisperX
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 8080

# Command to run the Job Controller
CMD ["uvicorn", "api.job_controller:app", "--host", "0.0.0.0", "--port", "8080"]
