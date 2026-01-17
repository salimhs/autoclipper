"""
Gumloop Node 4b: Validate EDL against schema and constraints.
"""

import json
import sys
import jsonschema
import tempfile
from pathlib import Path
from utils.logger import StructuredLogger


def load_schema() -> dict:
    """Load EDL JSON schema."""
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "edl.json"
    with open(schema_path) as f:
        return json.load(f)


def check_overlaps(clips: list) -> list:
    """
    Check for temporal overlaps between clips.
    Returns list of overlap errors.
    """
    errors = []
    sorted_clips = sorted(clips, key=lambda c: c["start_sec"])
    
    for i in range(len(sorted_clips) - 1):
        clip1 = sorted_clips[i]
        clip2 = sorted_clips[i + 1]
        
        if clip1["end_sec"] > clip2["start_sec"]:
            errors.append(
                f"Clips '{clip1['clip_id']}' and '{clip2['clip_id']}' overlap: "
                f"[{clip1['start_sec']}-{clip1['end_sec']}] vs [{clip2['start_sec']}-{clip2['end_sec']}]"
            )
    
    return errors


def validate_constraints(edl: dict, duration_sec: float, transcript_uri: str, logger) -> list:
    """
    Validate EDL business constraints.
    Returns list of validation errors.
    """
    errors = []
    clips = edl.get("clips", [])
    
    # Check minimum quality (if we have confidence stats)
    transcript_path = transcript_uri.replace("file://", "")
    with open(transcript_path) as f:
        transcript_data = json.load(f)
    
    MIN_CONFIDENCE = 0.75
    MIN_CLIP_LENGTH = 15
    MAX_CLIP_LENGTH = 90
    
    for clip in clips:
        # Check timestamp bounds
        if clip["start_sec"] < 0:
            errors.append(f"Clip '{clip['clip_id']}' has negative start time")
        
        if clip["end_sec"] > duration_sec:
            errors.append(f"Clip '{clip['clip_id']}' exceeds video duration ({duration_sec}s)")
        
        if clip["start_sec"] >= clip["end_sec"]:
            errors.append(f"Clip '{clip['clip_id']}' has invalid time range")
        
        # Check clip length
        length = clip["end_sec"] - clip["start_sec"]
        if length < MIN_CLIP_LENGTH:
            errors.append(f"Clip '{clip['clip_id']}' too short ({length:.1f}s < {MIN_CLIP_LENGTH}s)")
        
        if length > MAX_CLIP_LENGTH:
            errors.append(f"Clip '{clip['clip_id']}' too long ({length:.1f}s > {MAX_CLIP_LENGTH}s)")
        
        # Check score range
        if not (0 <= clip.get("score", 0) <= 1):
            errors.append(f"Clip '{clip['clip_id']}' has invalid score")
        
        # Check transcription quality for this clip
        clip_words = []
        for segment in transcript_data.get("segments", []):
            for word in segment.get("words", []):
                if clip["start_sec"] <= word["start"] <= clip["end_sec"]:
                    if "score" in word:
                        clip_words.append(word["score"])
        
        if clip_words:
            avg_confidence = sum(clip_words) / len(clip_words)
            if avg_confidence < MIN_CONFIDENCE:
                errors.append(
                    f"Clip '{clip['clip_id']}' has low transcription quality "
                    f"(confidence {avg_confidence:.2f} < {MIN_CONFIDENCE})"
                )
    
    # Check for overlaps
    overlap_errors = check_overlaps(clips)
    errors.extend(overlap_errors)
    
    return errors


def main(raw_edl_json: str, duration_sec: float, transcript_uri: str, job_id: str) -> dict:
    """
    Validate EDL JSON.
    """
    logger = StructuredLogger(job_id, "node_4b")
    logger.info("Starting EDL validation")
    
    try:
        # Parse JSON
        edl = json.loads(raw_edl_json)
        logger.info("JSON parsed successfully")
        
        # Validate against schema
        schema = load_schema()
        jsonschema.validate(edl, schema)
        logger.info("Schema validation passed")
        
        # Validate constraints
        constraint_errors = validate_constraints(edl, duration_sec, transcript_uri, logger)
        
        if constraint_errors:
            error_msg = "; ".join(constraint_errors)
            logger.warning("Constraint validation failed", errors=constraint_errors)
            
            return {
                "valid": False,
                "edl_uri": "",
                "validation_error": error_msg
            }
        
        # All validations passed - save EDL
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_edl_")
        edl_path = f"{output_dir}/edl.json"
        
        with open(edl_path, 'w') as f:
            json.dump(edl, f, indent=2)
        
        logger.info("EDL validation passed", num_clips=len(edl.get("clips", [])))
        
        return {
            "valid": True,
            "edl_uri": f"file://{edl_path}",
            "validation_error": ""
        }
        
    except json.JSONDecodeError as e:
        logger.error("JSON parse error", error=str(e))
        return {
            "valid": False,
            "edl_uri": "",
            "validation_error": f"Invalid JSON: {str(e)}"
        }
    
    except jsonschema.ValidationError as e:
        logger.error("Schema validation error", error=str(e))
        return {
            "valid": False,
            "edl_uri": "",
            "validation_error": f"Schema validation failed: {e.message}"
        }
    
    except Exception as e:
        logger.error("Validation failed", error=str(e))
        return {
            "valid": False,
            "edl_uri": "",
            "validation_error": str(e)
        }


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(
        args["raw_edl_json"],
        args["duration_sec"],
        args["transcript_uri"],
        args["job_id"]
    )
    print(json.dumps(result))
