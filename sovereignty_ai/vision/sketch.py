"""PhotoSketch contour extraction - draws seams and edges."""

import numpy as np
from typing import Optional, Tuple
import cv2


class SketchContours:
    """Extract and draw contours using PhotoSketch-inspired methods."""
    
    def __init__(
        self, 
        threshold1: int = 50, 
        threshold2: int = 150,
        blur_kernel: int = 5
    ):
        """
        Initialize sketch contour extractor.
        
        Args:
            threshold1: First threshold for Canny edge detection
            threshold2: Second threshold for Canny edge detection
            blur_kernel: Kernel size for Gaussian blur
        """
        self.threshold1 = threshold1
        self.threshold2 = threshold2
        self.blur_kernel = blur_kernel
    
    def extract_edges(self, image: np.ndarray) -> np.ndarray:
        """
        Extract edges using Canny edge detection.
        
        Args:
            image: Input image (H, W, C) or (H, W)
            
        Returns:
            Edge map (H, W)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)
        
        # Canny edge detection
        edges = cv2.Canny(blurred, self.threshold1, self.threshold2)
        
        return edges
    
    def find_contours(self, edge_map: np.ndarray) -> list:
        """
        Find contours from edge map.
        
        Args:
            edge_map: Binary edge map
            
        Returns:
            List of contours
        """
        contours, _ = cv2.findContours(
            edge_map, 
            cv2.RETR_TREE, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        return contours
    
    def draw_seams(
        self, 
        image: np.ndarray, 
        contours: list,
        color: Tuple[int, int, int] = (0, 0, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw contour seams on image.
        
        Args:
            image: Input image
            contours: List of contours to draw
            color: RGB color for seams
            thickness: Line thickness
            
        Returns:
            Image with drawn seams
        """
        output = image.copy()
        cv2.drawContours(output, contours, -1, color, thickness)
        return output
    
    def sketch(
        self, 
        image: np.ndarray,
        invert: bool = True
    ) -> np.ndarray:
        """
        Create sketch-style image from photo.
        
        Args:
            image: Input image
            invert: Invert colors for white background
            
        Returns:
            Sketch-style image
        """
        edges = self.extract_edges(image)
        
        if invert:
            sketch = 255 - edges
        else:
            sketch = edges
        
        # Convert to 3-channel if needed
        if len(image.shape) == 3:
            sketch = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        
        return sketch
    
    def stylize(
        self,
        image: np.ndarray,
        contour_weight: float = 0.7
    ) -> np.ndarray:
        """
        Create stylized image combining original and contours.
        
        Args:
            image: Input image
            contour_weight: Weight for contour overlay (0-1)
            
        Returns:
            Stylized image
        """
        edges = self.extract_edges(image)
        contours = self.find_contours(edges)
        
        # Create white canvas
        canvas = np.ones_like(image) * 255
        
        # Draw contours
        seamed = self.draw_seams(canvas, contours, (0, 0, 0), 1)
        
        # Blend with original
        output = cv2.addWeighted(
            image, 
            1 - contour_weight,
            seamed,
            contour_weight,
            0
        )
        
        return output
