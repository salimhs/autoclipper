"""
Utility: Cache manager for transcripts and tracking data.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class CacheManager:
    def __init__(self, cache_dir: str = "/tmp/cache", ttl_days: int = 7):
        self.cache_dir = Path(cache_dir)
        self.transcripts_dir = self.cache_dir / "transcripts"
        self.tracking_dir = self.cache_dir / "tracking"
        self.ttl = timedelta(days=ttl_days)
        
        # Create directories
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_key(self, video_url: str, duration_sec: float) -> str:
        """Generate cache key from video URL and duration."""
        content = f"{video_url}:{duration_sec}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_transcript(self, video_url: str, duration_sec: float) -> Optional[Dict[str, Any]]:
        """Retrieve cached transcript if exists and not expired."""
        key = self._generate_key(video_url, duration_sec)
        cache_file = self.transcripts_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check TTL
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_time > self.ttl:
            cache_file.unlink()  # Expired, delete
            return None
        
        with open(cache_file) as f:
            return json.load(f)
    
    def set_transcript(self, video_url: str, duration_sec: float, transcript: Dict[str, Any]):
        """Cache transcript data."""
        key = self._generate_key(video_url, duration_sec)
        cache_file = self.transcripts_dir / f"{key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(transcript, f)
    
    def get_tracking(self, video_url: str, duration_sec: float) -> Optional[Dict[str, Any]]:
        """Retrieve cached tracking data if exists and not expired."""
        key = self._generate_key(video_url, duration_sec)
        cache_file = self.tracking_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check TTL
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_time > self.ttl:
            cache_file.unlink()
            return None
        
        with open(cache_file) as f:
            return json.load(f)
    
    def set_tracking(self, video_url: str, duration_sec: float, tracking_data: Dict[str, Any]):
        """Cache tracking data."""
        key = self._generate_key(video_url, duration_sec)
        cache_file = self.tracking_dir / f"{key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(tracking_data, f)
    
    def cleanup_expired(self):
        """Remove all expired cache entries."""
        now = datetime.now()
        
        for cache_dir in [self.transcripts_dir, self.tracking_dir]:
            for cache_file in cache_dir.glob("*.json"):
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if now - file_time > self.ttl:
                    cache_file.unlink()
