# api/status_store.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import threading
import time


@dataclass
class JobRecord:
  job_id: str
  status: str = "queued"         # queued | processing | completed | failed
  progress: float = 0.0          # 0..1
  error: Optional[str] = None
  created_at: float = field(default_factory=time.time)
  updated_at: float = field(default_factory=time.time)
  payload: Dict[str, Any] = field(default_factory=dict)   # input params
  result: Dict[str, Any] = field(default_factory=dict)    # clips, etc.


class StatusStore:
  """
  Minimal in-memory store for hackathon.
  Swap to MongoDB/Redis later if needed.
  """
  def __init__(self):
    self._lock = threading.Lock()
    self._jobs: Dict[str, JobRecord] = {}

  def create_job(self, job_id: str, payload: Optional[Dict[str, Any]] = None) -> JobRecord:
    with self._lock:
      rec = JobRecord(job_id=job_id, payload=payload or {})
      self._jobs[job_id] = rec
      return rec

  def get_job(self, job_id: str) -> Optional[JobRecord]:
    with self._lock:
      return self._jobs.get(job_id)

  def update_job(
    self,
    job_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    error: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
  ) -> Optional[JobRecord]:
    with self._lock:
      rec = self._jobs.get(job_id)
      if not rec:
        return None
      if status is not None:
        rec.status = status
      if progress is not None:
        rec.progress = float(progress)
      if error is not None:
        rec.error = error
      if result is not None:
        rec.result = result
      rec.updated_at = time.time()
      return rec

  def as_dict(self, rec: JobRecord) -> Dict[str, Any]:
    return {
      "job_id": rec.job_id,
      "status": rec.status,
      "progress": rec.progress,
      "error": rec.error,
      "created_at": rec.created_at,
      "updated_at": rec.updated_at,
      **rec.payload,
      **rec.result,
    }
