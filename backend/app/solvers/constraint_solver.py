# app/services/enhanced_constraint_solver.py
# Production-grade constraint solver with advanced optimization

from typing import List, Dict, Any, Optional, Tuple, Set
import random
import math
import numpy as np
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass, field
from enum import Enum
import logging
from functools import lru_cache
from collections import defaultdict
from ..utils import geometry_utils as gu

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class Direction(str, Enum):
    """Vastu directions"""
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"
    CENTER = "center"

class RoomType(str, Enum):
    """Standard room types"""
    ENTRANCE = "entrance"
    MAIN_DOOR = "main_door"
    KITCHEN = "kitchen"
    MASTER_BEDROOM = "master_bedroom"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    TOILET = "toilet"
    POOJA_ROOM = "pooja_room"
    LIVING = "living"
    HALL = "hall"
    DINING = "dining"
    STUDY = "study"
    STORE = "store"
    BALCONY = "balcony"

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class Room(BaseModel):
    """Enhanced room model with validation"""
    id: str
    name: str
    type: str
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    direction: Optional[str] = None
    floor: int = 0
    area: Optional[float] = None
    
    @validator('type')
    def validate_room_type(cls, v):
        """Ensure room type is valid"""
        valid_types = [rt.value for rt in RoomType]
        if v not in valid_types:
            logger.warning(f"Unknown room type: {v}, treating as generic")
        return v
    
    def calculate_area(self) -> float:
        """Calculate room area"""
        if self.width and self.height:
            self.area = self.width * self.height
            return self.area
        return 0.0
    
    def get_center(self) -> Tuple[float, float]:
        """Get room center coordinates"""
        if self.x is not None and self.y is not None and self.width and self.height:
            return (self.x + self.width / 2, self.y + self.height / 2)
        return (0.0, 0.0)
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get room bounds (x_min, y_min, x_max, y_max)"""
        if all([self.x is not None, self.y is not None, self.width, self.height]):
            return (self.x, self.y, self.x + self.width, self.y + self.height)
        return (0.0, 0.0, 0.0, 0.0)

class SolverRequest(BaseModel):
    """Enhanced solver request with validation"""
    rooms: List[Dict[str, Any]]
    plot_width: float = Field(30.0, gt=0, le=100)
    plot_length: float = Field(30.0, gt=0, le=100)
    plot_shape: str = "rectangular"
    # Optional polygon for irregular/triangular/custom shapes
    plot_polygon: Optional[List[List[float]]] = None
    # Orientation metadata (e.g. {'hypotenuse_direction': 'west'})
    orientation: Optional[Dict[str, Any]] = None
    # IDs or types that are outdoor fixtures (garden, pool, parking)
    outdoor_fixtures: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    vastu_school: str = "modern"  # classical, modern, or flexible
    optimization_level: int = Field(2, ge=1, le=3)  # 1=fast, 2=balanced, 3=thorough
    seed: Optional[int] = None  # For reproducible results
    
    @validator('plot_shape')
    def validate_plot_shape(cls, v):
        # Normalize and allow broader set of shapes. Keep backwards compatibility.
        if isinstance(v, str):
            v_norm = v.lower().strip().replace('_', '-').replace(' ', '-')
        else:
            v_norm = v
        allowed = {"rectangular", "square", "l-shaped", "t-shaped", "triangular", "irregular", "circular"}
        if v_norm not in allowed:
            # Fallback to rectangular instead of raising to be more tolerant
            return "rectangular"
        return v_norm

class SolverResponse(BaseModel):
    """Enhanced solver response with detailed metrics"""
    rooms: List[Room]
    score: float = Field(..., ge=0, le=100)
    iterations: int
    solver_type: str = "constraint"
    metrics: Dict[str, float] = {}
    warnings: List[str] = []
    suggestions: List[str] = []
    convergence_history: List[float] = []  # Track score over time

# ============================================================================
# VASTU CONFIGURATION (Enhanced with weights and priorities)
# ============================================================================

@dataclass
class VastuPreference:
    """Enhanced Vastu preference with detailed configuration"""
    preferred: List[Direction]
    acceptable: List[Direction]
    avoid: List[Direction]
    weight: float  # Importance weight (0-1)
    priority: int = 0  # Higher priority rooms get placed first

VASTU_PREFERENCES = {
    RoomType.POOJA_ROOM: VastuPreference(
        preferred=[Direction.NORTHEAST],
        acceptable=[Direction.NORTH, Direction.EAST],
        avoid=[Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST],
        weight=1.0,
        priority=1  # Place first
    ),
    RoomType.ENTRANCE: VastuPreference(
        preferred=[Direction.NORTH, Direction.EAST, Direction.NORTHEAST],
        acceptable=[Direction.NORTHWEST],
        avoid=[Direction.SOUTH, Direction.SOUTHWEST],
        weight=1.0,
        priority=2
    ),
    RoomType.MASTER_BEDROOM: VastuPreference(
        preferred=[Direction.SOUTHWEST],
        acceptable=[Direction.SOUTH, Direction.WEST],
        avoid=[Direction.NORTHEAST, Direction.NORTH],
        weight=0.8,
        priority=3
    ),
    RoomType.KITCHEN: VastuPreference(
        preferred=[Direction.SOUTHEAST],
        acceptable=[Direction.NORTHWEST, Direction.EAST],
        avoid=[Direction.NORTH, Direction.NORTHEAST, Direction.SOUTHWEST],
        weight=0.9,
        priority=4
    ),
    RoomType.LIVING: VastuPreference(
        preferred=[Direction.NORTH, Direction.EAST, Direction.NORTHEAST],
        acceptable=[Direction.NORTHWEST, Direction.CENTER],
        avoid=[Direction.SOUTHWEST],
        weight=0.6,
        priority=5
    ),
    RoomType.BEDROOM: VastuPreference(
        preferred=[Direction.WEST, Direction.NORTHWEST, Direction.SOUTHWEST],
        acceptable=[Direction.SOUTH],
        avoid=[Direction.NORTHEAST],
        weight=0.6,
        priority=6
    ),
    RoomType.BATHROOM: VastuPreference(
        preferred=[Direction.NORTHWEST, Direction.WEST],
        acceptable=[Direction.SOUTH],
        avoid=[Direction.NORTHEAST, Direction.EAST, Direction.NORTH],
        weight=0.7,
        priority=7
    ),
    RoomType.DINING: VastuPreference(
        preferred=[Direction.EAST, Direction.WEST],
        acceptable=[Direction.NORTH, Direction.SOUTH],
        avoid=[],
        weight=0.5,
        priority=8
    ),
}

# Room size constraints (in meters) - Enhanced with aspect ratio
@dataclass
class RoomSizeConstraint:
    min_width: float
    max_width: float
    preferred_width: float
    min_height: float
    max_height: float
    preferred_height: float
    min_area: float
    max_area: float
    ideal_aspect_ratio: float = 1.0  # Width/Height ratio
    aspect_ratio_tolerance: float = 0.5

ROOM_SIZE_CONSTRAINTS = {
    RoomType.LIVING: RoomSizeConstraint(
        min_width=4.0, max_width=8.0, preferred_width=6.0,
        min_height=4.0, max_height=7.0, preferred_height=5.0,
        min_area=16.0, max_area=56.0,
        ideal_aspect_ratio=1.2, aspect_ratio_tolerance=0.4
    ),
    RoomType.KITCHEN: RoomSizeConstraint(
        min_width=2.5, max_width=5.0, preferred_width=3.5,
        min_height=2.5, max_height=4.5, preferred_height=3.5,
        min_area=6.25, max_area=22.5,
        ideal_aspect_ratio=1.0, aspect_ratio_tolerance=0.3
    ),
    RoomType.MASTER_BEDROOM: RoomSizeConstraint(
        min_width=3.5, max_width=6.0, preferred_width=4.5,
        min_height=3.5, max_height=5.5, preferred_height=4.5,
        min_area=12.25, max_area=33.0,
        ideal_aspect_ratio=1.0, aspect_ratio_tolerance=0.3
    ),
    RoomType.BEDROOM: RoomSizeConstraint(
        min_width=3.0, max_width=5.0, preferred_width=4.0,
        min_height=3.0, max_height=4.5, preferred_height=4.0,
        min_area=9.0, max_area=22.5,
        ideal_aspect_ratio=1.0, aspect_ratio_tolerance=0.3
    ),
    RoomType.BATHROOM: RoomSizeConstraint(
        min_width=1.8, max_width=3.0, preferred_width=2.2,
        min_height=1.8, max_height=3.0, preferred_height=2.0,
        min_area=3.24, max_area=9.0,
        ideal_aspect_ratio=1.1, aspect_ratio_tolerance=0.4
    ),
    RoomType.POOJA_ROOM: RoomSizeConstraint(
        min_width=1.2, max_width=2.5, preferred_width=1.8,
        min_height=1.2, max_height=2.5, preferred_height=1.8,
        min_area=1.44, max_area=6.25,
        ideal_aspect_ratio=1.0, aspect_ratio_tolerance=0.2
    ),
    RoomType.DINING: RoomSizeConstraint(
        min_width=2.5, max_width=5.0, preferred_width=3.5,
        min_height=2.5, max_height=5.0, preferred_height=3.5,
        min_area=6.25, max_area=25.0,
        ideal_aspect_ratio=1.0, aspect_ratio_tolerance=0.3
    ),
}

# Adjacency preferences (which rooms should be near each other)
ADJACENCY_PREFERENCES = [
    ("kitchen", "dining", 5.0, 3.0),  # (type1, type2, ideal_distance, weight)
    ("master_bedroom", "bathroom", 3.0, 2.5),
    ("living", "dining", 4.0, 2.0),
    ("entrance", "living", 5.0, 2.5),
    ("kitchen", "living", 6.0, 1.5),
    ("bedroom", "bathroom", 4.0, 1.5),
]

# ============================================================================
# OPTIMIZATION METRICS
# ============================================================================

@dataclass
class OptimizationMetrics:
    """Track optimization progress with detailed breakdown"""
    overlap_score: float = 0.0
    vastu_score: float = 0.0
    space_utilization: float = 0.0
    aspect_ratio_score: float = 0.0
    adjacency_score: float = 0.0
    boundary_score: float = 0.0  # Rooms within plot boundaries
    circulation_score: float = 0.0  # Space for movement
    total_score: float = 0.0
    
    # Detailed breakdown
    total_overlap_area: float = 0.0
    vastu_violations: int = 0
    out_of_bounds_count: int = 0
    poor_aspect_ratios: int = 0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for response"""
        return {
            "overlap_score": round(self.overlap_score, 2),
            "vastu_score": round(self.vastu_score, 2),
            "space_utilization": round(self.space_utilization, 2),
            "aspect_ratio_score": round(self.aspect_ratio_score, 2),
            "adjacency_score": round(self.adjacency_score, 2),
            "boundary_score": round(self.boundary_score, 2),
            "circulation_score": round(self.circulation_score, 2),
            "total_score": round(self.total_score, 2),
        }

