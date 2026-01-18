# Use official Python slim image for a small footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio/video processing (lightweight)
# Added git for whisperX installation
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (Railway uses PORT environment variable, usually 8080)
EXPOSE 8080

# Command to run the Job Controller
# Fixed: removed .py from module path
CMD ["uvicorn", "api.job_controller:app", "--host", "0.0.0.0", "--port", "8080"]
