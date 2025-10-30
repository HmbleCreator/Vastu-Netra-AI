"""
Force-directed graph solver implementation using agent-based physics.
"""
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
import numpy as np
import logging
import copy
from shapely.geometry import box, Point, Polygon
from shapely import affinity
from .phi_grid import PhiGrid

logger = logging.getLogger(__name__)

class SpatialIndex:
    """Spatial index supporting both grid and rtree implementations with automatic fallback.
    
    Will use rtree if available for better performance, otherwise falls back to grid-based indexing.
    """
    def __init__(self, rooms: List[Any], grid_size: float = 1.0):
        self.rooms = rooms
        self.grid_size = grid_size
        self.use_rtree = False
        self.grid = {}  # Initialize grid regardless of rtree success
        
        # Try to import and use rtree
        try:
            from rtree import index
            logger.info("Successfully imported rtree")
            
            # Create rtree index
            p = index.Property()
            p.dimension = 2
            self.idx = index.Index(properties=p)
            logger.info("Created rtree index")
            
            for i, room in enumerate(rooms):
                bounds = room.polygon.bounds
                self.idx.insert(i, bounds)
            
            logger.info("Successfully inserted all rooms into rtree index")
            self.use_rtree = True
            return  # Skip grid initialization if rtree succeeds
                
        except ImportError as e:
            logger.info(f"rtree not available ({str(e)}), using grid-based spatial index")
        except Exception as e:
            logger.warning(f"Failed to initialize rtree index ({str(e)}), falling back to grid")
        
        # Initialize grid-based index if rtree failed
        for i, room in enumerate(rooms):
            bounds = room.polygon.bounds
            min_x = int(bounds[0] / grid_size)
            min_y = int(bounds[1] / grid_size)
            max_x = int(bounds[2] / grid_size) + 1
            max_y = int(bounds[3] / grid_size) + 1
            
            for x in range(min_x, max_x):
                for y in range(min_y, max_y):
                    cell = (x, y)
                    if cell not in self.grid:
                        self.grid[cell] = []
                    self.grid[cell].append(i)
            # Fall back to grid implementation
            self.grid = {}
            
            # Insert room polygons into grid cells
            for i, room in enumerate(rooms):
                bounds = room.polygon.bounds
                min_x = int(bounds[0] / grid_size)
                min_y = int(bounds[1] / grid_size)
                max_x = int(bounds[2] / grid_size) + 1
                max_y = int(bounds[3] / grid_size) + 1
                
                for x in range(min_x, max_x):
                    for y in range(min_y, max_y):
                        cell = (x, y)
                        if cell not in self.grid:
                            self.grid[cell] = []
                        self.grid[cell].append(i)
    
    def query_overlaps(self, polygon: Polygon) -> Set[int]:
        """Find rooms that might overlap with given polygon using either rtree or grid."""
        bounds = polygon.bounds
        candidates = set()
        
        if self.use_rtree:
            # Use rtree for efficient spatial querying
            candidates.update(self.idx.intersection(bounds))
        else:
            # Fall back to grid-based querying
            min_x = int(bounds[0] / self.grid_size)
            min_y = int(bounds[1] / self.grid_size)
            max_x = int(bounds[2] / self.grid_size) + 1
            max_y = int(bounds[3] / self.grid_size) + 1
            
            for x in range(min_x, max_x):
                for y in range(min_y, max_y):
                    cell = (x, y)
                    if cell in self.grid:
                        candidates.update(self.grid[cell])
        
        # Filter candidates for actual overlaps
        return {i for i in candidates if polygon.intersects(self.rooms[i].polygon)}
        min_y = int(bounds[1] / self.grid_size)
        max_x = int(bounds[2] / self.grid_size) + 1
        max_y = int(bounds[3] / self.grid_size) + 1
        
        candidates = set()
        for x in range(min_x, max_x):
            for y in range(min_y, max_y):
                cell = (x, y)
                if cell in self.grid:
                    candidates.update(self.grid[cell])
        return candidates
    
    def query_nearby(self, polygon: Polygon, distance: float) -> Set[int]:
        """Find rooms within given distance of polygon."""
        expanded_bounds = (
            polygon.bounds[0] - distance,
            polygon.bounds[1] - distance,
            polygon.bounds[2] + distance,
            polygon.bounds[3] + distance
        )
        min_x = int(expanded_bounds[0] / self.grid_size)
        min_y = int(expanded_bounds[1] / self.grid_size)
        max_x = int(expanded_bounds[2] / self.grid_size) + 1
        max_y = int(expanded_bounds[3] / self.grid_size) + 1
        
        candidates = set()
        for x in range(min_x, max_x):
            for y in range(min_y, max_y):
                cell = (x, y)
                if cell in self.grid:
                    candidates.update(self.grid[cell])
        return candidates