# ============================================================================
# SPATIAL INDEX FOR FAST OVERLAP DETECTION
# ============================================================================

class SpatialIndex:
    """Simple spatial index for fast overlap queries"""
    
    def __init__(self, cell_size: float = 5.0):
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    
    def _get_cells(self, x: float, y: float, width: float, height: float) -> Set[Tuple[int, int]]:
        """Get all grid cells a room occupies"""
        cells = set()
        min_cell_x = int(x / self.cell_size)
        max_cell_x = int((x + width) / self.cell_size)
        min_cell_y = int(y / self.cell_size)
        max_cell_y = int((y + height) / self.cell_size)
        
        for cx in range(min_cell_x, max_cell_x + 1):
            for cy in range(min_cell_y, max_cell_y + 1):
                cells.add((cx, cy))
        return cells
    
    def insert(self, room_idx: int, room: Dict):
        """Insert a room into the spatial index"""
        cells = self._get_cells(room["x"], room["y"], room["width"], room["height"])
        for cell in cells:
            self.grid[cell].append(room_idx)
    
    def query_potential_overlaps(self, room: Dict) -> Set[int]:
        """Get rooms that potentially overlap with given room"""
        cells = self._get_cells(room["x"], room["y"], room["width"], room["height"])
        candidates = set()
        for cell in cells:
            candidates.update(self.grid.get(cell, []))
        return candidates
    
    def clear(self):
        """Clear the index"""
        self.grid.clear()

