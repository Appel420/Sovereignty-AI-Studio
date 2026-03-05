"""BFS navigation for maze/mine traversal - agent pathfinding under constraints."""

from typing import List, Tuple, Set, Optional, Dict
from collections import deque
from enum import Enum
import heapq


class CellType(Enum):
    """Types of cells in the navigation grid."""
    EMPTY = "."
    WALL = "#"
    START = "S"
    GOAL = "G"
    VISITED = "V"
    PATH = "*"
    DANGER = "X"


class BFSNavigator:
    """
    Breadth-First Search navigator for pathfinding in constrained environments.
    Inspired by mine maze navigation with safety constraints.
    """
    
    def __init__(
        self, 
        grid: List[List[str]],
        avoid_danger: bool = True,
        max_danger_proximity: int = 1
    ):
        """
        Initialize BFS navigator.
        
        Args:
            grid: 2D grid representing the environment
            avoid_danger: Whether to avoid dangerous cells
            max_danger_proximity: Maximum allowed proximity to danger cells
        """
        self.grid = [row[:] for row in grid]  # Deep copy
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0
        self.avoid_danger = avoid_danger
        self.max_danger_proximity = max_danger_proximity
        self.start_pos: Optional[Tuple[int, int]] = None
        self.goal_pos: Optional[Tuple[int, int]] = None
        self.visited: Set[Tuple[int, int]] = set()
        self.path: List[Tuple[int, int]] = []
        self._find_start_goal()
    
    def _find_start_goal(self):
        """Find start and goal positions in grid."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == 'S':
                    self.start_pos = (r, c)
                elif self.grid[r][c] == 'G':
                    self.goal_pos = (r, c)
    
    def is_valid(self, pos: Tuple[int, int]) -> bool:
        """
        Check if a position is valid for navigation.
        
        Args:
            pos: (row, col) position
            
        Returns:
            True if position is valid and navigable
        """
        r, c = pos
        
        # Bounds check
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return False
        
        # Wall check
        if self.grid[r][c] == '#':
            return False
        
        # Danger check
        if self.avoid_danger and self.grid[r][c] == 'X':
            return False
        
        # Danger proximity check
        if self.avoid_danger and self.max_danger_proximity > 0:
            for dr in range(-self.max_danger_proximity, self.max_danger_proximity + 1):
                for dc in range(-self.max_danger_proximity, self.max_danger_proximity + 1):
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < self.rows and 0 <= nc < self.cols and 
                        self.grid[nr][nc] == 'X'):
                        return False
        
        return True
    
    def get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Get valid neighboring positions.
        
        Args:
            pos: Current position
            
        Returns:
            List of valid neighbor positions
        """
        r, c = pos
        neighbors = []
        
        # 4-directional movement (up, down, left, right)
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            new_pos = (r + dr, c + dc)
            if self.is_valid(new_pos):
                neighbors.append(new_pos)
        
        return neighbors
    
    def bfs(self) -> Optional[List[Tuple[int, int]]]:
        """
        Perform BFS to find shortest path from start to goal.
        
        Returns:
            List of positions representing the path, or None if no path exists
        """
        if self.start_pos is None or self.goal_pos is None:
            return None
        
        queue = deque([(self.start_pos, [self.start_pos])])
        self.visited = {self.start_pos}
        
        while queue:
            current_pos, path = queue.popleft()
            
            # Check if goal reached
            if current_pos == self.goal_pos:
                self.path = path
                return path
            
            # Explore neighbors
            for neighbor in self.get_neighbors(current_pos):
                if neighbor not in self.visited:
                    self.visited.add(neighbor)
                    new_path = path + [neighbor]
                    queue.append((neighbor, new_path))
        
        # No path found
        return None
    
    def a_star(self) -> Optional[List[Tuple[int, int]]]:
        """
        Perform A* search for optimized pathfinding.
        
        Returns:
            List of positions representing the path, or None if no path exists
        """
        if self.start_pos is None or self.goal_pos is None:
            return None
        
        def heuristic(pos: Tuple[int, int]) -> float:
            """Manhattan distance heuristic."""
            return abs(pos[0] - self.goal_pos[0]) + abs(pos[1] - self.goal_pos[1])
        
        # Priority queue: (f_score, counter, position, path)
        counter = 0
        pq = [(heuristic(self.start_pos), counter, self.start_pos, [self.start_pos])]
        self.visited = {self.start_pos}
        g_scores: Dict[Tuple[int, int], float] = {self.start_pos: 0}
        
        while pq:
            f_score, _, current_pos, path = heapq.heappop(pq)
            
            # Check if goal reached
            if current_pos == self.goal_pos:
                self.path = path
                return path
            
            # Explore neighbors
            for neighbor in self.get_neighbors(current_pos):
                tentative_g = g_scores[current_pos] + 1
                
                if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                    g_scores[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor)
                    counter += 1
                    new_path = path + [neighbor]
                    heapq.heappush(pq, (f, counter, neighbor, new_path))
                    self.visited.add(neighbor)
        
        # No path found
        return None
    
    def visualize(self, show_visited: bool = False) -> str:
        """
        Create a string visualization of the grid with path.
        
        Args:
            show_visited: Whether to mark visited cells
            
        Returns:
            String representation of the grid
        """
        viz_grid = [row[:] for row in self.grid]
        
        # Mark path
        if self.path:
            for r, c in self.path:
                if viz_grid[r][c] not in ['S', 'G']:
                    viz_grid[r][c] = '*'
        
        # Mark visited if requested
        if show_visited:
            for r, c in self.visited:
                if viz_grid[r][c] == '.':
                    viz_grid[r][c] = 'v'
        
        # Create string
        lines = []
        lines.append("+" + "-" * self.cols + "+")
        for row in viz_grid:
            lines.append("|" + "".join(row) + "|")
        lines.append("+" + "-" * self.cols + "+")
        
        return "\n".join(lines)
    
    def get_path_cost(self) -> int:
        """
        Get the cost (length) of the found path.
        
        Returns:
            Path cost, or -1 if no path found
        """
        return len(self.path) - 1 if self.path else -1
    
    def navigate(self, algorithm: str = "bfs") -> Optional[List[Tuple[int, int]]]:
        """
        Navigate from start to goal using specified algorithm.
        
        Args:
            algorithm: "bfs" or "astar"
            
        Returns:
            Path as list of positions, or None if no path exists
        """
        if algorithm.lower() == "astar":
            return self.a_star()
        else:
            return self.bfs()