@dataclass
class RoomState:
    id: str
    type: str
    width: float
    height: float
    polygon: Polygon
    theta: float = 0.0
    original_area: float = 0.0

    def __post_init__(self):
        # Record original area for SA energy calculations
        try:
            self.original_area = float(self.polygon.area)
        except Exception:
            self.original_area = 0.0

    @property
    def center(self) -> Point:
        """Get room center."""
        return self.polygon.centroid

    def update_polygon(self):
        """Update polygon representation from center and dimensions.

        This helper will re-create a rectangular polygon centered at the current centroid
        using width/height.
        """
        cx, cy = self.center.x, self.center.y
        half_w = self.width / 2
        half_h = self.height / 2
        self.polygon = box(cx - half_w, cy - half_h, cx + half_w, cy + half_h)
        self.original_area = float(self.polygon.area)
        return self

    def copy(self) -> 'RoomState':
        """Return a deep copy of this RoomState (polygon cloned)."""
        new_poly = copy.deepcopy(self.polygon)
        return RoomState(
            id=self.id,
            type=self.type,
            width=self.width,
            height=self.height,
            polygon=new_poly,
            theta=self.theta,
            original_area=self.original_area
        )

@dataclass
class GraphSolverParams:
    dt: float = 0.1  # time step
    mu: float = 0.8  # damping
    alpha_v: float = 1.2  # vastu force weight
    alpha_r: float = 0.8  # repulsion weight
    alpha_a: float = 0.7  # adjacency weight
    alpha_b: float = 2.0  # boundary weight
    alpha_c: float = 1.0  # circulation weight
    iter_max: int = 800
    convergence_tol: float = 0.01
    repulsion_radius: float = 5.0  # meters
    repulsion_exponent: float = 1.5
    room_min_size: float = 1.0  # minimum room dimension in meters
    # Added parameters
    initial_spread: float = 0.5  # factor for initial placement spread
    boundary_margin: float = 0.2  # meters, keep rooms this far from plot boundary
    aspect_ratio_range: Tuple[float, float] = (0.5, 2.0)

@dataclass
class SolverState:
    rooms: List[RoomState]
    iterations: int = 0
    converged: bool = False
    metrics: Dict = field(default_factory=dict)

# Adjacency preferences (simplified version)
ADJACENCY_PREFS = {
    "kitchen": {"dining", "living"},
    "master_bedroom": {"bathroom"},
    "bedroom": {"bathroom"},
    "living": {"dining", "entrance"},
    "dining": {"kitchen", "living"},
    "entrance": {"living"}
}


def compute_overlap_area(r1: RoomState, r2: RoomState) -> float:
    """Compute overlap area between two rooms."""
    if r1.polygon is None or r2.polygon is None:
        return 0.0
    # polygons are shapely.geometry.Polygon instances
    try:
        return float(r1.polygon.intersection(r2.polygon).area)
    except Exception:
        return 0.0

def normalize_vector(x: float, y: float) -> Tuple[float, float]:
    """Normalize 2D vector."""
    mag = np.sqrt(x*x + y*y)
    if mag < 1e-10:
        return (0.0, 0.0)
    return (x/mag, y/mag)

