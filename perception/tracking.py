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
        """Apply smoothing to crop path to avoid jarring movements."""
        if len(crop_path) < 3:
            return crop_path
        
        # Simple moving average
        smoothed = [crop_path[0]]
        window = 3
        
        for i in range(1, len(crop_path) - 1):
            start = max(0, i - window // 2)
            end = min(len(crop_path), i + window // 2 + 1)
            
            avg_x = sum(cp["x"] for cp in crop_path[start:end]) // (end - start)
            
            smoothed.append({
                "t": crop_path[i]["t"],
                "x": avg_x,
                "y": crop_path[i]["y"],
                "w": crop_path[i]["w"],
                "h": crop_path[i]["h"]
            })
        
        smoothed.append(crop_path[-1])
        return smoothed
