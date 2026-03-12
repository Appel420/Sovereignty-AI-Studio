"""Hand tracking with MediaPipe and mouse smoothing."""

import numpy as np
from typing import Optional, List, Tuple
from collections import deque


class HandTracker:
    """MediaPipe hand tracker with smoothing for cursor control."""
    
    def __init__(self, smoothing_window: int = 5, confidence_threshold: float = 0.5):
        """
        Initialize hand tracker.
        
        Args:
            smoothing_window: Number of frames for smoothing
            confidence_threshold: Minimum confidence for detection
        """
        self.smoothing_window = smoothing_window
        self.confidence_threshold = confidence_threshold
        self.position_buffer = deque(maxlen=smoothing_window)
        self.detector = None
        self._init_detector()
    
    def _init_detector(self):
        """Initialize MediaPipe hand detector."""
        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.detector = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=self.confidence_threshold
            )
        except ImportError:
            print("MediaPipe not installed. Install with: pip install mediapipe")
    
    def track(self, frame: np.ndarray) -> Optional[List[Tuple[float, float]]]:
        """
        Track hand landmarks in frame.
        
        Args:
            frame: Input video frame (H, W, C)
            
        Returns:
            List of (x, y) coordinates for each hand landmark, or None
        """
        if self.detector is None:
            return None
        
        # TODO: Implement hand tracking
        results = self.detector.process(frame)
        
        if results.multi_hand_landmarks:
            landmarks = []
            for hand_landmarks in results.multi_hand_landmarks:
                for landmark in hand_landmarks.landmark:
                    landmarks.append((landmark.x, landmark.y))
            return landmarks
        
        return None
    
    def smooth_position(self, position: Tuple[float, float]) -> Tuple[float, float]:
        """
        Apply smoothing to position using moving average.
        
        Args:
            position: Raw (x, y) position
            
        Returns:
            Smoothed (x, y) position
        """
        self.position_buffer.append(position)
        
        if len(self.position_buffer) == 0:
            return position
        
        x_avg = sum(p[0] for p in self.position_buffer) / len(self.position_buffer)
        y_avg = sum(p[1] for p in self.position_buffer) / len(self.position_buffer)
        
        return (x_avg, y_avg)
    
    def get_cursor_position(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Get smoothed cursor position from hand tracking.
        
        Args:
            frame: Input video frame
            
        Returns:
            Pixel coordinates (x, y) or None
        """
        landmarks = self.track(frame)
        
        if landmarks and len(landmarks) > 8:  # Index finger tip
            finger_tip = landmarks[8]
            smoothed = self.smooth_position(finger_tip)
            
            h, w = frame.shape[:2]
            x = int(smoothed[0] * w)
            y = int(smoothed[1] * h)
            
            return (x, y)
        
        return None
