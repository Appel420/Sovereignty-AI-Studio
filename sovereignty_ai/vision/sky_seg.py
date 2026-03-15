"""SatViewAR NLOS mask - knows what blocks line of sight."""

import numpy as np
from typing import Tuple, Optional, List
import cv2


class SkySegmentation:
    """Satellite view-inspired AR segmentation for NLOS detection."""
    
    def __init__(
        self,
        sky_threshold: float = 0.5,
        elevation_scale: float = 1.0
    ):
        """
        Initialize sky segmentation system.
        
        Args:
            sky_threshold: Threshold for sky classification
            elevation_scale: Scaling factor for elevation data
        """
        self.sky_threshold = sky_threshold
        self.elevation_scale = elevation_scale
        self.elevation_map = None
        self.obstruction_mask = None
    
    def segment_sky(self, image: np.ndarray) -> np.ndarray:
        """
        Segment sky regions from image.
        
        Args:
            image: Input image (H, W, C)
            
        Returns:
            Binary mask (H, W) where 1 = sky, 0 = not sky
        """
        # Convert to HSV for better sky detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Sky typically has high saturation in blue channel
        # and specific hue range
        lower_sky = np.array([90, 50, 50])
        upper_sky = np.array([130, 255, 255])
        
        sky_mask = cv2.inRange(hsv, lower_sky, upper_sky)
        
        # Morphological operations to clean mask
        kernel = np.ones((5, 5), np.uint8)
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_CLOSE, kernel)
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_OPEN, kernel)
        
        return (sky_mask > 0).astype(np.uint8)
    
    def create_elevation_map(
        self, 
        image: np.ndarray,
        depth_map: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Create elevation map from image or depth data.
        
        Args:
            image: Input image
            depth_map: Optional depth map
            
        Returns:
            Elevation map (H, W)
        """
        if depth_map is not None:
            elevation = depth_map * self.elevation_scale
        else:
            # Estimate from image gradients
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gradient_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
            elevation = np.abs(gradient_y) * self.elevation_scale
        
        self.elevation_map = elevation
        return elevation
    
    def detect_nlos_regions(
        self,
        observer_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
        elevation_map: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Detect Non-Line-Of-Sight (NLOS) regions between observer and target.
        
        Args:
            observer_pos: (x, y) position of observer
            target_pos: (x, y) position of target
            elevation_map: Optional elevation map
            
        Returns:
            Binary mask showing NLOS regions
        """
        if elevation_map is None:
            if self.elevation_map is None:
                raise ValueError("No elevation map available")
            elevation_map = self.elevation_map
        
        h, w = elevation_map.shape
        nlos_mask = np.zeros((h, w), dtype=np.uint8)
        
        # Calculate line of sight
        x0, y0 = observer_pos
        x1, y1 = target_pos
        
        # Get all points along the line
        num_points = max(abs(x1 - x0), abs(y1 - y0)) + 1
        x_coords = np.linspace(x0, x1, num_points, dtype=int)
        y_coords = np.linspace(y0, y1, num_points, dtype=int)
        
        # Ensure coordinates are within bounds
        x_coords = np.clip(x_coords, 0, w - 1)
        y_coords = np.clip(y_coords, 0, h - 1)
        
        # Get elevations along the path
        if num_points > 0:
            path_elevations = elevation_map[y_coords, x_coords]
            
            # Calculate required line-of-sight elevation
            observer_elev = elevation_map[y0, x0]
            target_elev = elevation_map[y1, x1]
            required_elevs = np.linspace(observer_elev, target_elev, num_points)
            
            # Mark obstructed regions
            obstructed = path_elevations > required_elevs
            nlos_mask[y_coords[obstructed], x_coords[obstructed]] = 1
        
        self.obstruction_mask = nlos_mask
        return nlos_mask
    
    def visualize_los(
        self,
        image: np.ndarray,
        observer_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
        elevation_map: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Visualize line-of-sight analysis on image.
        
        Args:
            image: Input image
            observer_pos: Observer position
            target_pos: Target position
            elevation_map: Optional elevation map
            
        Returns:
            Annotated image
        """
        output = image.copy()
        
        # Detect NLOS regions
        nlos_mask = self.detect_nlos_regions(
            observer_pos, 
            target_pos, 
            elevation_map
        )
        
        # Overlay NLOS regions in red
        red_overlay = np.zeros_like(image)
        red_overlay[:, :, 2] = nlos_mask * 255
        output = cv2.addWeighted(output, 0.7, red_overlay, 0.3, 0)
        
        # Draw observer and target
        cv2.circle(output, observer_pos, 5, (0, 255, 0), -1)  # Green
        cv2.circle(output, target_pos, 5, (255, 0, 0), -1)    # Blue
        
        # Draw line of sight
        cv2.line(output, observer_pos, target_pos, (255, 255, 0), 2)
        
        return output
