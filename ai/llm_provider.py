"""
LLM Provider Interface and Implementations.
Abstracts Gumloop vs Gemini LLM providers.
"""

import json
import os
from typing import Dict, Any
from abc import ABC, abstractmethod
import google.generativeai as genai
from pathlib import Path


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_edl(self, transcript_text: str, duration_sec: float, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Generate EDL from transcript."""
        pass
    
    @abstractmethod
    def repair_edl(self, repair_instructions: str, duration_sec: float) -> Dict[str, Any]:
        """Repair invalid EDL."""
        pass


class GumloopProvider(LLMProvider):
    """
    Gumloop LLM provider (proxy/documentation).
    Actual Gumloop LLM calls happen in the Gumloop workflow itself.
    This is used when calling from custom scripts.
    """
    
    def generate_edl(self, transcript_text: str, duration_sec: float, constraints: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "GumloopProvider is a proxy. Gumloop LLM calls happen in workflow nodes, "
            "not in Python code. Use GeminiProvider for fallback."
        )
    
    def repair_edl(self, repair_instructions: str, duration_sec: float) -> Dict[str, Any]:
        raise NotImplementedError("GumloopProvider does not support direct calls")


class GeminiProvider(LLMProvider):
    """
    Gemini AI provider with 2-stage pipeline.
    Stage 1: Chunked candidate discovery
    Stage 2: Global selection and ranking
    """
    
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Load prompts
        prompt_dir = Path(__file__).parent / "gemini_prompts"
        with open(prompt_dir / "candidate_discovery.txt") as f:
            self.candidate_prompt = f.read()
        with open(prompt_dir / "global_rerank.txt") as f:
            self.rerank_prompt = f.read()
        with open(prompt_dir / "edl_repair_strict.txt") as f:
            self.repair_prompt = f.read()
    
    def generate_edl(self, transcript_text: str, duration_sec: float, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        2-stage pipeline for EDL generation.
        """
        # Stage 1: Discover candidates from chunks
        candidates = self._discover_candidates(transcript_text, duration_sec, constraints)
        
        # Stage 2: Global selection and ranking
        final_edl = self._global_selection(candidates, duration_sec, constraints)
        
        return final_edl
    
    def _discover_candidates(self, transcript_text: str, duration_sec: float, constraints: Dict[str, Any]) -> list:
        """Stage 1: Chunk transcript and find candidates."""
        # Simple chunking by token limit (very rough)
        CHUNK_SIZE = 20000  # chars
        chunks = [transcript_text[i:i+CHUNK_SIZE] for i in range(0, len(transcript_text), CHUNK_SIZE)]
        
        all_candidates = []
        
        for i, chunk in enumerate(chunks):
            prompt = f"""{self.candidate_prompt}

Transcript chunk ({i+1}/{len(chunks)}):
{chunk}

Video duration: {duration_sec} seconds
Min clip length: {constraints.get('min_clip_length', 15)}s
Max clip length: {constraints.get('max_clip_length', 90)}s

Find top 5 viral clip candidates in this chunk. Return JSON only.
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config={'temperature': 0.3, 'response_mime_type': 'application/json'}
            )
            
            try:
                chunk_candidates = json.loads(response.text)
                all_candidates.extend(chunk_candidates.get("clips", []))
            except:
                continue
        
        return all_candidates
    
    def _global_selection(self, candidates: list, duration_sec: float, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Select and rank final clips from all candidates."""
        max_clips = constraints.get('max_clips', 10)
        
        prompt = f"""{self.rerank_prompt}

Candidates ({len(candidates)} total):
{json.dumps(candidates, indent=2)}

Video duration: {duration_sec} seconds
Select best {max_clips} clips.

Rules:
- Ensure diversity (different topics/themes)
- No temporal overlaps
- Prefer clips with strong hooks in first 2-3 seconds
- Sort by score (descending)

Return final EDL JSON.
"""
        
        response = self.model.generate_content(
            prompt,
            generation_config={'temperature': 0.2, 'response_mime_type': 'application/json'}
        )
        
        edl = json.loads(response.text)
        
        # Enforce constraints
        edl = self._enforce_constraints(edl, duration_sec, constraints)
        
        return edl
    
    def _enforce_constraints(self, edl: Dict[str, Any], duration_sec: float, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process EDL to enforce hard constraints."""
        clips = edl.get("clips", [])
        
        min_len = constraints.get('min_clip_length', 15)
        max_len = constraints.get('max_clip_length', 90)
        max_clips = constraints.get('max_clips', 10)
        
        # Filter clips
        valid_clips = []
        for clip in clips:
            # Check bounds
            if clip["start_sec"] < 0 or clip["end_sec"] > duration_sec:
                continue
            if clip["start_sec"] >= clip["end_sec"]:
                continue
            
            # Check length
            length = clip["end_sec"] - clip["start_sec"]
            if length < min_len or length > max_len:
                continue
            
            # Check score
            if not (0 <= clip.get("score", 0) <= 1):
                clip["score"] = max(0, min(1, clip.get("score", 0.5)))
            
            valid_clips.append(clip)
        
        # Remove overlaps (keep higher scored)
        valid_clips = self._remove_overlaps(valid_clips)
        
        # Limit to max_clips
        valid_clips = sorted(valid_clips, key=lambda c: c["score"], reverse=True)[:max_clips]
        
        return {"clips": valid_clips}
    
    def _remove_overlaps(self, clips: list) -> list:
        """Remove overlapping clips, keeping higher scored."""
        sorted_clips = sorted(clips, key=lambda c: (c["start_sec"], -c["score"]))
        non_overlapping = []
        
        for clip in sorted_clips:
            overlaps = False
            for existing in non_overlapping:
                if not (clip["end_sec"] <= existing["start_sec"] or clip["start_sec"] >= existing["end_sec"]):
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append(clip)
        
        return non_overlapping
    
    def repair_edl(self, repair_instructions: str, duration_sec: float) -> Dict[str, Any]:
        """Repair invalid EDL."""
        prompt = f"""{self.repair_prompt}

{repair_instructions}
"""
        
        response = self.model.generate_content(
            prompt,
            generation_config={'temperature': 0.0, 'response_mime_type': 'application/json'}
        )
        
        return json.loads(response.text)


def get_provider(strategy: str = "gumloop_llm") -> LLMProvider:
    """Factory function to get LLM provider based on strategy."""
    if strategy == "gemini_fallback":
        return GeminiProvider()
    elif strategy == "gumloop_llm":
        return GumloopProvider()
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
