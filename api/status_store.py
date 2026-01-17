"""
Job status storage.
In production, replace with Redis or database.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import threading


class StatusStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_id: str, video_url: str, webhook_url: Optional[str] = None):
        """Create new job entry."""
        with self._lock:
            self._store[job_id] = {
                "job_id": job_id,
                "video_url": video_url,
                "webhook_url": webhook_url,
                "status": "pending",
                "progress": None,
                "clips": None,
                "error": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job by ID."""
        with self._lock:
            return self._store.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[str] = None,
        clips: Optional[list] = None,
        error: Optional[str] = None
    ):
        """Update job state."""
        with self._lock:
            if job_id not in self._store:
                raise ValueError(f"Job {job_id} not found")
            
            job = self._store[job_id]
            
            if status:
                job["status"] = status
            if progress:
                job["progress"] = progress
            if clips is not None:
                job["clips"] = clips
            if error:
                job["error"] = error
            
            job["updated_at"] = datetime.utcnow().isoformat()
    
    def list_jobs(self) -> list:
        """List all jobs."""
        with self._lock:
            return list(self._store.values())
