# Failure Handling Rules

## Gemini Output Invalid

**Condition**: JSON parsing fails  
**Action**: Run JSON repair prompt  
**Max Retries**: 2  
**Fallback**: Return error with raw output

## No Face Detected

**Condition**: Visual tracking finds no faces  
**Action**: Use center crop fallback  
**Implementation**: `(width - crop_w) // 2`

## Diarization Missing

**Condition**: WhisperX diarization fails  
**Action**: Ignore speaker logic  
**Impact**: All text treated as single speaker

## Clip Below Minimum Length

**Condition**: `end_sec - start_sec < MIN_CLIP_LENGTH`  
**Action**: Discard clip  
**Default MIN_CLIP_LENGTH**: 15 seconds

## Zero Clips Found

**Condition**: Gemini returns empty clips array  
**Action**: Explicit failure  
**Reason**: "No viable clips found in transcript"

## URL Validation Failed

**Condition**: Invalid or unreachable URL  
**Action**: Immediate failure  
**Status**: `status=failed, error="Invalid URL"`

## Download Failed

**Condition**: yt-dlp error  
**Action**: Return error with platform-specific guidance  
**Common Issues**: Private video, geo-blocked, deleted

## Render Worker Timeout

**Condition**: No response after 10 minutes  
**Action**: Mark job as failed  
**Retry**: Client responsibility
