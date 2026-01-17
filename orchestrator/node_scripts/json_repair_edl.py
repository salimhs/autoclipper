"""
Gumloop Node 4c: Repair invalid EDL JSON.
"""

import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai.llm_provider import get_provider
from utils.logger import StructuredLogger


def main(raw_edl_json: str, validation_error: str, duration_sec: float, strategy: str, job_id: str) -> dict:
    """
    Attempt to repair invalid EDL.
    """
    logger = StructuredLogger(job_id, "node_4c")
    logger.info("Starting EDL repair", error=validation_error)
    
    try:
        provider = get_provider(strategy)
        
        # Use repair prompt
        repair_instructions = f"""The following EDL JSON has validation errors:

{validation_error}

Original JSON:
{raw_edl_json}

Rules for repair:
1. Fix ONLY JSON syntax and field errors
2. Do NOT invent or change timestamps
3. Remove clips that violate constraints (too short, too long, overlapping)
4. Keep all valid clips unchanged
5. Ensure all timestamps are within 0-{duration_sec} seconds
6. Return ONLY valid JSON matching the EDL schema

Required schema:
{{
  "clips": [
    {{
      "clip_id": "string",
      "start_sec": number,
      "end_sec": number,
      "title": "string",
      "hook_text": "string",
      "score": number (0.0-1.0),
      "reason": "string"
    }}
  ]
}}
"""
        
        repaired_edl = provider.repair_edl(repair_instructions, duration_sec)
        
        # Save repaired EDL
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_edl_repaired_")
        edl_path = f"{output_dir}/edl.json"
        
        with open(edl_path, 'w') as f:
            json.dump(repaired_edl, f, indent=2)
        
        logger.info("EDL repaired successfully", num_clips=len(repaired_edl.get("clips", [])))
        
        return {
            "edl_uri": f"file://{edl_path}"
        }
        
    except Exception as e:
        logger.error("EDL repair failed", error=str(e))
        raise


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(
        args["raw_edl_json"],
        args["validation_error"],
        args["duration_sec"],
        args["strategy"],
        args["job_id"]
    )
    print(json.dumps(result))
