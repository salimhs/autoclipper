"""
Visual tracking service using MediaPipe for face detection.
Generates crop paths for vertical video conversion.
"""

import cv2
import mediapipe as mp
import json
from typing import Dict, Any, List, Tuple
from pathlib import Path


class VisualTracker:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # Full-range model
            min_detection_confidence=0.3
        )
    
    def track_video(self, video_path: str, sample_rate: int = 30) -> Dict[str, Any]:
        """
        Track faces/objects throughout video.
        
        Args:
            video_path: Path to video file
            sample_rate: Process every Nth frame
            
        Returns:
            Dict matching schemas/tracking.json
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        tracking_data = {"frames": []}
        frame_num = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_num % sample_rate == 0:
                timestamp = frame_num / fps
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_detection.process(rgb_frame)
                
                detections = []
                if results.detections:
                    h, w, _ = frame.shape
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        detections.append({
                            "bbox": {
                                "x": int(bbox.xmin * w),
                                "y": int(bbox.ymin * h),
                                "w": int(bbox.width * w),
                                "h": int(bbox.height * h)
                            },
                            "confidence": detection.score[0],
                            "type": "face"
                        })
                
                tracking_data["frames"].append({
                    "frame_num": frame_num,
                    "timestamp": timestamp,
                    "detections": detections
                })
            
            frame_num += 1
        
        cap.release()
        return tracking_data
    
    def generate_crop_paths(
        self,
        tracking_data: Dict[str, Any],
        target_aspect: Tuple[int, int] = (9, 16),
        source_width: int = 1920,
        source_height: int = 1080
    ) -> List[Dict[str, Any]]:
        """
        Generate smooth crop paths from tracking data.
        
        Returns:
            List of crop keyframes [{t, x, y, w, h}]
        """
        crop_w = int(source_height * target_aspect[0] / target_aspect[1])
        crop_h = source_height
        
        crop_path = []
        
        for frame_data in tracking_data["frames"]:
            timestamp = frame_data["timestamp"]
            
            if frame_data["detections"]:
                # Use first face detection
                det = frame_data["detections"][0]
                bbox = det["bbox"]
                
                # Center crop on face
                face_center_x = bbox["x"] + bbox["w"] // 2
                crop_x = max(0, min(face_center_x - crop_w // 2, source_width - crop_w))
                crop_y = 0
            else:
                # Center crop fallback
                crop_x = (source_width - crop_w) // 2
                crop_y = 0
            
            crop_path.append({
                "t": timestamp,
                "x": crop_x,
                "y": crop_y,
                "w": crop_w,
                "h": crop_h
            })
        
        return self._smooth_crop_path(crop_path)
    
    def _smooth_crop_path(self, crop_path: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply One Euro filter to crop path for smooth, responsive tracking.
        Better than moving average: reduces jitter while maintaining responsiveness.
        """
        if len(crop_path) < 2:
            return crop_path
        
        # One Euro filter for x-coordinate
        filter_x = OneEuroFilter(min_cutoff=1.0, beta=0.007)
        
        smoothed = []
        for i, keyframe in enumerate(crop_path):
            t = keyframe["t"]
            
            # Apply  filter to x coordinate (y is usually fixed at 0 for horizontal videos)
            smoothed_x = filter_x(keyframe["x"], t)
            
            smoothed.append({
                "t": t,
                "x": int(smoothed_x),
                "y": keyframe["y"],
                "w": keyframe["w"],
                "h": keyframe["h"]
            })
        
        return smoothed


class OneEuroFilter:
    """
    One Euro Filter for smooth, low-latency filtering.
    Reference: http://cristal.univ-lille.fr/~casiez/1euro/
    
    Reduces jitter while maintaining responsiveness to rapid changes.
    """
    
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        """
        Args:
            min_cutoff: Minimum cutoff frequency (lower = more smoothing)
            beta: Speed coefficient (higher = more responsive to rapid changes)
            d_cutoff: Cutoff frequency for derivative
        """
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None
    
    def __call__(self, x: float, t: float) -> float:
        """Filter a new value."""
        if self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x
        
        # Calculate time delta
        dt = t - self.t_prev
        if dt <= 0:
            dt = 0.001  # Avoid division by zero
        
        # Estimate derivative
        dx = (x - self.x_prev) / dt
        
        # Smooth derivative
        edx = self._smoothing_factor(dt, self.d_cutoff)
        dx_hat = self._exponential_smoothing(edx, dx, self.dx_prev)
        
        # Calculate adaptive cutoff
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        
        # Smooth value
        alpha = self._smoothing_factor(dt, cutoff)
        x_hat = self._exponential_smoothing(alpha, x, self.x_prev)
        
        # Store state
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        
        return x_hat
    
    def _smoothing_factor(self, dt: float, cutoff: float) -> float:
        """Calculate smoothing factor (alpha) from cutoff frequency."""
        r = 2 * 3.14159 * cutoff * dt
        return r / (r + 1)
    
    def _exponential_smoothing(self, alpha: float, x: float, x_prev: float) -> float:
        """Apply exponential smoothing."""
        return alpha * x + (1 - alpha) * x_prev
