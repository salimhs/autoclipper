"""
Gumloop Node 3c: Model Router.
Decides between Gumloop LLM (default) or Gemini fallback (long context).
"""

import json
import sys
from pathlib import Path
from utils.logger import StructuredLogger

# Token estimation constants
AVG_CHARS_PER_TOKEN = 4
GUMLOOP_MAX_TOKENS = 100000  # Assume Gumloop models have ~100K context
GEMINI_THRESHOLD = 80000  # Use Gemini if transcript > 80K tokens


def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text) // AVG_CHARS_PER_TOKEN


def main(transcript_uri: str, duration_sec: float, job_id: str) -> dict:
    """
    Route to best model based on transcript length.
    
    Strategy:
    - Gumloop LLM: transcript < 80K tokens (default, faster, cheaper)
    - Gemini fallback: transcript >= 80K tokens (long context support)
    """
    logger = StructuredLogger(job_id, "node_3c")
    
    # Load transcript to estimate length
    transcript_path = transcript_uri.replace("file://", "")
    with open(transcript_path) as f:
        transcript_data = json.load(f)
    
    # Concatenate all text
    full_text = " ".join(
        segment["text"] 
        for segment in transcript_data.get("segments", [])
    )
    
    estimated_tokens = estimate_tokens(full_text)
    logger.info("Token estimation", tokens=estimated_tokens, duration_sec=duration_sec)
    
    # Routing logic
    if estimated_tokens >= GEMINI_THRESHOLD:
        strategy = "gemini_fallback"
        reason = f"Transcript length ({estimated_tokens} tokens) exceeds Gumloop capacity"
        selected_model = "gemini-1.5-pro-latest"
        logger.info("Routing to Gemini", reason=reason)
    else:
        strategy = "gumloop_llm"
        reason = f"Transcript length ({estimated_tokens} tokens) within Gumloop capacity"
        selected_model = "gumloop_best_reasoning"
        logger.info("Routing to Gumloop LLM", reason=reason)
    
    return {
        "strategy": strategy,
        "reason": reason,
        "selected_model_name": selected_model
    }


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(
        args["transcript_uri"],
        args["duration_sec"],
        args["job_id"]
    )
    print(json.dumps(result))
