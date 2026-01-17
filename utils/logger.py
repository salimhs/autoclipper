"""
Utility: Structured JSON logger for distributed workflow debugging.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredLogger:
    def __init__(self, job_id: str, node_id: Optional[str] = None, log_dir: str = "/tmp/logs"):
        self.job_id = job_id
        self.node_id = node_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file handler
        self.log_file = self.log_dir / f"{job_id}.jsonl"
        
    def _log(self, level: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Write structured log entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": self.job_id,
            "node_id": self.node_id,
            "level": level,
            "message": message,
            "metadata": metadata or {}
        }
        
        # Write to file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Also print to stdout for Gumloop
        print(json.dumps(entry), file=sys.stdout, flush=True)
    
    def info(self, message: str, **metadata):
        self._log("INFO", message, metadata)
    
    def warning(self, message: str, **metadata):
        self._log("WARNING", message, metadata)
    
    def error(self, message: str, **metadata):
        self._log("ERROR", message, metadata)
    
    def debug(self, message: str, **metadata):
        self._log("DEBUG", message, metadata)
    
    def timing(self, operation: str, duration_sec: float, **metadata):
        """Log timing data for performance analysis."""
        self._log("TIMING", f"{operation} completed", {
            **metadata,
            "operation": operation,
            "duration_sec": duration_sec
        })
