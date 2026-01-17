"""
Gumloop Node 5: Merge render recipe.
Combines EDL, word timestamps, and crop paths into render recipe.
"""

import json
import sys
from pathlib import Path


def load_json(uri: str) -> dict:
    """Load JSON from file URI."""
    path = uri.replace("file://", "")
    with open(path) as f:
        return json.load(f)


def merge_render_recipe(edl_uri: str, word_timeline_uri: str, crop_paths_uri: str, video_uri: str) -> dict:
    """
    Merge all data into render recipe.
    
    Returns:
        Dict matching schemas/render_recipe.json
    """
    edl = load_json(edl_uri)
    transcript = load_json(word_timeline_uri)
    crop_paths = load_json(crop_paths_uri)
    
    recipe = {
        "video_uri": video_uri,
        "clips": []
    }
    
    for clip in edl["clips"]:
        # Extract clip-relative subtitles
        subtitles = extract_subtitles(transcript, clip["start_sec"], clip["end_sec"])
        
        # Extract clip-relative crop path
        crop_path = extract_crop_path(crop_paths, clip["start_sec"], clip["end_sec"])
        
        recipe["clips"].append({
            "clip_id": clip["clip_id"],
            "start_sec": clip["start_sec"],
            "end_sec": clip["end_sec"],
            "crop_path": crop_path,
            "subtitles": subtitles
        })
    
    return recipe


def extract_subtitles(transcript: dict, start_sec: float, end_sec: float) -> list:
    """Extract word-level subtitles for clip timerange."""
    subtitles = []
    
    for segment in transcript["segments"]:
        for word in segment.get("words", []):
            word_start = word["start"]
            word_end = word["end"]
            
            if word_start >= start_sec and word_end <= end_sec:
                # Convert to clip-relative time
                subtitles.append({
                    "start": word_start - start_sec,
                    "end": word_end - start_sec,
                    "text": word["word"]
                })
    
    return subtitles


def extract_crop_path(tracking: dict, start_sec: float, end_sec: float) -> list:
    """Extract crop path keyframes for clip timerange."""
    crop_path = []
    
    for frame in tracking.get("frames", []):
        t = frame["timestamp"]
        
        if start_sec <= t <= end_sec:
            # Find crop path entry (assuming tracking has crop_path field)
            # Or compute from detections
            if frame.get("detections"):
                det = frame["detections"][0]
                bbox = det["bbox"]
                
                crop_path.append({
                    "t": t - start_sec,
                    "x": bbox["x"],
                    "y": bbox["y"],
                    "w": bbox["w"],
                    "h": bbox["h"]
                })
    
    # Fallback: center crop
    if not crop_path:
        crop_path = [{
            "t": 0.0,
            "x": 420,  # Assuming 1920x1080, crop to 1080x1920
            "y": 0,
            "w": 1080,
            "h": 1920
        }]
    
    return crop_path


if __name__ == "__main__":
    # Gumloop passes args as JSON
    args = json.loads(sys.argv[1])
    
    recipe = merge_render_recipe(
        args["edl_uri"],
        args["word_timeline_uri"],
        args["crop_paths_uri"],
        args["video_uri"]
    )
    
    # Output to file
    output_path = "/tmp/render_recipe.json"
    with open(output_path, 'w') as f:
        json.dump(recipe, f, indent=2)
    
    # Return result
    print(json.dumps({"render_recipe_uri": f"file://{output_path}"}))
