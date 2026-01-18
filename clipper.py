"""
CLI tool for AutoClipper.
Simple command-line interface for processing videos.
"""

import argparse
import sys
import json
import time
from pathlib import Path
from utils.output_manager import OutputManager


def main():
    parser = argparse.ArgumentParser(
        description="AutoClipper - AI-powered video clip generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a YouTube video
  python clipper.py --url "https://youtube.com/watch?v=..."
  
  # Specify output directory
  python clipper.py --url "https://youtube.com/..." --output "./my_clips"
  
  # List all generated jobs
  python clipper.py --list
  
  # Get details of a specific job
  python clipper.py --job-id abc123
        """
    )
    
    parser.add_argument(
        "--url",
        help="Video URL to process (YouTube, Vimeo, Twitch, etc.)"
    )
    
    parser.add_argument(
        "--output",
        default="./outputs",
        help="Output directory for clips (default: ./outputs)"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all generated jobs"
    )
    
    parser.add_argument(
        "--job-id",
        help="Get details of a specific job"
    )
    
    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="Remove jobs older than DAYS"
    )
    
    args = parser.parse_args()
    
    # Initialize output manager
    output_mgr = OutputManager(args.output)
    
    # Handle different commands
    if args.list:
        list_jobs(output_mgr)
    elif args.job_id:
        show_job(output_mgr, args.job_id)
    elif args.cleanup:
        cleanup_jobs(output_mgr, args.cleanup)
    elif args.url:
        process_video(args.url, output_mgr)
    else:
        parser.print_help()
        sys.exit(1)


def list_jobs(output_mgr: OutputManager):
    """List all saved jobs."""
    jobs = output_mgr.list_jobs()
    
    if not jobs:
        print("No jobs found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(jobs)} job(s):\n")
    
    for job in jobs:
        print(f"Job ID: {job['job_id'][:16]}...")
        print(f"  Timestamp: {job['timestamp']}")
        print(f"  Video: {job['video_url'][:60]}...")
        print(f"  Clips: {job['total_clips']}")
        print(f"  Directory: {job['job_dir']}")
        print()


def show_job(output_mgr: OutputManager, job_id: str):
    """Show details of a specific job."""
    job = output_mgr.get_job(job_id)
    
    if not job:
        print(f"Job {job_id} not found.")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"Job Details:\n")
    print(json.dumps(job, indent=2))


def cleanup_jobs(output_mgr: OutputManager, days: int):
    """Remove old jobs."""
    print(f"Removing jobs older than {days} days...")
    removed = output_mgr.cleanup_old_jobs(days)
    print(f"Removed {removed} job(s).")


def process_video(url: str, output_mgr: OutputManager):
    """Process a video URL."""
    print(f"\n{'='*80}")
    print(f"Processing video: {url}\n")
    print("NOTE: This requires the API server to be running.")
    print("Start it with: python api/job_controller.py\n")
    
    # Determine backend URL (local or cloud)
    backend_url = os.environ.get("CLI_BACKEND_URL", "http://localhost:8081")
    
    try:
        # Submit job
        response = requests.post(
            f"{backend_url.rstrip('/')}/jobs",
            json={"video_url": url},
            timeout=10
        )
        response.raise_for_status()
        
        job_id = response.json()["job_id"]
        print(f"Job submitted: {job_id}")
        print("Waiting for completion...\n")
        
        # Poll for completion
        while True:
            status_response = requests.get(
                f"http://localhost:8081/jobs/{job_id}",
                timeout=10
            )
            status_response.raise_for_status()
            status = status_response.json()
            
            print(f"Status: {status['status']}", end="\r")
            
            if status["status"] == "completed":
                print("\n\n[SUCCESS] Job completed!")
                
                clips = status.get("clips", [])
                print(f"\nGenerated {len(clips)} clips:")
                for clip in clips:
                    # Handle both path and mp4_url
                    path = clip.get('path') or clip.get('mp4_url') or "N/A"
                    print(f"  - {clip.get('clip_id', 'unknown')}: {path}")
                
                print(f"\nAll clips saved to your local outputs/ directory (handled by Render Worker).")
                break
            
            elif status["status"] == "failed":
                print(f"\n\n[FAILED] Job failed: {status.get('error', 'Unknown error')}")
                sys.exit(1)
            
            time.sleep(2)
    
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to API server.")
        print("Make sure the server is running: python api/job_controller.py")
        sys.exit(1)
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
