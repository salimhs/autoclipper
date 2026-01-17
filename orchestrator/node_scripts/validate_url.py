"""
Gumloop Node 1: URL Validation.
Validates video URL format and platform support.
"""

import json
import sys
import re
from urllib.parse import urlparse
from utils.logger import StructuredLogger


SUPPORTED_PLATFORMS = {
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'vimeo.com': 'Vimeo',
    'dailymotion.com': 'Dailymotion',
    'twitch.tv': 'Twitch'
}


def validate_url(video_url: str, job_id: str) -> dict:
    """
    Validate video URL and detect platform.
    
    Returns:
        {video_url, valid, platform}
    """
    logger = StructuredLogger(job_id, "node_1")
    logger.info("Validating URL", url=video_url)
    
    try:
        parsed = urlparse(video_url)
        
        # Check valid URL structure
        if not parsed.scheme in ['http', 'https']:
            logger.error("Invalid URL scheme", scheme=parsed.scheme)
            return {
                "video_url": video_url,
                "valid": False,
                "platform": "unknown"
            }
        
        # Detect platform
        domain = parsed.netloc.lower().replace('www.', '')
        platform = "unknown"
        
        for supported_domain, platform_name in SUPPORTED_PLATFORMS.items():
            if supported_domain in domain:
                platform = platform_name
                break
        
        if platform == "unknown":
            logger.warning("Unsupported platform", domain=domain)
        
        valid = platform != "unknown"
        logger.info("Validation complete", valid=valid, platform=platform)
        
        return {
            "video_url": video_url,
            "valid": valid,
            "platform": platform
        }
        
    except Exception as e:
        logger.error("URL validation failed", error=str(e))
        return {
            "video_url": video_url,
            "valid": False,
            "platform": "unknown"
        }


if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    result = validate_url(args["video_url"], args["job_id"])
    print(json.dumps(result))
