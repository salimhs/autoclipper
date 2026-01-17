# AutoClipper Outputs

This directory contains all generated video clips organized by job.

## Structure

Each job creates a timestamped folder:
```
outputs/
├── 20260117_145800_youtube.com_watch_abc123ef/
│   ├── clip_001.mp4
│   ├── clip_002.mp4
│   ├── clip_003.mp4
│   ├── manifest.json
│   └── README.md
└── 20260117_150200_vimeo.com_456789_def456gh/
    ├── clip_001.mp4
    ├── manifest.json
    └── README.md
```

## Files

- **clip_XXX.mp4**: Generated video clips
- **manifest.json**: Job metadata and clip details
- **README.md**: Human-readable job summary

## Management

Use the CLI tool to manage outputs:

```bash
# List all jobs
python clipper.py --list

# View job details
python clipper.py --job-id abc123

# Clean up old jobs (30+ days)
python clipper.py --cleanup 30
```

## Storage

By default, clips are stored locally. For production:
1. Configure cloud storage (S3/GCS) in `.env`
2. Update `utils/output_manager.py` to upload instead of copy
3. Clips will be accessible via HTTPS URLs
