"""Drone evasion adapted to attention dodge mechanisms."""

import numpy as np
from typing import List, Tuple, Optional


class AvoidanceSystem:
    """Attention-based avoidance inspired by drone evasion algorithms."""
    
    def __init__(self, safety_radius: float = 2.0, attention_threshold: float = 0.7):
        """
        Initialize avoidance system.
        
        Args:
            safety_radius: Minimum distance to maintain from obstacles
            attention_threshold: Threshold for attention-based detection
        """
        self.safety_radius = safety_radius
        self.attention_threshold = attention_threshold
        self.obstacles = []
    
    def detect_obstacles(self, attention_map: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect obstacles from attention map.
        
        Args:
            attention_map: 2D attention heatmap
            
        Returns:
            List of (x, y) obstacle positions
        """
        # Find high-attention regions
        high_attention = attention_map > self.attention_threshold
        y_coords, x_coords = np.where(high_attention)
        
        obstacles = list(zip(x_coords.tolist(), y_coords.tolist()))
        self.obstacles = obstacles
        
        return obstacles
    
    def calculate_avoidance_vector(
        self, 
        current_pos: Tuple[float, float],
        target_pos: Tuple[float, float]
    ) -> Tuple[float, float]:
        """
        Calculate avoidance vector to dodge obstacles.
        
        Args:
            current_pos: Current (x, y) position
            target_pos: Target (x, y) position
            
        Returns:
            Avoidance vector (dx, dy)
        """
        if not self.obstacles:
            # Direct path if no obstacles
            dx = target_pos[0] - current_pos[0]
            dy = target_pos[1] - current_pos[1]
            return (dx, dy)
        
        # Calculate repulsion from obstacles
        repulsion_x, repulsion_y = 0.0, 0.0
        
        for obs_x, obs_y in self.obstacles:
            dist = np.sqrt(
                (current_pos[0] - obs_x)**2 + 
                (current_pos[1] - obs_y)**2
            )
            
            if dist < self.safety_radius and dist > 0:
                # Repulsion inversely proportional to distance
                force = (self.safety_radius - dist) / dist
                repulsion_x += force * (current_pos[0] - obs_x)
                repulsion_y += force * (current_pos[1] - obs_y)
        
        # Attraction to target
        attraction_x = target_pos[0] - current_pos[0]
        attraction_y = target_pos[1] - current_pos[1]
        
        # Combine forces
        total_x = attraction_x + repulsion_x
        total_y = attraction_y + repulsion_y
        
        return (total_x, total_y)
    
    def navigate(
        self,
        current_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        attention_map: Optional[np.ndarray] = None
    ) -> Tuple[float, float]:
        """
        Navigate from current to target position while avoiding obstacles.
        
        Args:
            current_pos: Current (x, y) position
            target_pos: Target (x, y) position
            attention_map: Optional attention map for obstacle detection
            
        Returns:
            Next position (x, y) to move to
        """
        if attention_map is not None:
            self.detect_obstacles(attention_map)
        
        avoidance = self.calculate_avoidance_vector(current_pos, target_pos)
        
        # Normalize and apply step
        magnitude = np.sqrt(avoidance[0]**2 + avoidance[1]**2)
        if magnitude > 0:
            step = 0.1  # Step size
            next_x = current_pos[0] + step * avoidance[0] / magnitude
            next_y = current_pos[1] + step * avoidance[1] / magnitude
        else:
            next_x, next_y = current_pos
        
        return (next_x, next_y)
