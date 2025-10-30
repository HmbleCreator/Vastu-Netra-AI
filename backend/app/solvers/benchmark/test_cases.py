"""
Standard test cases for benchmarking Vastu solvers.
Each case provides plot geometry, room requirements, and validation metrics.
"""
from typing import Dict, List, Tuple
from shapely.geometry import Polygon, box
import numpy as np

class BenchmarkCase:
    def __init__(self, 
                 name: str,
                 plot: Polygon,
                 rooms: List[Dict],
                 adjacency: Dict[int, List[int]],
                 vastu_directions: Dict[str, List[str]] = None):
        self.name = name
        self.plot = plot
        self.rooms = rooms
        self.adjacency = adjacency
        self.vastu_directions = vastu_directions or {}
        
    def get_solver_request(self) -> Dict:
        """Convert to solver input format."""
        return {
            'plot': self.plot,
            'rooms': self.rooms,
            'adjacency': self.adjacency,
            'vastu_directions': self.vastu_directions
        }

def create_rectangular_case() -> BenchmarkCase:
    """Simple rectangular plot with 4 rooms."""
    plot = box(0, 0, 10, 8)  # 10m x 8m plot
    
    rooms = [
        {'name': 'Living', 'area': 20, 'min_dim': 4},  # Living room
        {'name': 'Kitchen', 'area': 12, 'min_dim': 3},  # Kitchen
        {'name': 'Bedroom', 'area': 16, 'min_dim': 3},  # Bedroom
        {'name': 'Bath', 'area': 6, 'min_dim': 2},      # Bathroom
    ]
    
    # Living room connected to all, kitchen-bath connected
    adjacency = {
        0: [1, 2],  # Living - Kitchen, Bedroom
        1: [3],     # Kitchen - Bath
        2: [3],     # Bedroom - Bath
        3: []       # Bath - no additional
    }
    
    vastu = {
        'Living': ['E', 'NE'],
        'Kitchen': ['SE'],
        'Bedroom': ['SW', 'W'],
        'Bath': ['NW']
    }
    
    return BenchmarkCase('rectangular_4room', plot, rooms, adjacency, vastu)

def create_lshaped_case() -> BenchmarkCase:
    """L-shaped plot with 6 rooms."""
    # Create L-shaped plot
    coords = [(0,0), (12,0), (12,5), (5,5), (5,10), (0,10), (0,0)]
    plot = Polygon(coords)
    
    rooms = [
        {'name': 'Living', 'area': 24, 'min_dim': 4},
        {'name': 'Kitchen', 'area': 15, 'min_dim': 3},
        {'name': 'Dining', 'area': 12, 'min_dim': 3},
        {'name': 'Master', 'area': 18, 'min_dim': 3},
        {'name': 'Bedroom', 'area': 14, 'min_dim': 3},
        {'name': 'Bath', 'area': 8, 'min_dim': 2}
    ]
    
    adjacency = {
        0: [1, 2],      # Living - Kitchen, Dining
        1: [2],         # Kitchen - Dining
        2: [3],         # Dining - Master Bed
        3: [4, 5],      # Master - Bed2, Bath
        4: [5],         # Bed2 - Bath
        5: []           # Bath - no additional
    }
    
    vastu = {
        'Living': ['E', 'NE'],
        'Kitchen': ['SE'],
        'Dining': ['S'],
        'Master': ['SW'],
        'Bedroom': ['W'],
        'Bath': ['NW']
    }
    
    return BenchmarkCase('lshaped_6room', plot, rooms, adjacency, vastu)

def create_triangular_case() -> BenchmarkCase:
    """Triangular plot with 3 rooms for edge case testing."""
    # Create triangular plot
    coords = [(0,0), (10,0), (5,8), (0,0)]
    plot = Polygon(coords)
    
    rooms = [
        {'name': 'Living', 'area': 16, 'min_dim': 3},
        {'name': 'Kitchen', 'area': 12, 'min_dim': 3},
        {'name': 'Bedroom', 'area': 14, 'min_dim': 3}
    ]
    
    adjacency = {
        0: [1, 2],  # Living connected to both
        1: [],      # Kitchen - no additional
        2: []       # Bedroom - no additional
    }
    
    vastu = {
        'Living': ['E'],
        'Kitchen': ['SE'],
        'Bedroom': ['W']
    }
    
    return BenchmarkCase('triangular_3room', plot, rooms, adjacency, vastu)

# List of all available benchmark cases
BENCHMARK_CASES = [
    create_rectangular_case(),
    create_lshaped_case(),
    create_triangular_case()
]