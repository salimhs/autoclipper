"""
Gumloop Node 3a: WhisperX transcription with caching.
"""

import json
import sys
import time
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from perception.whisperx_runner import WhisperXRunner
from utils.logger import StructuredLogger
from utils.cache import CacheManager


def main(audio_uri: str, video_url: str, duration_sec: float, job_id: str) -> dict:
    """Transcribe audio with WhisperX."""
    logger = StructuredLogger(job_id, "node_3a")
    cache = CacheManager()
    start_time = time.time()
    
    # Check cache first
    cached = cache.get_transcript(video_url, duration_sec)
    if cached:
        logger.info("Using cached transcript")
        
        # Write to temp file
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_transcript_")
        transcript_path = f"{output_dir}/transcript.json"
        
        with open(transcript_path, 'w') as f:
            json.dump(cached, f)
        
        return {
            "transcript_uri": f"file://{transcript_path}",
            "word_timeline_uri": f"file://{transcript_path}",  # Same file
            "confidence_stats": {"avg_confidence": 1.0, "cached": True}
        }
    
    logger.info("Starting WhisperX transcription")
    
    audio_path = audio_uri.replace("file://", "")
    
    try:
        runner = WhisperXRunner()
        transcript = runner.transcribe(audio_path)
        
        # Calculate confidence stats
        all_confidences = []
        for segment in transcript.get("segments", []):
            for word in segment.get("words", []):
                if "score" in word:
                    all_confidences.append(word["score"])
        
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        logger.info("Transcription complete", avg_confidence=avg_confidence)
        
        # Cache transcript
        cache.set_transcript(video_url, duration_sec, transcript)
        
        # Save to file
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_transcript_")
        transcript_path = f"{output_dir}/transcript.json"
        
        with open(transcript_path, 'w') as f:
            json.dump(transcript, f)
        
        duration = time.time() - start_time
        logger.timing("whisperx_transcription", duration)
        
        return {
            "transcript_uri": f"file://{transcript_path}",
            "word_timeline_uri": f"file://{transcript_path}",
            "confidence_stats": {
                "avg_confidence": avg_confidence,
                "total_words": len(all_confidences)
            }
        }
        
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(
        args["audio_uri"],
        args["video_url"],
        args["duration_sec"],
        args["job_id"]
    )
    print(json.dumps(result))
