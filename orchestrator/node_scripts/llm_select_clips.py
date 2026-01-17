"""
Gumloop Node 4 (fallback): LLM clip selection.
This script is used when Gumloop's native LLM fails or for Gemini fallback.
"""

import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai.llm_provider import get_provider
from utils.logger import StructuredLogger


def main(transcript_uri: str, duration_sec: float, strategy: str, job_id: str) -> dict:
    """
    Generate EDL using selected LLM provider.
    """
    logger = StructuredLogger(job_id, "node_4")
    start_time = time.time()
    
    logger.info("Starting clip selection", strategy=strategy)
    
    # Load transcript
    transcript_path = transcript_uri.replace("file://", "")
    with open(transcript_path) as f:
        transcript_data = json.load(f)
    
    # Concatenate full text
    transcript_text = "\n".join(
        segment["text"] 
        for segment in transcript_data.get("segments", [])
    )
    
    try:
        # Get provider based on strategy
        provider = get_provider(strategy)
        
        # Generate EDL
        constraints = {
            "min_clip_length": 15,
            "max_clip_length": 90,
            "max_clips": 10,
            "require_strong_hook": True
        }
        
        edl = provider.generate_edl(transcript_text, duration_sec, constraints)
        
        duration = time.time() - start_time
        logger.timing("llm_clip_selection", duration, num_clips=len(edl.get("clips", [])))
        
        # Return as JSON string for validation node
        return {
            "raw_edl_json": json.dumps(edl)
        }
        
    except Exception as e:
        logger.error("Clip selection failed", error=str(e))
        raise


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(
        args["transcript_uri"],
        args["duration_sec"],
        args["strategy"],
        args["job_id"]
    )
    print(json.dumps(result))
