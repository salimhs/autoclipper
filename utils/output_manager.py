"""
Output Manager: Automatically collect and organize generated clips.
Moves clips from temp directories to permanent storage with metadata.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class OutputManager:
    """Manages permanent storage of generated clips."""
    
    def __init__(self, base_output_dir: str = None):
        """
        Initialize output manager.
        
        Args:
            base_output_dir: Base directory for outputs (default: ./outputs)
        """
        if base_output_dir is None:
            # Default to outputs/ in project root
            project_root = Path(__file__).parent.parent
            base_output_dir = project_root / "outputs"
        
        self.base_dir = Path(base_output_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"OutputManager initialized: {self.base_dir}")
    
    def save_job_results(
        self,
        job_id: str,
        video_url: str,
        clips: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Save all clips from a job to permanent storage.
        
        Args:
            job_id: Unique job identifier
            video_url: Original video URL
            clips: List of clip data with temp paths
            metadata: Additional metadata (strategy, model, etc.)
        
        Returns:
            {
                "job_dir": "path/to/job/folder",
                "clips": [...],
                "manifest_path": "path/to/manifest.json"
            }
        """
        # Create job directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_name = self._sanitize_filename(video_url)[:50]  # Truncate long URLs
        job_dir = self.base_dir / f"{timestamp}_{job_name}_{job_id[:8]}"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving job results to: {job_dir}")
        
        # Copy clips to permanent storage
        saved_clips = []
        for i, clip in enumerate(clips):
            clip_id = clip.get("clip_id", f"clip_{i+1:03d}")
            temp_path = clip.get("mp4_url", "").replace("file://", "")
            
            if not temp_path or not Path(temp_path).exists():
                logger.warning(f"Clip {clip_id} not found at {temp_path}, skipping")
                continue
            
            # Copy to permanent location
            permanent_path = job_dir / f"{clip_id}.mp4"
            shutil.copy2(temp_path, permanent_path)
            
            saved_clips.append({
                "clip_id": clip_id,
                "filename": permanent_path.name,
                "path": str(permanent_path),
                "score": clip.get("score", 0.0),
                "size_mb": permanent_path.stat().st_size / (1024 * 1024)
            })
            
            logger.info(f"Saved clip: {clip_id} -> {permanent_path.name}")
        
        # Create manifest file
        manifest = {
            "job_id": job_id,
            "video_url": video_url,
            "timestamp": timestamp,
            "total_clips": len(saved_clips),
            "clips": saved_clips,
            "metadata": metadata or {}
        }
        
        manifest_path = job_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Manifest saved: {manifest_path}")
        
        # Create README for easy browsing
        self._create_readme(job_dir, manifest)
        
        return {
            "job_dir": str(job_dir),
            "clips": saved_clips,
            "manifest_path": str(manifest_path)
        }
    
    def _create_readme(self, job_dir: Path, manifest: Dict[str, Any]):
        """Create a human-readable README in the job directory."""
        readme_path = job_dir / "README.md"
        
        content = f"""# AutoClipper Job Results

**Job ID**: `{manifest['job_id']}`  
**Video URL**: {manifest['video_url']}  
**Generated**: {manifest['timestamp']}  
**Total Clips**: {manifest['total_clips']}

## Clips

"""
        
        for clip in manifest['clips']:
            content += f"### {clip['clip_id']}\n"
            content += f"- **File**: `{clip['filename']}`\n"
            content += f"- **Score**: {clip['score']:.2f}\n"
            content += f"- **Size**: {clip['size_mb']:.1f} MB\n\n"
        
        if manifest.get('metadata'):
            content += "\n## Metadata\n\n"
            content += f"```json\n{json.dumps(manifest['metadata'], indent=2)}\n```\n"
        
        with open(readme_path, 'w') as f:
            f.write(content)
    
    def _sanitize_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        # Remove URL scheme
        text = text.replace("https://", "").replace("http://", "")
        # Replace invalid chars
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, "_")
        return text
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all saved jobs."""
        jobs = []
        
        for job_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if not job_dir.is_dir():
                continue
            
            manifest_path = job_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            jobs.append({
                "job_id": manifest["job_id"],
                "timestamp": manifest["timestamp"],
                "video_url": manifest["video_url"],
                "total_clips": manifest["total_clips"],
                "job_dir": str(job_dir)
            })
        
        return jobs
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get details of a specific job."""
        for job_dir in self.base_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            manifest_path = job_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            if manifest["job_id"] == job_id:
                return manifest
        
        return None
    
    def cleanup_old_jobs(self, days: int = 30):
        """Remove jobs older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        removed = 0
        
        for job_dir in self.base_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            # Check directory modification time
            if job_dir.stat().st_mtime < cutoff:
                shutil.rmtree(job_dir)
                removed += 1
                logger.info(f"Removed old job: {job_dir.name}")
        
        logger.info(f"Cleanup complete: {removed} jobs removed")
        return removed
