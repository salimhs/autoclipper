# Execution Order

## Fixed Workflow Sequence

### 1. URL Validation (Node 1)
- Validate video URL format
- Check platform support
- Verify accessibility

### 2. Download + Extract (Node 2)
- Download video with yt-dlp
- Extract audio (16kHz mono WAV)
- Extract metadata (duration, fps, resolution)

### 3. Parallel Processing (Nodes 3a & 3b)

**3a. WhisperX Transcription**
- Transcribe audio
- Align for word-level timestamps
- Generate confidence stats

**3b. Visual Tracking**
- Detect faces with MediaPipe
- Track positions across frames
- Generate crop paths

### 4. Gemini Clip Selection (Node 4)
- Analyze transcript
- Identify viral clip candidates
- Generate EDL with scores

### 5. Merge Render Recipe (Node 5)
- Combine EDL + word timestamps + crop paths
- Map subtitles to clip timeline
- Validate recipe schema

### 6. Dispatch GPU Render (Node 6)
- Send recipe to render worker
- Receive batch ID
- Begin polling

### 7. Collect Results (Node 7)
- Poll render worker status
- Retrieve completed clips
- Return ranked results

## Total Duration Estimate

- Nodes 1-2: ~30 seconds
- Nodes 3a-3b: ~2-5 minutes (GPU)
- Node 4: ~10-30 seconds
- Node 5: <5 seconds
- Nodes 6-7: ~3-10 minutes (GPU)

**Total**: ~6-16 minutes for typical video