# ============================================================================
# ENHANCED CONSTRAINT SOLVER
# ============================================================================

class EnhancedConstraintSolver:
    """
    Production-grade constraint solver with:
    - Multi-objective optimization (Vastu + Space + Adjacency + Circulation)
    - Adaptive simulated annealing with restart
    - Spatial indexing for fast overlap detection
    - Priority-based placement
    - Detailed metrics and suggestions
    """
    
    def __init__(self, 
                 plot_width: float = 30.0, 
                 plot_length: float = 30.0,
                 plot_polygon: Optional[List[List[float]]] = None,
                 optimization_level: int = 2,
                 vastu_school: str = "modern",
                 seed: Optional[int] = None):
        
        self.plot_width = plot_width
        self.plot_length = plot_length
        # If provided, prefer polygon area to rectangular area
        self.plot_polygon = plot_polygon
        if self.plot_polygon:
            try:
                self.plot_area = gu.calculate_polygon_area(self.plot_polygon)
            except Exception:
                self.plot_area = plot_width * plot_length
        else:
            self.plot_area = plot_width * plot_length
        self.optimization_level = optimization_level
        self.vastu_school = vastu_school
        self.grid_size = 0.1  # Fine grid for precision
        
        # Set random seed for reproducibility
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        # Optimization parameters based on level
        self.max_iterations = {1: 50, 2: 200, 3: 500}[optimization_level]
        self.initial_temp = {1: 0.5, 2: 1.5, 3: 3.0}[optimization_level]
        self.cooling_rate = {1: 0.90, 2: 0.95, 3: 0.98}[optimization_level]
        self.restart_threshold = {1: 30, 2: 50, 3: 80}[optimization_level]
        
        # Vastu strictness based on school
        self.vastu_weight = {
            "classical": 1.0,
            "modern": 0.6,
            "flexible": 0.3
        }.get(vastu_school, 0.6)
        
        # Spatial index for fast overlap detection
        self.spatial_index = SpatialIndex(cell_size=5.0)
        
        # Track convergence
        self.convergence_history: List[float] = []
        
        logger.info(f"Solver initialized: {plot_width}x{plot_length}m, level={optimization_level}, vastu={vastu_school}")
    
    # ========================================================================
    # DIRECTION & REGION MANAGEMENT
    # ========================================================================
    
    @lru_cache(maxsize=32)
    def _get_direction_region(self, direction: Direction) -> Tuple[float, float, float, float]:
        """Get precise region boundaries for a Vastu direction (cached)"""
        band_w = self.plot_width / 3
        band_h = self.plot_length / 3
        
        regions = {
            Direction.NORTHEAST: (0, 0, band_w, band_h),
            Direction.NORTH: (band_w, 0, band_w, band_h),
            Direction.NORTHWEST: (2 * band_w, 0, band_w, band_h),
            Direction.EAST: (0, band_h, band_w, band_h),
            Direction.CENTER: (band_w, band_h, band_w, band_h),
            Direction.WEST: (2 * band_w, band_h, band_w, band_h),
            Direction.SOUTHEAST: (0, 2 * band_h, band_w, band_h),
            Direction.SOUTH: (band_w, 2 * band_h, band_w, band_h),
            Direction.SOUTHWEST: (2 * band_w, 2 * band_h, band_w, band_h),
        }
        
        return regions.get(direction, (band_w, band_h, band_w, band_h))
    
    def _get_room_direction(self, x: float, y: float, width: float, height: float) -> Direction:
        """Determine which Vastu direction a room is in (based on center)"""
        center_x = x + width / 2
        center_y = y + height / 2
        
        # Determine column and row
        col = min(2, int(center_x / (self.plot_width / 3)))
        row = min(2, int(center_y / (self.plot_length / 3)))
        
        direction_map = [
            [Direction.NORTHEAST, Direction.NORTH, Direction.NORTHWEST],
            [Direction.EAST, Direction.CENTER, Direction.WEST],
            [Direction.SOUTHEAST, Direction.SOUTH, Direction.SOUTHWEST]
        ]
        
        return direction_map[row][col]
    
    # ========================================================================
    # ROOM SIZING (Enhanced with aspect ratio control)
    # ========================================================================
    
    def _get_room_size(self, room_type: str) -> Tuple[float, float]:
        """Get optimal room size with controlled randomization and aspect ratio"""
        
        # Get constraints
        constraint = ROOM_SIZE_CONSTRAINTS.get(room_type)
        if not constraint:
            # Default constraints
            return 4.0, 4.0
        
        # Start with preferred size and add variation
        width = constraint.preferred_width + random.gauss(0, 0.25)
        height = constraint.preferred_height + random.gauss(0, 0.25)
        
        # Clamp to min/max
        width = np.clip(width, constraint.min_width, constraint.max_width)
        height = np.clip(height, constraint.min_height, constraint.max_height)
        
        # Enforce aspect ratio constraints
        current_ratio = width / height if height > 0 else 1.0
        target_ratio = constraint.ideal_aspect_ratio
        tolerance = constraint.aspect_ratio_tolerance
        
        if abs(current_ratio - target_ratio) > tolerance:
            # Adjust to meet aspect ratio
            if current_ratio > target_ratio + tolerance:
                # Too wide, reduce width or increase height
                width = height * (target_ratio + tolerance * 0.5)
            elif current_ratio < target_ratio - tolerance:
                # Too tall, increase width or reduce height
                width = height * (target_ratio - tolerance * 0.5)
            
            # Re-clamp after adjustment
            width = np.clip(width, constraint.min_width, constraint.max_width)
            height = np.clip(height, constraint.min_height, constraint.max_height)
        
        # Ensure area constraints
        area = width * height
        if area < constraint.min_area:
            scale = math.sqrt(constraint.min_area / area)
            width *= scale
            height *= scale
        elif area > constraint.max_area:
            scale = math.sqrt(constraint.max_area / area)
            width *= scale
            height *= scale
        
        return round(width, 2), round(height, 2)
    
    # ========================================================================
    # INITIAL PLACEMENT (Priority-based)
    # ========================================================================
    
    def _get_initial_position(self, 
                              room_type: str, 
                              width: float, 
                              height: float,
                              existing_rooms: List[Dict]) -> Tuple[float, float]:
        """Smart initial placement using Vastu + space availability"""
        
        # Get Vastu preferences
        vastu_pref = VASTU_PREFERENCES.get(room_type)
        if not vastu_pref:
            # Random placement for unknown types
            return (random.uniform(0, max(0.1, self.plot_width - width)),
                    random.uniform(0, max(0.1, self.plot_length - height)))
        
        preferred_dirs = vastu_pref.preferred
        acceptable_dirs = vastu_pref.acceptable
        
        # Try preferred directions first
        for direction in preferred_dirs + acceptable_dirs:
            x_region, y_region, w_region, h_region = self._get_direction_region(direction)
            
            # Try multiple random positions within this region
            for _ in range(15):
                x = x_region + random.uniform(0, max(0.1, w_region - width))
                y = y_region + random.uniform(0, max(0.1, h_region - height))
                
                # Clamp to plot boundaries
                x = np.clip(x, 0, self.plot_width - width)
                y = np.clip(y, 0, self.plot_length - height)
                
                # Check overlap using spatial index
                test_room = {"x": x, "y": y, "width": width, "height": height}
                candidates = self.spatial_index.query_potential_overlaps(test_room)
                
                total_overlap = sum(
                    self._calculate_overlap_area(test_room, existing_rooms[idx])
                    for idx in candidates
                    if idx < len(existing_rooms)
                )
                
                if total_overlap < 0.3:  # Minimal overlap tolerance
                    return x, y
        
        # Fallback: find position with minimal overlap anywhere
        best_x, best_y = 0, 0
        min_overlap = float('inf')
        
        for _ in range(30):
            x = random.uniform(0, self.plot_width - width)
            y = random.uniform(0, self.plot_length - height)
            
            test_room = {"x": x, "y": y, "width": width, "height": height}
            candidates = self.spatial_index.query_potential_overlaps(test_room)
            
            total_overlap = sum(
                self._calculate_overlap_area(test_room, existing_rooms[idx])
                for idx in candidates
                if idx < len(existing_rooms)
            )
            
            if total_overlap < min_overlap:
                min_overlap = total_overlap
                best_x, best_y = x, y
                if min_overlap < 0.5:  # Good enough
                    break
        
        return best_x, best_y
    
    # ========================================================================
    # OVERLAP DETECTION (Optimized)
    # ========================================================================
    
    @staticmethod
    def _check_overlap(room1: Dict, room2: Dict, margin: float = 0.0) -> bool:
        """Check if two rooms overlap (with optional margin)"""
        return (
            room1["x"] - margin < room2["x"] + room2["width"] + margin and
            room1["x"] + room1["width"] + margin > room2["x"] - margin and
            room1["y"] - margin < room2["y"] + room2["height"] + margin and
            room1["y"] + room1["height"] + margin > room2["y"] - margin
        )
    
    @staticmethod
    def _calculate_overlap_area(room1: Dict, room2: Dict) -> float:
        """Calculate exact overlap area between two rooms"""
        if not EnhancedConstraintSolver._check_overlap(room1, room2):
            return 0.0
        
        x_overlap = min(room1["x"] + room1["width"], room2["x"] + room2["width"]) - \
                    max(room1["x"], room2["x"])
        y_overlap = min(room1["y"] + room1["height"], room2["y"] + room2["height"]) - \
                    max(room1["y"], room2["y"])
        
        return max(0, x_overlap) * max(0, y_overlap)
    
    @staticmethod
    def _calculate_distance(room1: Dict, room2: Dict) -> float:
        """Calculate distance between room centers"""
        c1_x = room1["x"] + room1["width"] / 2
        c1_y = room1["y"] + room1["height"] / 2
        c2_x = room2["x"] + room2["width"] / 2
        c2_y = room2["y"] + room2["height"] / 2
        
        return math.sqrt((c1_x - c2_x)**2 + (c1_y - c2_y)**2)
    
    # ========================================================================
    # SCORING SYSTEM (Enhanced multi-objective)
    # ========================================================================
    
    def _calculate_metrics(self, positioned_rooms: List[Dict]) -> OptimizationMetrics:
        """Calculate comprehensive optimization metrics"""
        
        metrics = OptimizationMetrics()
        
        # 1. OVERLAP PENALTY (highest priority)
        total_overlap = 0.0
        overlap_count = 0
        
        for i in range(len(positioned_rooms)):
            for j in range(i + 1, len(positioned_rooms)):
                overlap = self._calculate_overlap_area(positioned_rooms[i], positioned_rooms[j])
                if overlap > 0:
                    total_overlap += overlap
                    overlap_count += 1
        
        metrics.total_overlap_area = total_overlap
        metrics.overlap_score = max(0, 100 - total_overlap * 25 - overlap_count * 5)
        
        # 2. VASTU COMPLIANCE
        vastu_violations = 0
        vastu_penalty = 0.0
        
        for room in positioned_rooms:
            room_type = room["type"]
            vastu_pref = VASTU_PREFERENCES.get(room_type)
            
            if not vastu_pref:
                continue
            
            # Get room's actual direction
            actual_dir = self._get_room_direction(
                room["x"], room["y"], room["width"], room["height"]
            )
            
            # Check compliance
            if actual_dir in vastu_pref.avoid:
                vastu_violations += 1
                vastu_penalty += vastu_pref.weight * 4.0  # Strong penalty
            elif actual_dir not in vastu_pref.preferred and actual_dir not in vastu_pref.acceptable:
                vastu_violations += 1
                vastu_penalty += vastu_pref.weight * 1.5  # Moderate penalty
        
        metrics.vastu_violations = vastu_violations
        metrics.vastu_score = max(0, 100 - vastu_penalty * self.vastu_weight * 8)
        
        # 3. SPACE UTILIZATION
        total_room_area = sum(r["width"] * r["height"] for r in positioned_rooms)
        utilization = (total_room_area / self.plot_area) * 100
        # Target 65-75% utilization
        if 65 <= utilization <= 75:
            metrics.space_utilization = 100
        else:
            metrics.space_utilization = max(0, 100 - abs(utilization - 70) * 2)
        
        # 4. ASPECT RATIO SCORE
        aspect_penalties = 0.0
        poor_ratios = 0
        
        for room in positioned_rooms:
            constraint = ROOM_SIZE_CONSTRAINTS.get(room["type"])
            if constraint:
                ratio = room["width"] / room["height"] if room["height"] > 0 else 1.0
                ideal = constraint.ideal_aspect_ratio
                tolerance = constraint.aspect_ratio_tolerance
                
                deviation = abs(ratio - ideal)
                if deviation > tolerance:
                    poor_ratios += 1
                    aspect_penalties += (deviation - tolerance) * 10
            else:
                # Generic aspect ratio check
                ratio = max(room["width"], room["height"]) / min(room["width"], room["height"])
                if ratio > 2.5:
                    poor_ratios += 1
                    aspect_penalties += (ratio - 2.5) * 3
        
        metrics.poor_aspect_ratios = poor_ratios
        metrics.aspect_ratio_score = max(0, 100 - aspect_penalties)
        
        # 5. ADJACENCY SCORE
        adjacency_score = 0.0
        
        for type1, type2, ideal_dist, weight in ADJACENCY_PREFERENCES:
            room1 = next((r for r in positioned_rooms if type1 in r["type"]), None)
            room2 = next((r for r in positioned_rooms if type2 in r["type"]), None)
            
            if room1 and room2:
                dist = self._calculate_distance(room1, room2)
                # Score based on how close to ideal distance
                if dist <= ideal_dist:
                    adjacency_score += weight * 10
                else:
                    # Penalty increases with distance
                    penalty = min(weight * 10, weight * 10 * (ideal_dist / dist))
                    adjacency_score += penalty
        
        metrics.adjacency_score = min(100, adjacency_score * 2)
        
        # 6. BOUNDARY SCORE (rooms within plot)
        out_of_bounds = 0
        boundary_penalty = 0.0
        
        for room in positioned_rooms:
            # If a polygon is provided, check center containment; otherwise use rectangular bounds
            if getattr(self, "plot_polygon", None):
                cx = room["x"] + room["width"] / 2.0
                cy = room["y"] + room["height"] / 2.0
                if not gu.point_in_polygon((float(cx), float(cy)), self.plot_polygon):
                    proj = gu.project_point_inside((float(cx), float(cy)), self.plot_polygon)
                    # penalty proportional to distance from valid region
                    d = math.hypot(cx - proj[0], cy - proj[1])
                    boundary_penalty += d * 10
                    out_of_bounds += 1
            else:
                if room["x"] < 0:
                    boundary_penalty += abs(room["x"]) * 10
                    out_of_bounds += 1
                if room["y"] < 0:
                    boundary_penalty += abs(room["y"]) * 10
                    out_of_bounds += 1
                if room["x"] + room["width"] > self.plot_width:
                    boundary_penalty += (room["x"] + room["width"] - self.plot_width) * 10
                    out_of_bounds += 1
                if room["y"] + room["height"] > self.plot_length:
                    boundary_penalty += (room["y"] + room["height"] - self.plot_length) * 10
                    out_of_bounds += 1
        
        metrics.out_of_bounds_count = out_of_bounds
        metrics.boundary_score = max(0, 100 - boundary_penalty)
        
        # 7. CIRCULATION SCORE (space for corridors/movement)
        # Check if there's reasonable spacing between rooms
        circulation_penalty = 0.0
        tight_spaces = 0
        
        for i in range(len(positioned_rooms)):
            for j in range(i + 1, len(positioned_rooms)):
                r1, r2 = positioned_rooms[i], positioned_rooms[j]
                
                # Calculate minimum gap
                x_gap = max(0, min(
                    abs(r1["x"] + r1["width"] - r2["x"]),
                    abs(r2["x"] + r2["width"] - r1["x"])
                ))
                y_gap = max(0, min(
                    abs(r1["y"] + r1["height"] - r2["y"]),
                    abs(r2["y"] + r2["height"] - r1["y"])
                ))
                
                min_gap = min(x_gap, y_gap)
                
                # Penalize if rooms are too close (less than 0.5m apart)
                if 0 < min_gap < 0.5:
                    tight_spaces += 1
                    circulation_penalty += (0.5 - min_gap) * 20
        
        metrics.circulation_score = max(0, 100 - circulation_penalty)
        
        # TOTAL SCORE (weighted combination)
        metrics.total_score = (
            metrics.overlap_score * 0.35 +       # 35% - most critical
            metrics.boundary_score * 0.20 +      # 20% - must fit in plot
            metrics.vastu_score * 0.20 +         # 20% - vastu compliance
            metrics.space_utilization * 0.10 +   # 10% - efficient use
            metrics.aspect_ratio_score * 0.07 +  # 7% - good proportions
            metrics.adjacency_score * 0.05 +     # 5% - functional layout
            metrics.circulation_score * 0.03     # 3% - movement space
        )
        
        return metrics
    
    # ========================================================================
    # OPTIMIZATION (Advanced Simulated Annealing with Restart)
    # ========================================================================
    
    def _optimize_layout(self, rooms: List[Dict[str, Any]]) -> Tuple[List[Dict], OptimizationMetrics]:
        """
        Optimize layout using adaptive simulated annealing with:
        - Temperature decay
        - Adaptive step sizes
        - Multiple move types
        - Automatic restart on stagnation
        """
        
        logger.info(f"Starting optimization: {len(rooms)} rooms, {self.max_iterations} iterations")
        
        # Sort rooms by priority (high priority rooms placed first)
        sorted_rooms = sorted(rooms, key=lambda r: VASTU_PREFERENCES.get(r["type"], VastuPreference([], [], [], 0.5, 999)).priority)
        
        # Initialize rooms with smart placement
        positioned_rooms = []
        for room in sorted_rooms:
            width, height = self._get_room_size(room["type"])
            x, y = self._get_initial_position(room["type"], width, height, positioned_rooms)
            
            positioned_rooms.append({
                "id": room["id"],
                "name": room["name"],
                "type": room["type"],
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "direction": room.get("direction")
            })
            
            # Update spatial index
            self.spatial_index.insert(len(positioned_rooms) - 1, positioned_rooms[-1])
        
        # Initial metrics
        best_metrics = self._calculate_metrics(positioned_rooms)
        best_layout = [r.copy() for r in positioned_rooms]
        current_metrics = best_metrics
        current_layout = [r.copy() for r in positioned_rooms]
        
        self.convergence_history = [best_metrics.total_score]
        
        logger.info(f"Initial score: {best_metrics.total_score:.2f} (overlap: {best_metrics.overlap_score:.1f}, vastu: {best_metrics.vastu_score:.1f})")
        
        # Simulated annealing
        temperature = self.initial_temp
        no_improvement_count = 0
        restart_count = 0
        
        for iteration in range(self.max_iterations):
            # Check for restart condition
            if no_improvement_count > self.restart_threshold and restart_count < 2:
                logger.info(f"Restarting optimization at iteration {iteration} (restart #{restart_count + 1})")
                # Restart with perturbation of best layout
                current_layout = [r.copy() for r in best_layout]
                for room in current_layout:
                    room["x"] += random.gauss(0, 1.0)
                    room["y"] += random.gauss(0, 1.0)
                    room["x"] = np.clip(room["x"], 0, self.plot_width - room["width"])
                    room["y"] = np.clip(room["y"], 0, self.plot_length - room["height"])
                
                current_metrics = self._calculate_metrics(current_layout)
                temperature = self.initial_temp * 0.5
                no_improvement_count = 0
                restart_count += 1
            
            # Adaptive move strategy
            if no_improvement_count > 30:
                # More aggressive exploration
                move_type = random.choices(
                    ["translate", "swap", "resize", "rotate"],
                    weights=[0.4, 0.3, 0.2, 0.1]
                )[0]
            elif best_metrics.overlap_score < 80:
                # Focus on resolving overlaps
                move_type = random.choices(
                    ["translate", "swap"],
                    weights=[0.7, 0.3]
                )[0]
            else:
                # Balanced exploration
                move_type = random.choices(
                    ["translate", "swap", "resize", "rotate"],
                    weights=[0.5, 0.25, 0.15, 0.1]
                )[0]
            
            # Make a copy for trial move
            trial_layout = [r.copy() for r in current_layout]
            
            # Apply move
            if move_type == "translate":
                success = self._try_translation(trial_layout, temperature)
            elif move_type == "swap":
                success = self._try_swap(trial_layout)
            elif move_type == "resize":
                success = self._try_resize(trial_layout)
            else:  # rotate
                success = self._try_rotate(trial_layout)
            
            if not success:
                continue
            
            # Rebuild spatial index for new layout
            self.spatial_index.clear()
            for idx, room in enumerate(trial_layout):
                self.spatial_index.insert(idx, room)
            
            # Evaluate new layout
            new_metrics = self._calculate_metrics(trial_layout)
            
            # Accept or reject based on Metropolis criterion
            delta = new_metrics.total_score - current_metrics.total_score
            
            if delta > 0 or (temperature > 0 and random.random() < math.exp(delta / temperature)):
                # Accept move
                current_layout = trial_layout
                current_metrics = new_metrics
                
                if new_metrics.total_score > best_metrics.total_score:
                    best_metrics = new_metrics
                    best_layout = [r.copy() for r in current_layout]
                    no_improvement_count = 0
                    
                    if iteration % 20 == 0:
                        logger.info(f"Iteration {iteration}: New best = {best_metrics.total_score:.2f}")
                else:
                    no_improvement_count += 1
            else:
                # Reject move - keep current layout
                no_improvement_count += 1
            
            # Track convergence
            if iteration % 5 == 0:
                self.convergence_history.append(best_metrics.total_score)
            
            # Cool down
            temperature *= self.cooling_rate
            
            # Early stopping if excellent solution found
            if (best_metrics.overlap_score > 98 and 
                best_metrics.boundary_score > 98 and 
                best_metrics.vastu_score > 85):
                logger.info(f"Excellent solution found at iteration {iteration}")
                break
        
        logger.info(f"Optimization complete: Final score = {best_metrics.total_score:.2f}")
        logger.info(f"  Overlap: {best_metrics.overlap_score:.1f}, Vastu: {best_metrics.vastu_score:.1f}, Boundary: {best_metrics.boundary_score:.1f}")
        
        return best_layout, best_metrics
    
    def _try_translation(self, rooms: List[Dict], temperature: float) -> bool:
        """Try translating a random room"""
        room_idx = random.randint(0, len(rooms) - 1)
        room = rooms[room_idx]
        
        # Adaptive step size based on temperature
        max_displacement = min(3.0, 1.5 * temperature)
        dx = random.gauss(0, max_displacement)
        dy = random.gauss(0, max_displacement)
        
        # Apply move
        room["x"] = room["x"] + dx
        room["y"] = room["y"] + dy

        # Enforce boundaries: polygon-aware if available, else rectangular clip
        if getattr(self, "plot_polygon", None):
            # Project center into polygon if needed
            cx = room["x"] + room["width"] / 2.0
            cy = room["y"] + room["height"] / 2.0
            if not gu.point_in_polygon((float(cx), float(cy)), self.plot_polygon):
                proj = gu.project_point_inside((float(cx), float(cy)), self.plot_polygon)
                room["x"] = proj[0] - room["width"] / 2.0
                room["y"] = proj[1] - room["height"] / 2.0
        else:
            room["x"] = np.clip(room["x"], 0, self.plot_width - room["width"])
            room["y"] = np.clip(room["y"], 0, self.plot_length - room["height"])
        
        return True
    
    def _try_swap(self, rooms: List[Dict]) -> bool:
        """Try swapping positions of two rooms"""
        if len(rooms) < 2:
            return False
        
        idx1, idx2 = random.sample(range(len(rooms)), 2)
        room1, room2 = rooms[idx1], rooms[idx2]
        
        # Save original positions
        orig_x1, orig_y1 = room1["x"], room1["y"]
        
        # Swap positions
        room1["x"], room2["x"] = room2["x"], orig_x1
        room1["y"], room2["y"] = room2["y"], orig_y1
        
        # Ensure both rooms fit (polygon-aware if available)
        for r in (room1, room2):
            if getattr(self, "plot_polygon", None):
                cx = r["x"] + r["width"] / 2.0
                cy = r["y"] + r["height"] / 2.0
                if not gu.point_in_polygon((float(cx), float(cy)), self.plot_polygon):
                    proj = gu.project_point_inside((float(cx), float(cy)), self.plot_polygon)
                    r["x"] = proj[0] - r["width"] / 2.0
                    r["y"] = proj[1] - r["height"] / 2.0
            else:
                r["x"] = np.clip(r["x"], 0, self.plot_width - r["width"])
                r["y"] = np.clip(r["y"], 0, self.plot_length - r["height"])
        
        return True
    
    def _try_resize(self, rooms: List[Dict]) -> bool:
        """Try resizing a room slightly"""
        room_idx = random.randint(0, len(rooms) - 1)
        room = rooms[room_idx]
        
        # Get constraints
        constraint = ROOM_SIZE_CONSTRAINTS.get(room["type"])
        if not constraint:
            return False
        
        # Small resize with aspect ratio preservation
        delta_w = random.gauss(0, 0.2)
        delta_h = random.gauss(0, 0.2)
        
        room["width"] = np.clip(
            room["width"] + delta_w,
            constraint.min_width,
            constraint.max_width
        )
        room["height"] = np.clip(
            room["height"] + delta_h,
            constraint.min_height,
            constraint.max_height
        )
        
        # Ensure still within plot (polygon-aware if available)
        if getattr(self, "plot_polygon", None):
            cx = room["x"] + room["width"] / 2.0
            cy = room["y"] + room["height"] / 2.0
            if not gu.point_in_polygon((float(cx), float(cy)), self.plot_polygon):
                proj = gu.project_point_inside((float(cx), float(cy)), self.plot_polygon)
                room["x"] = proj[0] - room["width"] / 2.0
                room["y"] = proj[1] - room["height"] / 2.0
        else:
            room["x"] = np.clip(room["x"], 0, self.plot_width - room["width"])
            room["y"] = np.clip(room["y"], 0, self.plot_length - room["height"])
        
        return True
    
    def _try_rotate(self, rooms: List[Dict]) -> bool:
        """Try rotating a room (swap width and height)"""
        room_idx = random.randint(0, len(rooms) - 1)
        room = rooms[room_idx]
        
        # Swap dimensions
        room["width"], room["height"] = room["height"], room["width"]
        
        # Ensure still within plot
        if getattr(self, "plot_polygon", None):
            cx = room["x"] + room["width"] / 2.0
            cy = room["y"] + room["height"] / 2.0
            if not gu.point_in_polygon((float(cx), float(cy)), self.plot_polygon):
                proj = gu.project_point_inside((float(cx), float(cy)), self.plot_polygon)
                room["x"] = proj[0] - room["width"] / 2.0
                room["y"] = proj[1] - room["height"] / 2.0
        else:
            if room["x"] + room["width"] > self.plot_width:
                room["x"] = self.plot_width - room["width"]
            if room["y"] + room["height"] > self.plot_length:
                room["y"] = self.plot_length - room["height"]
        
        return True
    
    # ========================================================================
    # SUGGESTIONS & WARNINGS
    # ========================================================================
    
    def _generate_suggestions(self, 
                              positioned_rooms: List[Dict], 
                              metrics: OptimizationMetrics) -> Tuple[List[str], List[str]]:
        """Generate actionable suggestions and warnings"""
        
        warnings = []
        suggestions = []
        
        # 1. Overlap issues
        if metrics.overlap_score < 90:
            if metrics.total_overlap_area > 10:
                warnings.append(f"Significant room overlap detected ({metrics.total_overlap_area:.1f} sq.m). Layout may not be feasible.")
                suggestions.append("Consider: (1) Increasing plot size, (2) Reducing number of rooms, or (3) Decreasing room sizes.")
            else:
                warnings.append("Minor room overlaps detected.")
                suggestions.append("Fine-tune room positions to eliminate overlaps.")
        
        # 2. Boundary issues
        if metrics.out_of_bounds_count > 0:
            warnings.append(f"{metrics.out_of_bounds_count} room(s) extending beyond plot boundaries.")
            suggestions.append("Increase plot dimensions or reduce room sizes to fit within boundaries.")
        
        # 3. Vastu compliance
        if metrics.vastu_score < 70:
            vastu_issues = []
            for room in positioned_rooms:
                vastu_pref = VASTU_PREFERENCES.get(room["type"])
                if not vastu_pref:
                    continue
                
                actual_dir = self._get_room_direction(
                    room["x"], room["y"], room["width"], room["height"]
                )
                
                if actual_dir in vastu_pref.avoid:
                    vastu_issues.append((room["name"], actual_dir, vastu_pref.preferred))
            
            if vastu_issues:
                warnings.append(f"{len(vastu_issues)} room(s) in non-compliant Vastu directions.")
                for room_name, actual, preferred in vastu_issues[:3]:  # Show top 3
                    suggestions.append(
                        f"Move '{room_name}' from {actual.value} to {', '.join(d.value for d in preferred)} direction."
                    )
        
        # 4. Space utilization
        utilization = (sum(r["width"] * r["height"] for r in positioned_rooms) / self.plot_area) * 100
        
        if utilization > 85:
            warnings.append(f"Very high space utilization ({utilization:.1f}%). Limited circulation space.")
            suggestions.append("Consider larger plot or smaller rooms for comfortable living space.")
        elif utilization < 50:
            suggestions.append(f"Low space utilization ({utilization:.1f}%). Consider adding more rooms or features (study, balcony, storage).")
        
        # 5. Aspect ratios
        if metrics.poor_aspect_ratios > 0:
            warnings.append(f"{metrics.poor_aspect_ratios} room(s) have suboptimal proportions.")
            suggestions.append("Adjust room dimensions for better usability (avoid overly elongated rooms).")
        
        # 6. Adjacency
        if metrics.adjacency_score < 50:
            suggestions.append("Consider repositioning rooms for better functional adjacency (e.g., kitchen near dining).")
        
        # 7. Circulation
        if metrics.circulation_score < 70:
            warnings.append("Limited space between rooms for circulation.")
            suggestions.append("Add corridors or increase spacing between rooms for better movement.")
        
        return warnings, suggestions
    
    # ========================================================================
    # MAIN SOLVE METHOD
    # ========================================================================
    
    def solve(self, request: SolverRequest) -> SolverResponse:
        """
        Main solve entry point.
        Returns optimized floor plan with detailed metrics and suggestions.
        """
        
        try:
            # Validate input
            if not request.rooms:
                raise ValueError("No rooms provided")
            
            if request.plot_width <= 0 or request.plot_length <= 0:
                raise ValueError("Invalid plot dimensions")
            
            # Run optimization
            positioned_rooms, metrics = self._optimize_layout(request.rooms)
            
            # Generate suggestions and warnings
            warnings, suggestions = self._generate_suggestions(positioned_rooms, metrics)
            
            # Create response with positioned rooms
            result_rooms = []
            for room_data in positioned_rooms:
                room = Room(
                    id=room_data["id"],
                    name=room_data["name"],
                    type=room_data["type"],
                    x=round(room_data["x"], 2),
                    y=round(room_data["y"], 2),
                    width=round(room_data["width"], 2),
                    height=round(room_data["height"], 2),
                    direction=self._get_room_direction(
                        room_data["x"], 
                        room_data["y"], 
                        room_data["width"], 
                        room_data["height"]
                    ).value,
                    floor=room_data.get("floor", 0)
                )
                room.calculate_area()
                result_rooms.append(room)
            
            return SolverResponse(
                rooms=result_rooms,
                score=round(metrics.total_score, 2),
                iterations=self.max_iterations,
                solver_type="enhanced_constraint",
                metrics=metrics.to_dict(),
                warnings=warnings,
                suggestions=suggestions,
                convergence_history=self.convergence_history
            )
        
        except Exception as e:
            logger.error(f"Solver error: {str(e)}", exc_info=True)
            raise


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def solve_floor_plan(request: SolverRequest) -> SolverResponse:
    """
    Entry point for the enhanced constraint solver.
    
    Args:
        request: SolverRequest with rooms and plot specifications
    
    Returns:
        SolverResponse with optimized layout, metrics, and suggestions
    """
    solver = EnhancedConstraintSolver(
        plot_width=request.plot_width,
        plot_length=request.plot_length,
        plot_polygon=getattr(request, "plot_polygon", None) or (request.constraints or {}).get("plot_polygon"),
        optimization_level=request.optimization_level,
        vastu_school=request.vastu_school,
        seed=request.seed
    )
    return solver.solve(request)