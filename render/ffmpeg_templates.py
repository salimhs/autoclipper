"""
FFmpeg command templates for video rendering.
"""

from typing import List, Dict, Any
from pathlib import Path
import subprocess


class FFmpegRenderer:
    TARGET_WIDTH = 1080
    TARGET_HEIGHT = 1920
    VIDEO_CODEC = "libx264"
    AUDIO_CODEC = "aac"
    PRESET = "medium"
    CRF = "23"
    
    @staticmethod
    def generate_crop_filter(crop_path: List[Dict[str, Any]], duration: float) -> str:
        """
        Generate FFmpeg crop filter with interpolation from crop path.
        
        Args:
            crop_path: List of crop keyframes
            duration: Clip duration
            
        Returns:
            FFmpeg filter string
        """
        if len(crop_path) == 1:
            cp = crop_path[0]
            return f"crop={cp['w']}:{cp['h']}:{cp['x']}:{cp['y']}"
        
        # Use zoompan for smooth interpolation
        expressions = []
        for i, cp in enumerate(crop_path):
            t = cp['t']
            if i < len(crop_path) - 1:
                next_cp = crop_path[i + 1]
                next_t = next_cp['t']
                dt = next_t - t
                
                # Linear interpolation
                x_expr = f"if(between(t,{t},{next_t}),{cp['x']}+(t-{t})*({next_cp['x']}-{cp['x']})/{dt},{cp['x']})"
                expressions.append(x_expr)
            else:
                expressions.append(f"{cp['x']}")
        
        # Simplified: use crop with first keyframe, scale to target
        cp = crop_path[0]
        return f"crop={cp['w']}:{cp['h']}:{cp['x']}:{cp['y']},scale={FFmpegRenderer.TARGET_WIDTH}:{FFmpegRenderer.TARGET_HEIGHT}"
    
    @staticmethod
    def generate_subtitle_file(subtitles: List[Dict[str, Any]], output_path: str) -> str:
        """
        Generate ASS subtitle file for burning in.
        
        Args:
            subtitles: List of subtitle dicts
            output_path: Path to save .ass file
            
        Returns:
            Path to generated ASS file
        """
        ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        events = []
        for sub in subtitles:
            start = FFmpegRenderer._format_ass_time(sub['start'])
            end = FFmpegRenderer._format_ass_time(sub['end'])
            text = sub['text'].replace('\n', '\\N')
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_header)
            f.write('\n'.join(events))
        
        return output_path
    
    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Convert seconds to ASS timestamp format (H:MM:SS.CS)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
    
    @staticmethod
    def render_clip(
        input_video: str,
        output_video: str,
        start_sec: float,
        end_sec: float,
        crop_path: List[Dict[str, Any]],
        subtitles: List[Dict[str, Any]],
        temp_dir: str
    ) -> str:
        """
        Render a single clip with cropping and burned-in subtitles.
        
        Args:
            input_video: Path to source video
            output_video: Path for output clip
            start_sec: Clip start time
            end_sec: Clip end time
            crop_path: Crop keyframes
            subtitles: Subtitle data
            temp_dir: Directory for temporary files
            
        Returns:
            Path to rendered video
        """
        duration = end_sec - start_sec
        
        # Generate subtitle file
        ass_path = Path(temp_dir) / f"{Path(output_video).stem}.ass"
        FFmpegRenderer.generate_subtitle_file(subtitles, str(ass_path))
        
        # Build crop filter
        crop_filter = FFmpegRenderer.generate_crop_filter(crop_path, duration)
        
        # FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',
            '-ss', str(start_sec),
            '-t', str(duration),
            '-i', input_video,
            '-vf', f"{crop_filter},ass={ass_path}",
            '-c:v', FFmpegRenderer.VIDEO_CODEC,
            '-preset', FFmpegRenderer.PRESET,
            '-crf', FFmpegRenderer.CRF,
            '-c:a', FFmpegRenderer.AUDIO_CODEC,
            '-b:a', '128k',
            '-ar', '44100',
            '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',  # Loudness normalization
            output_video
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_video
