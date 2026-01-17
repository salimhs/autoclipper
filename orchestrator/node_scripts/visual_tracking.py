"""
Gumloop Node 3b: Visual tracking with caching.
"""

import json
import sys
import time
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from perception.tracking import VisualTracker
from utils.logger import StructuredLogger
from utils.cache import CacheManager


def main(video_uri: str, video_url: str, width: int, height: int, job_id: str) -> dict:
    """Track faces and generate crop paths."""
    logger = StructuredLogger(job_id, "node_3b")
    cache = CacheManager()
    start_time = time.time()
    
    # Check cache
    cached = cache.get_tracking(video_url, width * height)  # Use resolution as part of key
    if cached:
        logger.info("Using cached tracking data")
        
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_tracking_")
        tracking_path = f"{output_dir}/tracking.json"
        crop_paths_path = f"{output_dir}/crop_paths.json"
        
        with open(tracking_path, 'w') as f:
            json.dump(cached["tracking"], f)
        with open(crop_paths_path, 'w') as f:
            json.dump(cached["crop_paths"], f)
        
        return {
            "tracking_uri": f"file://{tracking_path}",
            "crop_paths_uri": f"file://{crop_paths_path}"
        }
    
    logger.info("Starting visual tracking")
    
    video_path = video_uri.replace("file://", "")
    
    try:
        tracker = VisualTracker()
        
        # Track video
        tracking_data = tracker.track_video(video_path)
        logger.info("Tracking complete", frames_tracked=len(tracking_data["frames"]))
        
        # Generate crop paths
        crop_paths = tracker.generate_crop_paths(
            tracking_data,
            source_width=width,
            source_height=height
        )
        logger.info("Crop paths generated", keyframes=len(crop_paths))
        
        # Cache combined data
        cache_data = {
            "tracking": tracking_data,
            "crop_paths": {"crop_path": crop_paths}
        }
        cache.set_tracking(video_url, width * height, cache_data)
        
        # Save to files
        output_dir = tempfile.mkdtemp(prefix=f"autoclipper_{job_id}_tracking_")
        tracking_path = f"{output_dir}/tracking.json"
        crop_paths_path = f"{output_dir}/crop_paths.json"
        
        with open(tracking_path, 'w') as f:
            json.dump(tracking_data, f)
        with open(crop_paths_path, 'w') as f:
            json.dump({"crop_path": crop_paths}, f)
        
        duration = time.time() - start_time
        logger.timing("visual_tracking", duration)
        
        return {
            "tracking_uri": f"file://{tracking_path}",
            "crop_paths_uri": f"file://{crop_paths_path}"
        }
        
    except Exception as e:
        logger.error("Tracking failed", error=str(e))
        raise


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = main(
        args["video_uri"],
        args["video_url"],
        args["width"],
        args["height"],
        args["job_id"]
    )
    print(json.dumps(result))
