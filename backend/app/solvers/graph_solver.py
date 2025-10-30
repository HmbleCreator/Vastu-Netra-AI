# app/services/graph_solver_service.py
# Production-grade graph-based layout solver using force-directed physics

from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
import numpy as np
from pydantic import BaseModel, Field, validator
from ..utils import geometry_utils as gu
from dataclasses import dataclass
from enum import Enum
import logging
import math

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
    """Room model"""
    id: str
    name: str
    type: str
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    direction: Optional[str] = None
    area: Optional[float] = None
    
    def calculate_area(self) -> float:
        if self.width and self.height:
            self.area = self.width * self.height
            return self.area
        return 0.0

class SolverRequest(BaseModel):
    """Solver request"""
    rooms: List[Dict[str, Any]]
    plot_width: float = Field(30.0, gt=0)
    plot_length: float = Field(30.0, gt=0)
    plot_shape: str = "rectangular"
    # Optional polygon for irregular/triangular/custom shapes: list of [x,y]
    plot_polygon: Optional[List[List[float]]] = None
    # Orientation details and metadata (e.g. {'hypotenuse_direction': 'west', 'right_angle_at': 'east'})
    orientation: Optional[Dict[str, Any]] = None
    # List of room ids/types considered outdoor (helps two-phase solver)
    outdoor_fixtures: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None

    @validator('plot_shape')
    def normalize_plot_shape(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.lower().strip().replace('_', '-')
        allowed = {"rectangular", "square", "l-shaped", "t-shaped", "triangular", "irregular", "circular"}
        return v if v in allowed else "rectangular"

class SolverResponse(BaseModel):
    """Solver response"""
    rooms: List[Room]
    score: float = Field(..., ge=0, le=100)
    iterations: int
    solver_type: str = "graph"
    generation_time: float = 0.0
    converged: bool = True
    warnings: List[str] = []

# ============================================================================
# VASTU & ROOM CONFIGURATION
# ============================================================================

# Vastu direction preferences (with weights for force calculation)
VASTU_PREFERENCES = {
    RoomType.POOJA_ROOM: {
        "preferred": [Direction.NORTHEAST],
        "acceptable": [Direction.NORTH, Direction.EAST],
        "avoid": [Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST],
        "weight": 1.0
    },
    RoomType.ENTRANCE: {
        "preferred": [Direction.NORTH, Direction.EAST, Direction.NORTHEAST],
        "acceptable": [Direction.NORTHWEST],
        "avoid": [Direction.SOUTH, Direction.SOUTHWEST],
        "weight": 0.9
    },
    RoomType.KITCHEN: {
        "preferred": [Direction.SOUTHEAST],
        "acceptable": [Direction.NORTHWEST, Direction.EAST],
        "avoid": [Direction.NORTH, Direction.NORTHEAST, Direction.SOUTHWEST],
        "weight": 0.9
    },
    RoomType.MASTER_BEDROOM: {
        "preferred": [Direction.SOUTHWEST],
        "acceptable": [Direction.SOUTH, Direction.WEST],
        "avoid": [Direction.NORTHEAST, Direction.NORTH],
        "weight": 0.8
    },
    RoomType.LIVING: {
        "preferred": [Direction.NORTH, Direction.EAST, Direction.NORTHEAST],
        "acceptable": [Direction.NORTHWEST, Direction.CENTER],
        "avoid": [Direction.SOUTHWEST],
        "weight": 0.6
    },
    RoomType.BEDROOM: {
        "preferred": [Direction.WEST, Direction.NORTHWEST, Direction.SOUTHWEST],
        "acceptable": [Direction.SOUTH],
        "avoid": [Direction.NORTHEAST],
        "weight": 0.6
    },
    RoomType.BATHROOM: {
        "preferred": [Direction.NORTHWEST, Direction.WEST],
        "acceptable": [Direction.SOUTH],
        "avoid": [Direction.NORTHEAST, Direction.EAST, Direction.NORTH],
        "weight": 0.7
    },
    RoomType.DINING: {
        "preferred": [Direction.EAST, Direction.WEST],
        "acceptable": [Direction.NORTH, Direction.SOUTH],
        "avoid": [],
        "weight": 0.5
    },
}

# Adjacency preferences (which rooms should be near each other)
ADJACENCY_GRAPH = {
    "kitchen": ["dining", "living"],
    "master_bedroom": ["bathroom"],
    "bedroom": ["bathroom"],
    "living": ["dining", "entrance", "hall"],
    "dining": ["kitchen", "living"],
    "entrance": ["living", "hall"],
    "hall": ["living", "entrance"],
    "pooja_room": ["living", "entrance"],
}

# Outdoor fixtures that should be excluded from indoor adjacency/physics
OUTDOOR_TYPES = {
    "garden", "lawn", "car_parking", "carport", "parking", "swimming_pool",
    "driveway", "deck", "patio", "terrace", "trees", "bore_well", "water_tank"
}

# Simple Vastu anchors for outdoor fixtures
OUTDOOR_VASTU_PREFERENCES = {
    "garden": {"preferred": [Direction.NORTHEAST, Direction.NORTH, Direction.EAST]},
    "lawn": {"preferred": [Direction.NORTHEAST, Direction.NORTH, Direction.EAST]},
    "swimming_pool": {"preferred": [Direction.NORTHEAST, Direction.NORTH]},
    "parking": {"preferred": [Direction.SOUTHEAST, Direction.NORTHWEST]},
    "car_parking": {"preferred": [Direction.SOUTHEAST, Direction.NORTHWEST]},
    "carport": {"preferred": [Direction.SOUTHEAST, Direction.NORTHWEST]},
    "deck": {"preferred": [Direction.EAST, Direction.NORTH]},
    "patio": {"preferred": [Direction.EAST, Direction.NORTH]},
    "terrace": {"preferred": [Direction.EAST, Direction.NORTH]},
    "trees": {"preferred": [Direction.NORTHEAST, Direction.NORTH]},
    "bore_well": {"preferred": [Direction.NORTHEAST]},
    "water_tank": {"preferred": [Direction.SOUTHWEST]}
}

def _is_outdoor(room_type: str) -> bool:
    try:
        rt = str(room_type).lower()
    except Exception:
        rt = str(room_type)
    return rt in OUTDOOR_TYPES

# Room size specifications (in meters)
ROOM_SIZES = {
    RoomType.LIVING: {"width": 6.0, "height": 5.0, "min_area": 20.0, "max_area": 50.0},
    RoomType.HALL: {"width": 6.0, "height": 5.0, "min_area": 20.0, "max_area": 50.0},
    RoomType.KITCHEN: {"width": 3.5, "height": 3.5, "min_area": 8.0, "max_area": 20.0},
    RoomType.MASTER_BEDROOM: {"width": 4.5, "height": 4.5, "min_area": 15.0, "max_area": 30.0},
    RoomType.BEDROOM: {"width": 4.0, "height": 4.0, "min_area": 12.0, "max_area": 22.0},
    RoomType.BATHROOM: {"width": 2.2, "height": 2.0, "min_area": 3.5, "max_area": 8.0},
    RoomType.TOILET: {"width": 1.8, "height": 1.8, "min_area": 2.5, "max_area": 5.0},
    RoomType.POOJA_ROOM: {"width": 1.8, "height": 1.8, "min_area": 2.0, "max_area": 5.0},
    RoomType.DINING: {"width": 3.5, "height": 3.5, "min_area": 9.0, "max_area": 20.0},
    RoomType.ENTRANCE: {"width": 3.0, "height": 2.0, "min_area": 4.0, "max_area": 10.0},
    RoomType.STUDY: {"width": 3.0, "height": 3.0, "min_area": 6.0, "max_area": 12.0},
    RoomType.BALCONY: {"width": 2.5, "height": 4.0, "min_area": 6.0, "max_area": 15.0},
}

# ============================================================================
# PHYSICS PARAMETERS
# ============================================================================

@dataclass
class PhysicsParams:
    """Physics simulation parameters"""
    max_iterations: int = 100
    time_step: float = 0.1
    damping: float = 0.8
    attraction_strength: float = 0.5
    repulsion_strength: float = 1.0
    vastu_force_strength: float = 2.0
    boundary_force_strength: float = 3.0
    convergence_threshold: float = 0.01
    ideal_spacing: float = 1.0  # meters gap between adjacent rooms

# ============================================================================
# GRAPH-BASED SOLVER
# ============================================================================

class GraphBasedLayoutSolver:
    """
    Force-directed layout solver using physics simulation.
    
    Algorithm: Fruchterman-Reingold inspired with Vastu forces
    - Adjacent rooms attract (should be near each other)
    - Non-adjacent rooms repel (should be apart)
    - Vastu forces pull rooms to preferred directions
    - Boundary forces keep rooms within plot
    
    Target: <2 seconds for 5-6 room layouts
    """

    def __init__(self, 
                 plot_width: float = 30.0, 
                 plot_length: float = 30.0,
                 plot_shape: Optional[str] = "rectangular",
                 seed: Optional[int] = None):
        self.plot_width = plot_width
        self.plot_length = plot_length
        self.plot_shape = (plot_shape or "rectangular").lower()
        self.graph = nx.Graph()
        self.params = PhysicsParams()
        self.plot_polygon = None
        self.plot_circle: Optional[Dict[str, Any]] = None  # {center: [x,y], radius: r}
        self.constraints: Dict[str, Any] = {}
        # Nodes that should remain fixed (used by two-phase solver)
        self.fixed_nodes: set = set()
        
        # Random seed for reproducibility
        if seed is not None:
            np.random.seed(seed)
        
        # Physics state
        self.positions: Dict[str, np.ndarray] = {}  # Room center positions
        self.velocities: Dict[str, np.ndarray] = {}  # Room velocities
        self.dimensions: Dict[str, Tuple[float, float]] = {}  # Room (width, height)
        
        logger.info(f"Graph solver initialized: {plot_width}x{plot_length}m")

    # ========================================================================
    # GRAPH CONSTRUCTION
    # ========================================================================

    def _normalize_room_type(self, room_type: Any) -> Optional[RoomType]:
        """Normalize diverse room type inputs to RoomType enum when possible.
        Falls back to None when no mapping is found.
        """
        try:
            # If already an enum or matching value string
            return RoomType(room_type)  # type: ignore[arg-type]
        except Exception:
            pass

        if not room_type:
            return None

        key = str(room_type).strip().lower()
        mapping = {
            "living_room": RoomType.LIVING,
            "living": RoomType.LIVING,
            "hall": RoomType.HALL,
            "kitchen": RoomType.KITCHEN,
            "master_bedroom": RoomType.MASTER_BEDROOM,
            "bedroom": RoomType.BEDROOM,
            "bathroom": RoomType.BATHROOM,
            "toilet": RoomType.TOILET,
            "pooja": RoomType.POOJA_ROOM,
            "pooja_room": RoomType.POOJA_ROOM,
            "dining": RoomType.DINING,
            "entrance": RoomType.ENTRANCE,
            "main_door": RoomType.ENTRANCE,
            "study": RoomType.STUDY,
            "balcony": RoomType.BALCONY,
        }
        return mapping.get(key)
    
    def _build_adjacency_graph(self, rooms: List[Dict[str, Any]]) -> nx.Graph:
        """Build graph with rooms as nodes and adjacency as edges"""
        G = nx.Graph()
        
        # Add nodes
        for room in rooms:
            G.add_node(
                room["id"],
                room_type=room["type"],
                name=room["name"],
                is_outdoor=_is_outdoor(room.get("type", ""))
            )
        
        # Add edges based on adjacency preferences
        for room in rooms:
            room_type = room["type"]
            room_id = room["id"]
            
            # Only add adjacency edges for indoor-to-indoor relationships
            if (room_type in ADJACENCY_GRAPH) and (not _is_outdoor(room_type)):
                for adjacent_type in ADJACENCY_GRAPH[room_type]:
                    # Find all rooms of the adjacent type
                    for other_room in rooms:
                        if (
                            other_room["type"] == adjacent_type
                            and other_room["id"] != room_id
                            and not _is_outdoor(other_room.get("type", ""))
                        ):
                            # Add edge with weight based on importance
                            weight = 1.0
                            # Higher weight for critical adjacencies
                            if (room_type == "kitchen" and adjacent_type == "dining") or \
                               (room_type == "master_bedroom" and adjacent_type == "bathroom"):
                                weight = 2.0
                            
                            G.add_edge(room_id, other_room["id"], weight=weight)
        
        logger.info(f"Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    
    # ========================================================================
    # INITIALIZATION
    # ========================================================================
    
    def _get_room_dimensions(self, room_type: str) -> Tuple[float, float]:
        """Get room dimensions based on type"""
        rt = self._normalize_room_type(room_type)
        specs = ROOM_SIZES.get(rt, {"width": 4.0, "height": 4.0})
        
        # Add small random variation
        width = specs["width"] * np.random.uniform(0.95, 1.05)
        height = specs["height"] * np.random.uniform(0.95, 1.05)
        
        return round(width, 2), round(height, 2)
    
    def _get_vastu_target_position(self, room_type: str) -> np.ndarray:
        """Get ideal position for room based on Vastu"""
        rt = self._normalize_room_type(room_type)
        # Indoor preferences via enum
        vastu_pref = VASTU_PREFERENCES.get(rt) if rt else None
        # Outdoor preferences via string mapping
        outdoor_pref = OUTDOOR_VASTU_PREFERENCES.get(str(room_type).lower())
        
        if not vastu_pref and not outdoor_pref:
            # Default to center
            return np.array([self.plot_width / 2, self.plot_length / 2])

        # If triangular plot, delegate to triangle-aware mapping
        if self.plot_shape == "triangular":
            return self._get_vastu_target_position_triangular(room_type)
        
        # Map direction to position
        direction_map = {
            Direction.NORTHEAST: np.array([self.plot_width * 0.25, self.plot_length * 0.25]),
            Direction.NORTH: np.array([self.plot_width * 0.5, self.plot_length * 0.25]),
            Direction.NORTHWEST: np.array([self.plot_width * 0.75, self.plot_length * 0.25]),
            Direction.EAST: np.array([self.plot_width * 0.25, self.plot_length * 0.5]),
            Direction.CENTER: np.array([self.plot_width * 0.5, self.plot_length * 0.5]),
            Direction.WEST: np.array([self.plot_width * 0.75, self.plot_length * 0.5]),
            Direction.SOUTHEAST: np.array([self.plot_width * 0.25, self.plot_length * 0.75]),
            Direction.SOUTH: np.array([self.plot_width * 0.5, self.plot_length * 0.75]),
            Direction.SOUTHWEST: np.array([self.plot_width * 0.75, self.plot_length * 0.75]),
        }
        
        # Use preferred direction, allowing entrance override via constraints
        preferred = list(vastu_pref["preferred"]) if vastu_pref else []
        if outdoor_pref and not preferred:
            preferred = list(outdoor_pref.get("preferred", []))
        try:
            if rt == RoomType.ENTRANCE and isinstance(self.constraints, dict):
                facing = str(self.constraints.get("house_facing", "")).strip().lower()
                if facing:
                    # Normalize to Direction if valid
                    if facing in {d.value for d in Direction}:
                        dir_enum = Direction(facing)
                        # Prepend facing direction with de-duplication
                        preferred = [dir_enum] + [d for d in preferred if d != dir_enum]
        except Exception:
            # Non-fatal: if constraints are missing or malformed, ignore
            pass

        # Use first preferred direction
        if preferred:
            return direction_map.get(preferred[0], np.array([self.plot_width / 2, self.plot_length / 2]))
        
        return np.array([self.plot_width / 2, self.plot_length / 2])


    def _get_vastu_target_position_triangular(self, room_type: str) -> np.ndarray:
        """Triangle-aware Vastu target mapping.

        Uses centroid and inradius to calculate a safe placement point inside the triangle
        that approximates the requested Vastu direction.
        """
        # Ensure we have a polygon
        if not self.plot_polygon or len(self.plot_polygon) < 3:
            return np.array([self.plot_width / 2, self.plot_length / 2])

        # centroid and inradius
        centroid = np.array(gu.calculate_polygon_centroid(self.plot_polygon))
        inradius = gu.calculate_polygon_inradius(self.plot_polygon)
        safe_radius = max(0.1, inradius * 0.7)

        rt = self._normalize_room_type(room_type)
        vastu_pref = VASTU_PREFERENCES.get(rt) if rt else None
        outdoor_pref = OUTDOOR_VASTU_PREFERENCES.get(str(room_type).lower())

        # default to centroid
        if not vastu_pref and not outdoor_pref:
            return centroid

        preferred = list(vastu_pref["preferred"]) if vastu_pref else []
        if outdoor_pref and not preferred:
            preferred = list(outdoor_pref.get("preferred", []))

        # map Direction enum to angles with 0 = East, 90 = North
        angle_map = {
            Direction.EAST: 0,
            Direction.NORTHEAST: 45,
            Direction.NORTH: 90,
            Direction.NORTHWEST: 135,
            Direction.WEST: 180,
            Direction.SOUTHWEST: 225,
            Direction.SOUTH: 270,
            Direction.SOUTHEAST: 315,
            Direction.CENTER: None
        }

        if not preferred:
            return centroid

        dir_enum = preferred[0]
        angle = angle_map.get(dir_enum)
        if angle is None:
            return centroid

        rad = np.radians(angle)
        offset = np.array([safe_radius * np.cos(rad), safe_radius * np.sin(rad)])
        target = centroid + offset

        # Final safety: if outside, project back to polygon
        if not gu.point_in_polygon((float(target[0]), float(target[1])), self.plot_polygon):
            proj = gu.project_point_inside((float(target[0]), float(target[1])), self.plot_polygon)
            return np.array(proj)

        return target
    
    def _initialize_positions(self, rooms: List[Dict[str, Any]]):
        """Initialize room positions, velocities, and dimensions"""
        for room in rooms:
            room_id = room["id"]
            room_type = room["type"]
            
            # Get dimensions
            width, height = self._get_room_dimensions(room_type)
            self.dimensions[room_id] = (width, height)
            
            # Get Vastu target with random offset
            vastu_target = self._get_vastu_target_position(room_type)
            offset = np.random.uniform(-2, 2, 2)  # Small random offset
            
            # Initialize position (ensure within bounds)
            pos = vastu_target + offset
            if self.plot_shape == "irregular" and self.plot_polygon:
                pos = self._project_inside_polygon(pos, width, height)
            elif self.plot_shape == "triangular":
                pos[0] = max(pos[0], width/2)
                pos[1] = max(pos[1], height/2)
                corner = pos + np.array([width/2, height/2])
                val = corner[0] / self.plot_width + corner[1] / self.plot_length - 1.0
                if val > 0:
                    grad = np.array([1.0 / self.plot_width, 1.0 / self.plot_length])
                    alpha = val / np.dot(grad, grad)
                    corner = corner - alpha * grad
                    pos = corner - np.array([width/2, height/2])
            else:
                pos[0] = np.clip(pos[0], width/2, self.plot_width - width/2)
                pos[1] = np.clip(pos[1], height/2, self.plot_length - height/2)
            
            self.positions[room_id] = pos
            self.velocities[room_id] = np.zeros(2)
    
    # ========================================================================
    # POLYGON HELPERS
    # ========================================================================
    
    def _point_in_polygon(self, point: np.ndarray) -> bool:
        """Check if point is inside polygon using ray casting"""
        if not self.plot_polygon:
            return True
        # delegate to shared geometry util (accepts tuple)
        return gu.point_in_polygon((float(point[0]), float(point[1])), self.plot_polygon)
    
    def _project_point_to_edge(self, point: np.ndarray, edge_start: np.ndarray, edge_end: np.ndarray) -> Tuple[np.ndarray, float]:
        """Project point onto edge, return projected point and distance"""
        edge_vec = edge_end - edge_start
        edge_len_sq = np.dot(edge_vec, edge_vec)
        
        if edge_len_sq < 1e-6:
            return edge_start, np.linalg.norm(point - edge_start)
        
        t = max(0, min(1, np.dot(point - edge_start, edge_vec) / edge_len_sq))
        projection = edge_start + t * edge_vec
        distance = np.linalg.norm(point - projection)
        
        return projection, distance
    
    def _project_inside_polygon(self, pos: np.ndarray, width: float, height: float) -> np.ndarray:
        """Project room center to be inside polygon"""
        if not self.plot_polygon:
            return pos

        # If any corner is outside, project that corner inside and adjust center accordingly.
        corners = [
            pos + np.array([-width/2, -height/2]),
            pos + np.array([width/2, -height/2]),
            pos + np.array([width/2, height/2]),
            pos + np.array([-width/2, height/2])
        ]

        for corner in corners:
            if not gu.point_in_polygon((float(corner[0]), float(corner[1])), self.plot_polygon):
                proj = gu.project_point_inside((float(corner[0]), float(corner[1])), self.plot_polygon)
                proj = np.array(proj)
                corner_offset = corner - pos
                pos = proj - corner_offset
                break

        return pos

    def _project_inside_circle(self, pos: np.ndarray, width: float, height: float) -> np.ndarray:
        """Ensure room center keeps all corners inside circle boundary"""
        if not self.plot_circle:
            return pos
        center = np.array(self.plot_circle.get("center", [self.plot_width/2, self.plot_length/2]))
        radius = float(self.plot_circle.get("radius", min(self.plot_width, self.plot_length)/2))
        # Use half-diagonal to ensure rectangle fits in circle
        half_diag = math.sqrt((width/2)**2 + (height/2)**2)
        max_center_dist = max(0.0, radius - half_diag)
        delta = pos - center
        dist = np.linalg.norm(delta)
        if dist > max_center_dist and dist > 1e-6:
            pos = center + (delta / dist) * max_center_dist
        return pos
    
    # ========================================================================
    # FORCE CALCULATION
    # ========================================================================
    
    def _calculate_attractive_force(self, room1_id: str, room2_id: str, weight: float) -> np.ndarray:
        """Calculate attractive force between adjacent rooms"""
        pos1 = self.positions[room1_id]
        pos2 = self.positions[room2_id]
        
        # Vector from room1 to room2
        delta = pos2 - pos1
        distance = np.linalg.norm(delta)
        
        if distance < 0.1:
            return np.zeros(2)
        
        direction = delta / distance
        
        # Ideal distance: rooms barely touching with small gap
        w1, h1 = self.dimensions[room1_id]
        w2, h2 = self.dimensions[room2_id]
        ideal_distance = (max(w1, w2) + max(h1, h2)) / 2 + self.params.ideal_spacing
        
        # Spring force: F = k * (distance - ideal_distance)
        force_magnitude = self.params.attraction_strength * weight * (distance - ideal_distance)
        
        return force_magnitude * direction
    
    def _calculate_repulsive_force(self, room1_id: str, room2_id: str) -> np.ndarray:
        """Calculate repulsive force between non-adjacent rooms"""
        pos1 = self.positions[room1_id]
        pos2 = self.positions[room2_id]
        
        delta = pos1 - pos2  # Repel away from each other
        distance = np.linalg.norm(delta)
        
        if distance < 0.1:
            # Too close, apply strong random push
            return np.random.uniform(-5, 5, 2)
        
        direction = delta / distance
        
        # Coulomb-like repulsion: F = k / distance
        force_magnitude = self.params.repulsion_strength * (5.0 / distance)
        
        return force_magnitude * direction
    
    def _calculate_vastu_force(self, room_id: str, room_type: str) -> np.ndarray:
        """Calculate force pulling room toward Vastu-preferred direction"""
        rt = self._normalize_room_type(room_type)
        vastu_pref = VASTU_PREFERENCES.get(rt) if rt else None
        is_outdoor = _is_outdoor(room_type)
        
        # For indoor types without preferences, no Vastu force.
        # For outdoor types, still apply anchor-only gentle pull.
        if not vastu_pref and not is_outdoor:
            return np.zeros(2)
        
        current_pos = self.positions[room_id]
        target_pos = self._get_vastu_target_position(room_type)
        
        # Vector toward target
        delta = target_pos - current_pos
        distance = np.linalg.norm(delta)
        
        if distance < 0.5:
            return np.zeros(2)  # Already close enough
        
        direction = delta / distance
        
        # Stronger force if in "avoid" direction
        if vastu_pref:
            weight = vastu_pref["weight"]
        else:
            # Outdoor anchor: gentler pull to avoid disturbing indoor layout
            weight = 0.4
        force_magnitude = self.params.vastu_force_strength * weight
        
        return force_magnitude * direction
    
    def _calculate_boundary_force(self, room_id: str) -> np.ndarray:
        """Calculate force to keep room within plot boundaries"""
        pos = self.positions[room_id]
        width, height = self.dimensions[room_id]
        force = np.zeros(2)

        # Polygon boundaries
        if self.plot_shape == "irregular" and self.plot_polygon:
            corners = [
                pos + np.array([-width/2, -height/2]),
                pos + np.array([width/2, -height/2]),
                pos + np.array([width/2, height/2]),
                pos + np.array([-width/2, height/2])
            ]
            
            for corner in corners:
                if not self._point_in_polygon(corner):
                    # Find nearest edge
                    min_dist = float('inf')
                    best_normal = np.zeros(2)
                    
                    n = len(self.plot_polygon)
                    for i in range(n):
                        edge_start = np.array(self.plot_polygon[i])
                        edge_end = np.array(self.plot_polygon[(i + 1) % n])
                        
                        proj, dist = self._project_point_to_edge(corner, edge_start, edge_end)
                        if dist < min_dist:
                            min_dist = dist
                            # Normal points inward
                            edge_vec = edge_end - edge_start
                            normal = np.array([-edge_vec[1], edge_vec[0]])
                            normal = normal / np.linalg.norm(normal)
                            # Check if normal points inward
                            center = np.mean(self.plot_polygon, axis=0)
                            if np.dot(normal, center - proj) < 0:
                                normal = -normal
                            best_normal = normal
                    
            # For irregular polygons, keep standard strength
            force += self.params.boundary_force_strength * min_dist * best_normal
            return force

        # Circular boundaries
        if self.plot_shape == "circular" and self.plot_circle:
            center = np.array(self.plot_circle.get("center", [self.plot_width/2, self.plot_length/2]))
            radius = float(self.plot_circle.get("radius", min(self.plot_width, self.plot_length)/2))
            # Apply force for each corner exceeding radius
            corners = [
                pos + np.array([-width/2, -height/2]),
                pos + np.array([width/2, -height/2]),
                pos + np.array([width/2, height/2]),
                pos + np.array([-width/2, height/2])
            ]
            for corner in corners:
                delta = corner - center
                dist = np.linalg.norm(delta)
                overflow = dist - radius
                if overflow > 0:
                    direction = delta / (dist if dist > 1e-6 else 1.0)
                    force -= self.params.boundary_force_strength * overflow * direction
            return force

        # Triangular boundaries
        if self.plot_shape == "triangular":
            # Left and top hard boundaries
            if pos[0] - width/2 < 0:
                force[0] += (self.params.boundary_force_strength * 5.0) * abs(pos[0] - width/2)
            if pos[1] - height/2 < 0:
                force[1] += (self.params.boundary_force_strength * 5.0) * abs(pos[1] - height/2)
            # Hypotenuse boundary: (x+w/2)/W + (y+h/2)/L <= 1
            corner = pos + np.array([width/2, height/2])
            val = corner[0] / self.plot_width + corner[1] / self.plot_length - 1.0
            if val > 0:
                grad = np.array([1.0 / self.plot_width, 1.0 / self.plot_length])
                # multiply force strength for triangular plots to prevent escape
                force -= (self.params.boundary_force_strength * 5.0) * val * grad * max(width, height)
            return force

        # Rectangular boundaries (default)
        if pos[0] - width/2 < 0:
            force[0] += self.params.boundary_force_strength * abs(pos[0] - width/2)
        if pos[0] + width/2 > self.plot_width:
            force[0] -= self.params.boundary_force_strength * (pos[0] + width/2 - self.plot_width)
        if pos[1] - height/2 < 0:
            force[1] += self.params.boundary_force_strength * abs(pos[1] - height/2)
        if pos[1] + height/2 > self.plot_length:
            force[1] -= self.params.boundary_force_strength * (pos[1] + height/2 - self.plot_length)
        return force
    
    def _calculate_all_forces(self, G: nx.Graph) -> Dict[str, np.ndarray]:
        """Calculate all forces for all rooms"""
        forces = {room_id: np.zeros(2) for room_id in self.positions.keys()}
        
        # 1. Attractive forces (adjacent rooms)
        for edge in G.edges(data=True):
            room1_id, room2_id, data = edge
            weight = data.get('weight', 1.0)
            force = self._calculate_attractive_force(room1_id, room2_id, weight)
            forces[room1_id] += force
            forces[room2_id] -= force
        
        # 2. Repulsive forces (non-adjacent rooms)
        room_ids = list(self.positions.keys())
        for i, room1_id in enumerate(room_ids):
            for room2_id in room_ids[i+1:]:
                if not G.has_edge(room1_id, room2_id):
                    is_outdoor_1 = bool(G.nodes[room1_id].get('is_outdoor', False))
                    is_outdoor_2 = bool(G.nodes[room2_id].get('is_outdoor', False))
                    force = self._calculate_repulsive_force(room1_id, room2_id)
                    if is_outdoor_1 and not is_outdoor_2:
                        # Push outdoor away from indoor without moving indoor
                        forces[room1_id] += force
                    elif is_outdoor_2 and not is_outdoor_1:
                        forces[room2_id] -= force
                    else:
                        # Symmetric for indoor-indoor and outdoor-outdoor
                        forces[room1_id] += force
                        forces[room2_id] -= force
        
        # 3. Vastu forces
        for room_id in self.positions.keys():
            room_type = G.nodes[room_id]['room_type']
            vastu_force = self._calculate_vastu_force(room_id, room_type)
            forces[room_id] += vastu_force
        
        # 4. Boundary forces
        for room_id in self.positions.keys():
            boundary_force = self._calculate_boundary_force(room_id)
            forces[room_id] += boundary_force
        
        return forces
    
    def _physics_step(self, G: nx.Graph) -> float:
        """Execute one physics simulation step, return max velocity"""
        # Calculate forces
        forces = self._calculate_all_forces(G)
        
        max_velocity = 0.0
        
        # Update velocities and positions
        for room_id in self.positions.keys():
            # Update velocity: v = (v + F) * damping
            # If node is fixed (phase-1 indoor), don't update its velocity/position
            if room_id in getattr(self, "fixed_nodes", set()):
                # ensure velocity zeroed
                self.velocities[room_id] = np.zeros(2)
                continue

            self.velocities[room_id] = (self.velocities[room_id] + forces[room_id]) * self.params.damping

            # Update position: pos = pos + v * dt
            self.positions[room_id] += self.velocities[room_id] * self.params.time_step
            
            # Enforce hard boundaries
            width, height = self.dimensions[room_id]
            if self.plot_shape == "irregular" and self.plot_polygon:
                self.positions[room_id] = self._project_inside_polygon(self.positions[room_id], width, height)
            elif self.plot_shape == "circular" and self.plot_circle:
                self.positions[room_id] = self._project_inside_circle(self.positions[room_id], width, height)
            elif self.plot_shape == "triangular":
                # Ensure left/top boundaries
                self.positions[room_id][0] = max(self.positions[room_id][0], width/2)
                self.positions[room_id][1] = max(self.positions[room_id][1], height/2)
                # Project corner onto hypotenuse if outside
                corner = self.positions[room_id] + np.array([width/2, height/2])
                val = corner[0] / self.plot_width + corner[1] / self.plot_length - 1.0
                if val > 0:
                    grad = np.array([1.0 / self.plot_width, 1.0 / self.plot_length])
                    alpha = val / np.dot(grad, grad)
                    corner = corner - alpha * grad
                    self.positions[room_id] = corner - np.array([width/2, height/2])
                # Extra safety: if center somehow outside polygon, snap back
                center = self.positions[room_id]
                if self.plot_polygon and not gu.point_in_polygon((float(center[0]), float(center[1])), self.plot_polygon):
                    proj = gu.project_point_inside((float(center[0]), float(center[1])), self.plot_polygon)
                    # project returns a point; keep same relative offset of center
                    self.positions[room_id] = np.array(proj)
                # Ensure all corners are inside after snapping
                self.positions[room_id] = self._project_inside_polygon(self.positions[room_id], width, height)
            else:
                self.positions[room_id][0] = np.clip(
                    self.positions[room_id][0],
                    width/2,
                    self.plot_width - width/2
                )
                self.positions[room_id][1] = np.clip(
                    self.positions[room_id][1],
                    height/2,
                    self.plot_length - height/2
                )
            
            # Track max velocity for convergence check
            velocity_magnitude = np.linalg.norm(self.velocities[room_id])
            max_velocity = max(max_velocity, velocity_magnitude)
        
        return max_velocity
    
    def _run_simulation(self, G: nx.Graph) -> Tuple[bool, int]:
        """Run physics simulation until convergence or max iterations"""
        logger.info("Starting physics simulation...")
        
        for iteration in range(self.params.max_iterations):
            max_velocity = self._physics_step(G)
            
            # Check convergence
            if max_velocity < self.params.convergence_threshold:
                logger.info(f"Converged at iteration {iteration} (max_velocity={max_velocity:.4f})")
                return True, iteration + 1
            
            if iteration % 20 == 0:
                logger.debug(f"Iteration {iteration}: max_velocity={max_velocity:.4f}")
        
        logger.warning(f"Did not converge after {self.params.max_iterations} iterations")
        return False, self.params.max_iterations
    
    # ========================================================================
    # OVERLAP RESOLUTION
    # ========================================================================
    
    def _check_overlap(self, room1_id: str, room2_id: str) -> bool:
        """Check if two rooms overlap"""
        pos1 = self.positions[room1_id]
        pos2 = self.positions[room2_id]
        w1, h1 = self.dimensions[room1_id]
        w2, h2 = self.dimensions[room2_id]
        
        # Convert center positions to corner positions
        x1 = pos1[0] - w1/2
        y1 = pos1[1] - h1/2
        x2 = pos2[0] - w2/2
        y2 = pos2[1] - h2/2
        
        return (x1 < x2 + w2 and x1 + w1 > x2 and
                y1 < y2 + h2 and y1 + h1 > y2)
    
    def _resolve_overlaps(self) -> int:
        """Post-process to resolve any remaining overlaps"""
        max_iterations = 20
        overlap_count = 0
        
        for iteration in range(max_iterations):
            overlaps_resolved = 0
            room_ids = list(self.positions.keys())
            
            for i, room1_id in enumerate(room_ids):
                for room2_id in room_ids[i+1:]:
                    if self._check_overlap(room1_id, room2_id):
                        overlaps_resolved += 1
                        
                        # Calculate separation vector
                        pos1 = self.positions[room1_id]
                        pos2 = self.positions[room2_id]
                        delta = pos1 - pos2
                        distance = np.linalg.norm(delta)
                        
                        if distance < 0.1:
                            # Random push if centers coincide
                            delta = np.random.uniform(-1, 1, 2)
                            distance = np.linalg.norm(delta)
                        
                        direction = delta / distance
                        
                        # Calculate overlap amount
                        w1, h1 = self.dimensions[room1_id]
                        w2, h2 = self.dimensions[room2_id]
                        required_separation = (max(w1, w2) + max(h1, h2)) / 2
                        
                        # Push apart
                        push = (required_separation - distance) / 2
                        self.positions[room1_id] += direction * push
                        self.positions[room2_id] -= direction * push
                        
                        # Enforce boundaries
                        for room_id in [room1_id, room2_id]:
                            w, h = self.dimensions[room_id]
                            if self.plot_shape == "irregular" and self.plot_polygon:
                                self.positions[room_id] = self._project_inside_polygon(self.positions[room_id], w, h)
                            elif self.plot_shape == "triangular":
                                self.positions[room_id][0] = max(self.positions[room_id][0], w/2)
                                self.positions[room_id][1] = max(self.positions[room_id][1], h/2)
                                corner = self.positions[room_id] + np.array([w/2, h/2])
                                val = corner[0] / self.plot_width + corner[1] / self.plot_length - 1.0
                                if val > 0:
                                    grad = np.array([1.0 / self.plot_width, 1.0 / self.plot_length])
                                    alpha = val / np.dot(grad, grad)
                                    corner = corner - alpha * grad
                                    self.positions[room_id] = corner - np.array([w/2, h/2])
                            else:
                                self.positions[room_id][0] = np.clip(
                                    self.positions[room_id][0], w/2, self.plot_width - w/2
                                )
                                self.positions[room_id][1] = np.clip(
                                    self.positions[room_id][1], h/2, self.plot_length - h/2
                                )
            
            overlap_count = overlaps_resolved
            if overlaps_resolved == 0:
                break
        
        if overlap_count > 0:
            logger.warning(f"Could not resolve all overlaps ({overlap_count} remaining)")
        
        return overlap_count
    
    # ========================================================================
    # SCORING
    # ========================================================================
    def _infer_direction_from_pos(self, pos: np.ndarray) -> Direction:
        """Infer Vastu direction from a room center position relative to plot.

        Uses the same orientation convention as `_get_vastu_target_position`:
        smaller y => north, smaller x => east.
        """
        fx = pos[0] / self.plot_width if self.plot_width > 0 else 0.5
        fy = pos[1] / self.plot_length if self.plot_length > 0 else 0.5

        # Near center tolerance
        if abs(fx - 0.5) < 0.15 and abs(fy - 0.5) < 0.15:
            return Direction.CENTER

        # Column buckets
        if fx < 0.33:
            col = "left"  # maps to EAST in this coordinate convention
        elif fx > 0.66:
            col = "right"  # maps to WEST
        else:
            col = "center"

        # Row buckets
        if fy < 0.33:
            row = "top"  # NORTH
        elif fy > 0.66:
            row = "bottom"  # SOUTH
        else:
            row = "center"

        if row == "top":
            if col == "left":
                return Direction.NORTHEAST
            elif col == "center":
                return Direction.NORTH
            else:
                return Direction.NORTHWEST
        elif row == "bottom":
            if col == "left":
                return Direction.SOUTHEAST
            elif col == "center":
                return Direction.SOUTH
            else:
                return Direction.SOUTHWEST
        else:
            if col == "left":
                return Direction.EAST
            elif col == "right":
                return Direction.WEST
            else:
                return Direction.CENTER

    def _calculate_score(self, G: nx.Graph) -> float:
        """Calculate quality score (0-100)"""
        score = 100.0
        
        # 1. Penalty for overlaps
        overlap_count = 0
        room_ids = list(self.positions.keys())
        for i, room1_id in enumerate(room_ids):
            for room2_id in room_ids[i+1:]:
                if self._check_overlap(room1_id, room2_id):
                    overlap_count += 1
                    score -= 15  # Heavy penalty per overlap
        
        # 2. Penalty for poor adjacency (connected rooms too far)
        for edge in G.edges():
            room1_id, room2_id = edge
            distance = np.linalg.norm(self.positions[room1_id] - self.positions[room2_id])
            if distance > 10:  # Rooms should be within 10m
                score -= (distance - 10) * 0.5
        
        # 3. Penalty for rooms out of bounds
        for room_id, pos in self.positions.items():
            w, h = self.dimensions[room_id]
            
            if self.plot_shape == "irregular" and self.plot_polygon:
                # Check all corners
                corners = [
                    pos + np.array([-w/2, -h/2]),
                    pos + np.array([w/2, -h/2]),
                    pos + np.array([w/2, h/2]),
                    pos + np.array([-w/2, h/2])
                ]
                
                for corner in corners:
                    if not self._point_in_polygon(corner):
                        # Find distance to nearest edge
                        min_dist = float('inf')
                        n = len(self.plot_polygon)
                        for i in range(n):
                            edge_start = np.array(self.plot_polygon[i])
                            edge_end = np.array(self.plot_polygon[(i + 1) % n])
                            _, dist = self._project_point_to_edge(corner, edge_start, edge_end)
                            min_dist = min(min_dist, dist)
                        
                        score -= min(10, min_dist * 2)
            
            elif self.plot_shape == "triangular":
                # Left/top bounds
                if pos[0] - w/2 < 0 or pos[1] - h/2 < 0:
                    score -= 10
                # Hypotenuse overflow
                corner = pos + np.array([w/2, h/2])
                val = corner[0] / self.plot_width + corner[1] / self.plot_length - 1.0
                if val > 0:
                    score -= min(10, val * 100)
            
            else:
                # Rectangular bounds
                if (pos[0] - w/2 < 0 or pos[0] + w/2 > self.plot_width or
                    pos[1] - h/2 < 0 or pos[1] + h/2 > self.plot_length):
                    score -= 10

        # 4. Vastu direction compliance and zoning bonuses
        for room_id, pos in self.positions.items():
            room_type_raw = G.nodes[room_id].get('room_type')
            rt = self._normalize_room_type(room_type_raw)
            is_outdoor = _is_outdoor(room_type_raw)

            # Get preferences (indoor via enum, outdoor via string map)
            prefs: Optional[Dict[str, Any]] = None
            if rt:
                prefs = VASTU_PREFERENCES.get(rt)
            if is_outdoor and prefs is None:
                prefs = OUTDOOR_VASTU_PREFERENCES.get(str(room_type_raw).lower(), None)

            if not prefs:
                continue

            direction = self._infer_direction_from_pos(pos)
            weight = float(prefs.get("weight", 0.5)) if isinstance(prefs, dict) else 0.5
            preferred = set(prefs.get("preferred", [])) if isinstance(prefs, dict) else set()
            acceptable = set(prefs.get("acceptable", [])) if isinstance(prefs, dict) else set()
            avoid = set(prefs.get("avoid", [])) if isinstance(prefs, dict) else set()

            if direction in preferred:
                score += 1.5 * weight
            elif direction in acceptable:
                score += 0.5 * weight
            elif direction in avoid:
                score -= 2.0 * weight

        # 5. Aspect ratio penalty for unrealistic elongated rooms
        for room_id, (w, h) in self.dimensions.items():
            if w and h and min(w, h) > 0:
                ratio = max(w, h) / min(w, h)
                if ratio > 2.2:
                    score -= (ratio - 2.2) * 3.0
        
        return max(0, min(100, score))
    
    # ========================================================================
    # MAIN SOLVE METHOD
    # ========================================================================
    
    def solve(self, request: SolverRequest) -> SolverResponse:
        """
        Main entry point for graph-based solver.
        Target: <2 seconds for typical layouts.
        """
        import time
        start_time = time.time()
        
        warnings = []
        # Ensure graph reference exists for scoring phase
        G = None  # type: ignore
        
        try:
            # Make sure solver has up-to-date plot shape and constraints
            self.plot_shape = getattr(request, "plot_shape", self.plot_shape)
            self.constraints = request.constraints or {}
            # Parse polygon constraints if irregular shape
            if self.plot_shape == "irregular" and request.constraints:
                polygon_data = request.constraints.get("plot_polygon")
                if polygon_data and isinstance(polygon_data, list):
                    self.plot_polygon = polygon_data
                    logger.info(f"Loaded irregular polygon with {len(self.plot_polygon)} vertices")
                else:
                    warnings.append("Irregular plot shape specified but no valid plot_polygon in constraints")
                    self.plot_shape = "rectangular"
            # Parse circle constraints
            if (self.plot_shape == "circular") or (request.constraints and request.constraints.get("circle")):
                circle_data = (request.constraints or {}).get("circle")
                if circle_data and isinstance(circle_data, dict):
                    center = circle_data.get("center")
                    radius = circle_data.get("radius")
                    if isinstance(center, (list, tuple)) and len(center) == 2 and isinstance(radius, (int, float)):
                        self.plot_circle = {"center": list(center), "radius": float(radius)}
                        self.plot_shape = "circular"
                        logger.info(f"Loaded circular plot with radius {radius}")
                    else:
                        warnings.append("Circular plot specified but invalid circle constraints; defaulting to inferred circle")
                        self.plot_circle = {"center": [self.plot_width/2, self.plot_length/2], "radius": min(self.plot_width, self.plot_length)/2}
                        self.plot_shape = "circular"
                elif self.plot_shape == "circular":
                    # Infer circle from plot dimensions
                    self.plot_circle = {"center": [self.plot_width/2, self.plot_length/2], "radius": min(self.plot_width, self.plot_length)/2}
                    logger.info("Inferred circular plot from dimensions")
            
            # Two-phase solving: place indoor rooms first, then outdoor fixtures
            outdoor_list = set(request.outdoor_fixtures or [])

            def _is_room_outdoor(room: Dict[str, Any]) -> bool:
                # Mark outdoor based on explicit list (id or type) or by type heuristic
                if _is_outdoor(room.get("type", "")):
                    return True
                if room.get("id") in outdoor_list or room.get("type") in outdoor_list:
                    return True
                return False

            indoor_rooms = [r for r in request.rooms if not _is_room_outdoor(r)]
            outdoor_rooms = [r for r in request.rooms if _is_room_outdoor(r)]

            # Phase 1: indoor-only placement
            if indoor_rooms:
                G_indoor = self._build_adjacency_graph(indoor_rooms)
                self._initialize_positions(indoor_rooms)
                converged, iterations = self._run_simulation(G_indoor)
                overlap_count = self._resolve_overlaps()
                if overlap_count > 0:
                    warnings.append(f"Phase-1: {overlap_count} indoor overlaps remain")
                # Freeze indoor nodes for phase 2
                self.fixed_nodes = set(r["id"] for r in indoor_rooms)
                # If there are no outdoor rooms, use the indoor graph for scoring
                G = G_indoor
            else:
                converged, iterations = True, 0

            # Phase 2: place outdoor fixtures into remaining space (if any)
            if outdoor_rooms:
                # initialize outdoor room positions (will not overwrite indoor positions)
                self._initialize_positions(outdoor_rooms)
                # build full graph (indoor nodes will be present and fixed)
                G = self._build_adjacency_graph(request.rooms)
                converged2, iterations2 = self._run_simulation(G)
                # merge iteration counts
                iterations = iterations + (iterations2 if 'iterations2' in locals() else 0)
                if not converged2:
                    warnings.append("Phase-2: outdoor placement did not fully converge")
                overlap_count2 = self._resolve_overlaps()
                if overlap_count2 > 0:
                    warnings.append(f"Phase-2: {overlap_count2} overlaps remain after outdoor placement")
            else:
                # no outdoor rooms, ensure we at least had a graph run above
                if not indoor_rooms:
                    G = self._build_adjacency_graph(request.rooms)
                    self._initialize_positions(request.rooms)
                    converged, iterations = self._run_simulation(G)
            
            if not converged:
                warnings.append("Physics simulation did not fully converge")
            
            # Resolve any remaining overlaps
            overlap_count = self._resolve_overlaps()
            if overlap_count > 0:
                warnings.append(f"{overlap_count} room overlaps could not be resolved")
            
            # Calculate score
            # Guard against uninitialized graph reference
            if G is None:
                # Build a graph from whatever rooms we have positions for
                rooms_for_graph = request.rooms if request.rooms else []
                G = self._build_adjacency_graph(rooms_for_graph)
            score = self._calculate_score(G)
            
            # Build response
            result_rooms = []
            for room_data in request.rooms:
                room_id = room_data["id"]
                pos = self.positions[room_id]
                width, height = self.dimensions[room_id]
                
                # Convert center position to corner position
                x = pos[0] - width / 2
                y = pos[1] - height / 2
                
                room = Room(
                    id=room_id,
                    name=room_data["name"],
                    type=room_data["type"],
                    x=round(x, 2),
                    y=round(y, 2),
                    width=round(width, 2),
                    height=round(height, 2),
                    direction=room_data.get("direction")
                )
                room.calculate_area()
                result_rooms.append(room)
            
            generation_time = time.time() - start_time
            logger.info(f"Graph solver complete: {generation_time:.2f}s, score={score:.1f}")
            
            return SolverResponse(
                rooms=result_rooms,
                score=round(score, 2),
                iterations=iterations,
                solver_type="graph",
                generation_time=round(generation_time, 3),
                converged=converged,
                warnings=warnings
            )
        
        except Exception as e:
            logger.error(f"Graph solver error: {str(e)}", exc_info=True)
            raise


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def solve_floor_plan(request: SolverRequest) -> SolverResponse:
    """
    Entry point for the graph-based solver.
    Fast physics-based layout generation.
    """
    solver = GraphBasedLayoutSolver(
        plot_width=request.plot_width,
        plot_length=request.plot_length,
        plot_shape=getattr(request, "plot_shape", "rectangular"),
        seed=request.seed
    )
    return solver.solve(request)