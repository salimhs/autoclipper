"""
WhisperX transcription service with word-level alignment.
"""

import json
from pathlib import Path
from typing import Dict, Any


class WhisperXRunner:
    def __init__(self, device: str = "cuda", compute_type: str = "float16"):
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.align_model = None
        self.metadata = None
    
    def load_model(self, model_name: str = "large-v2"):
        """Load WhisperX model."""
        import whisperx
        self.model = whisperx.load_model(
            model_name,
            self.device,
            compute_type=self.compute_type
        )
    
    def transcribe(self, audio_path: str, language: str = None) -> Dict[str, Any]:
        """
        Transcribe audio with word-level timestamps.
        
        Args:
            audio_path: Path to audio file (WAV, 16kHz mono recommended)
            language: Language code (None for auto-detect)
            
        Returns:
            Dict matching schemas/transcript.json
        """
        import whisperx
        
        if self.model is None:
            self.load_model()
        
        # Transcribe
        audio = whisperx.load_audio(audio_path)
        result = self.model.transcribe(audio, language=language, batch_size=16)
        
        # Align for word-level timestamps
        detected_language = result.get("language", language or "en")
        
        self.align_model, self.metadata = whisperx.load_align_model(
            language_code=detected_language,
            device=self.device
        )
        
        result = whisperx.align(
            result["segments"],
            self.align_model,
            self.metadata,
            audio,
            self.device,
            return_char_alignments=False
        )
        
        # Format to schema
        transcript = {
            "segments": []
        }
        
        for segment in result["segments"]:
            transcript["segments"].append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "words": [
                    {
                        "word": word["word"],
                        "start": word["start"],
                        "end": word["end"]
                    }
                    for word in segment.get("words", [])
                ]
            })
        
        return transcript
    
    def save_transcript(self, transcript: Dict[str, Any], output_path: str):
        """Save transcript to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)
