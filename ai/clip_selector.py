"""
Gemini-based clip selection service.
Analyzes transcript and returns EDL with ranked clips.
"""

import json
import google.generativeai as genai
from pathlib import Path
from typing import Dict, Any


class ClipSelector:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Load prompts
        prompt_dir = Path(__file__).parent / "gemini_prompts"
        with open(prompt_dir / "clip_selection.txt") as f:
            self.clip_selection_prompt = f.read()
        with open(prompt_dir / "json_repair.txt") as f:
            self.json_repair_prompt = f.read()
    
    def select_clips(self, transcript_text: str, duration_sec: float) -> Dict[str, Any]:
        """
        Generate EDL from transcript using Gemini.
        
        Args:
            transcript_text: Full video transcript
            duration_sec: Video duration in seconds
            
        Returns:
            EDL dict matching schemas/edl.json
        """
        prompt = f"{self.clip_selection_prompt}\n\nTranscript:\n{transcript_text}\n\nDuration: {duration_sec} seconds"
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'response_mime_type': 'application/json'
                }
            )
            
            edl = json.loads(response.text)
            self._validate_edl(edl, duration_sec)
            return edl
            
        except json.JSONDecodeError as e:
            # Attempt JSON repair
            return self._repair_json(response.text, duration_sec)
    
    def _repair_json(self, broken_json: str, duration_sec: float) -> Dict[str, Any]:
        """Attempt to repair malformed JSON using Gemini."""
        repair_prompt = f"{self.json_repair_prompt}\n\n{broken_json}"
        
        response = self.model.generate_content(
            repair_prompt,
            generation_config={
                'temperature': 0.0,
                'response_mime_type': 'application/json'
            }
        )
        
        edl = json.loads(response.text)
        self._validate_edl(edl, duration_sec)
        return edl
    
    def _validate_edl(self, edl: Dict[str, Any], duration_sec: float):
        """Validate EDL structure and constraints."""
        assert 'clips' in edl, "EDL must have 'clips' field"
        
        for clip in edl['clips']:
            assert clip['start_sec'] >= 0, f"Clip {clip['clip_id']} has negative start"
            assert clip['end_sec'] <= duration_sec, f"Clip {clip['clip_id']} exceeds video duration"
            assert clip['start_sec'] < clip['end_sec'], f"Clip {clip['clip_id']} has invalid time range"
            assert 0 <= clip['score'] <= 1, f"Clip {clip['clip_id']} has invalid score"
