"""
Gumloop Node 2: Download video and extract audio.
Uses yt-dlp for download, ffmpeg for audio extraction.
"""

import json
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from utils.logger import StructuredLogger
from utils.retry import retry_with_backoff


@retry_with_backoff(max_retries=3, base_delay=2.0)
def download_video(video_url: str, output_dir: str) -> str:
    """Download video using yt-dlp."""
    cmd = [
        'yt-dlp',
        '-f', 'best[ext=mp4]',
        '-o', f'{output_dir}/video.mp4',
        video_url
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return f"{output_dir}/video.mp4"


def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract audio as 16kHz mono WAV."""
    audio_path = f"{output_dir}/audio.wav"
    
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',
        '-ar', '16000',  # 16kHz
        '-ac', '1',  # Mono
        audio_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_path


def get_video_metadata(video_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        video_path
    ]
    
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    # Extract video stream metadata
    video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    
    return {
        'duration_sec': float(data['format']['duration']),
        'fps': eval(video_stream['r_frame_rate']),  # "30/1" -> 30.0
        'width': int(video_stream['width']),
        'height': int(video_stream['height'])
    }


def main(video_url: str, job_id: str) -> dict:
    """Download and extract."""
    logger = StructuredLogger(job_id, "node_2")
    start_time = time.time()
    
    logger.info("Starting download", url=video_url)
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_")
    
    try:
        # Download video
        video_path = download_video(video_url, temp_dir)
        logger.info("Video downloaded", path=video_path)
        
        # Extract audio
        audio_path = extract_audio(video_path, temp_dir)
        logger.info("Audio extracted", path=audio_path)
        
        # Get metadata
        metadata = get_video_metadata(video_path)
        logger.info("Metadata extracted", metadata=metadata)
        
        duration = time.time() - start_time
        logger.timing("download_extract", duration)
        
        return {
            "video_uri": f"file://{video_path}",
            "audio_uri": f"file://{audio_path}",
            **metadata
        }
        
    except Exception as e:
        logger.error("Download/extract failed", error=str(e))
        raise


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(args["video_url"], args["job_id"])
    print(json.dumps(result))