class GraphSolver:
    """Force-directed graph solver using physics-based optimization."""
    
    def __init__(self,
                room_polygons: List[Polygon],
                boundary_polygon: Polygon,
                adjacency_graph: Dict[int, List[int]],
                params: Optional[GraphSolverParams] = None):
        """Initialize solver with room shapes and constraints."""
        self.room_polygons = room_polygons
        self.boundary_polygon = boundary_polygon
        self.adjacency_graph = adjacency_graph
        self.params = params or GraphSolverParams()
        self.best_state = None
        self.best_energy = float('inf')
        
        # Create initial room states at random positions within boundary
        bounds = boundary_polygon.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        
        self.rooms = []
        for i, poly in enumerate(room_polygons):
            # Random position near center
            x = center_x + np.random.normal(0, width/6)
            y = center_y + np.random.normal(0, height/6)
            # translate polygon to initial random position
            placed_poly = affinity.translate(poly, x, y)
            room = RoomState(
                id=str(i),
                type=f"room_{i}",
                width=placed_poly.bounds[2] - placed_poly.bounds[0],
                height=placed_poly.bounds[3] - placed_poly.bounds[1],
                polygon=placed_poly
            )
            self.rooms.append(room)
    
    def compute_forces(self, state: List[RoomState]) -> List[Tuple[float, float]]:
        """Compute net force on each room."""
        forces = [(0.0, 0.0) for _ in state]
        params = self.params
        
        # Room-room repulsion and adjacency forces
        for i, room in enumerate(state):
            room_centroid = room.polygon.centroid
            
            for j, other in enumerate(state):
                if i == j:
                    continue
                    
                other_centroid = other.polygon.centroid
                
                # Get vector from other to room
                dx = room_centroid.x - other_centroid.x
                dy = room_centroid.y - other_centroid.y
                dist = np.sqrt(dx*dx + dy*dy)
                
                if dist < 1e-6:
                    continue
                    
                # Normalized direction
                dx, dy = dx/dist, dy/dist
                
                # Repulsion force
                if dist < params.repulsion_radius:
                    magnitude = params.alpha_r * (
                        (params.repulsion_radius/dist)**params.repulsion_exponent - 1
                    )
                    forces[i] = (
                        forces[i][0] + magnitude * dx,
                        forces[i][1] + magnitude * dy
                    )
                
                # Adjacency attraction
                if j in self.adjacency_graph.get(i, []):
                    magnitude = -params.alpha_a * dist
                    forces[i] = (
                        forces[i][0] + magnitude * dx,
                        forces[i][1] + magnitude * dy
                    )
        
        # Boundary containment force
        for i, room in enumerate(state):
            if not self.boundary_polygon.contains(room.polygon):
                boundary_centroid = self.boundary_polygon.centroid
                room_centroid = room.polygon.centroid
                
                # Push toward boundary center
                dx = boundary_centroid.x - room_centroid.x
                dy = boundary_centroid.y - room_centroid.y
                dist = np.sqrt(dx*dx + dy*dy)
                
                if dist > 1e-6:
                    dx, dy = dx/dist, dy/dist
                    magnitude = params.alpha_b
                    forces[i] = (
                        forces[i][0] + magnitude * dx,
                        forces[i][1] + magnitude * dy
                    )
        
        return forces
    
    def update_state(self, state: List[RoomState], forces: List[Tuple[float, float]],
                   dt: float) -> List[RoomState]:
        """Update room positions based on forces."""
        new_state = []
        for room, (fx, fy) in zip(state, forces):
            # Apply damping
            fx *= (1 - self.params.mu)
            fy *= (1 - self.params.mu)
            
            # Update position using shapely translate
            new_polygon = affinity.translate(room.polygon, fx * dt, fy * dt)
            new_centroid = new_polygon.centroid
            
            # Create new state
            new_room = RoomState(
                id=room.id,
                type=room.type,
                width=room.width,
                height=room.height,
                polygon=new_polygon,
                theta=room.theta
            )
            new_state.append(new_room)
            
        return new_state
    
    def compute_energy(self, state: List[RoomState]) -> float:
        """Compute total system energy (lower is better)."""
        energy = 0.0
        
        # Room-room overlap and adjacency energy
        for i, room in enumerate(state):
            for j, other in enumerate(state[i+1:], i+1):
                # Overlap penalty
                if room.polygon.intersects(other.polygon):
                    energy += room.polygon.intersection(other.polygon).area * 1000
                
                # Adjacency reward/penalty
                dist = room.polygon.distance(other.polygon)
                if j in self.adjacency_graph.get(i, []):
                    energy += dist * 10  # Penalize non-adjacent required rooms
                else:
                    energy -= np.log1p(dist)  # Small reward for separation
        
        # Boundary containment
        for room in state:
            if not self.boundary_polygon.contains(room.polygon):
                energy += room.polygon.difference(self.boundary_polygon).area * 1000

        return energy
    
    def solve(self, max_iterations: int = 1000) -> SolverState:
        """Run force-directed optimization."""
        current_state = self.rooms
        current_energy = self.compute_energy(current_state)
        
        self.best_state = current_state
        self.best_energy = current_energy
        
        dt = self.params.dt
        iter_count = 0
        stall_count = 0
        
        while iter_count < max_iterations and stall_count < 100:
            # Compute and apply forces
            forces = self.compute_forces(current_state)
            new_state = self.update_state(current_state, forces, dt)
            new_energy = self.compute_energy(new_state)
            
            # Update best solution
            if new_energy < self.best_energy:
                self.best_state = new_state
                self.best_energy = new_energy
                stall_count = 0
            else:
                stall_count += 1
            
            # Continue with new state
            current_state = new_state
            current_energy = new_energy
            iter_count += 1
            
            # Optionally reduce time step
            if stall_count > 50:
                dt *= 0.99
        
        # Return best state found with metrics
        converged = stall_count < 100
        metrics = {
            'graph_energy': self.best_energy,
            'final_energy': self.best_energy
        }
        return SolverState(rooms=self.best_state, iterations=iter_count, converged=converged, metrics=metrics)
