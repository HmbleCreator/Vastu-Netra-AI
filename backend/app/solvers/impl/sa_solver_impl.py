"""
Enhanced simulated annealing solver implementation.
"""
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
import logging
from .phi_grid import PhiGrid, Point, Polygon
from shapely import affinity
from shapely.geometry import Point as ShapelyPoint, Polygon as ShapelyPolygon
from .graph_solver_impl import RoomState, SolverState, SpatialIndex

logger = logging.getLogger(__name__)

@dataclass
class SAParams:
    T0: float = 1.0  # initial temperature
    alpha: float = 0.995  # cooling rate
    max_iters: int = 3000
    stall_patience: int = 300
    cooling_step: int = 10
    local_repair_interval: int = 100
    min_temp: float = 1e-3
    # Move parameters
    trans_sigma: float = 0.5  # meters
    resize_min: float = 0.9
    resize_max: float = 1.1
    move_probs: Dict[str, float] = None  # weights for different moves
    allow_rotations: bool = False
    hop_radius: float = 3.0  # meters for vastu hop
    # Grid snap parameters
    grid_snap: float = 0.01  # meters
    slide_steps: int = 10
    slide_step: float = 0.1  # meters
    overlap_tolerance: float = 1e-3  # m²
    # Energy weights
    lambda_overlap: float = 1e5
    lambda_vastu: float = 1.0
    lambda_adjacency: float = 0.8
    lambda_circulation: float = 1.2
    lambda_boundary: float = 2.0
    lambda_alignment: float = 0.5
    lambda_area: float = 0.7
    hard_violation_penalty: float = 1e6

def compute_energy(rooms: List[RoomState], req: Dict, phi: PhiGrid,
                  params: SAParams) -> float:
    """Compute total layout energy (lower is better).
    
    Combines multiple energy terms:
    - Overlap penalty between rooms
    - Vastu potential energy from phi grid
    - Adjacency satisfaction
    - Circulation space requirements
    - Boundary containment
    - Room area preservation
    - Alignment bonus
    """
    energy = 0.0
    spatial_index = SpatialIndex(rooms)
    boundary = req['plot']

    # Room overlaps
    for i, room in enumerate(rooms):
        for other in spatial_index.query_overlaps(room.polygon):
            if other != i:
                overlap_area = room.polygon.intersection(rooms[other].polygon).area
                energy += params.lambda_overlap * max(0, overlap_area - params.overlap_tolerance)

    # Vastu potential
    for room in rooms:
        centroid = room.polygon.centroid
        vastu_potential = phi.sample_phi(centroid.x, centroid.y)
        energy -= params.lambda_vastu * vastu_potential

    # Adjacency satisfaction
    required_adj = req.get('adjacency', {})
    for i, room in enumerate(rooms):
        for j, other in enumerate(rooms):
            if i < j:  # Avoid counting pairs twice
                if j in required_adj.get(i, []):
                    # Penalize required adjacencies that aren't satisfied
                    if not room.polygon.touches(rooms[j].polygon):
                        dist = room.polygon.distance(rooms[j].polygon)
                        energy += params.lambda_adjacency * dist
                else:
                    # Small bonus for non-required rooms being non-adjacent
                    if room.polygon.touches(rooms[j].polygon):
                        energy += params.lambda_adjacency * 0.1

    # Circulation space
    for room in rooms:
        min_clearance = req.get('min_circulation', 0.8)  # meters
        for other in spatial_index.query_nearby(room.polygon, min_clearance):
            if room != other:
                dist = room.polygon.distance(rooms[other].polygon)
                if dist < min_clearance:
                    energy += params.lambda_circulation * (min_clearance - dist)

    # Boundary containment
    for room in rooms:
        if not boundary.contains(room.polygon):
            # Compute area of room outside boundary
            outside_area = room.polygon.difference(boundary).area
            energy += params.lambda_boundary * outside_area

    # Room area preservation
    for i, room in enumerate(rooms):
        target_area = req['rooms'][i].get('area', room.original_area)
        area_diff = abs(room.polygon.area - target_area)
        energy += params.lambda_area * area_diff

    # Alignment bonus (slight reward for aligned edges)
    if params.lambda_alignment > 0:
        for i, room in enumerate(rooms):
            for j, other in enumerate(rooms):
                if i < j:
                    if rooms_have_aligned_edges(room.polygon, rooms[j].polygon):
                        energy -= params.lambda_alignment

    return energy

def rooms_have_aligned_edges(poly1: Polygon, poly2: Polygon, tolerance: float = 0.1) -> bool:
    """Check if two rooms have any aligned edges."""
    # Get coordinates of all edges
    edges1 = list(zip(poly1.exterior.coords[:-1], poly1.exterior.coords[1:]))
    edges2 = list(zip(poly2.exterior.coords[:-1], poly2.exterior.coords[1:]))
    
    # Check for alignment between any pair of edges
    for (x1, y1), (x2, y2) in edges1:
        for (x3, y3), (x4, y4) in edges2:
            # Compute slopes safely (handle vertical edges)
            def _slope(xa, ya, xb, yb):
                if abs(xb - xa) < 1e-9:
                    return None
                return (yb - ya) / (xb - xa)

            s1 = _slope(x1, y1, x2, y2)
            s2 = _slope(x3, y3, x4, y4)

            slopes_aligned = False
            if s1 is None and s2 is None:
                slopes_aligned = True
            elif s1 is not None and s2 is not None and abs(s1 - s2) < tolerance:
                slopes_aligned = True

            if slopes_aligned:
                # Check if the edges are spatially close (endpoints near each other)
                if min(abs(y1 - y3), abs(y2 - y4), abs(x1 - x3), abs(x2 - x4)) < tolerance:
                    return True
    return False

def propose_move(current: List[RoomState], req: Dict,
                params: SAParams) -> List[RoomState]:
    """Generate candidate state by applying random move.
    
    Available moves:
    1. Translation - Move room by random delta
    2. Rotation - Rotate room around its centroid (if allowed)
    3. Resizing - Scale room while preserving area
    4. Vastu Hop - Jump to high-potential location
    5. Edge Alignment - Snap to nearby room edges
    """
    # Copy current state
    new_state = [r.copy() for r in current]

    # Default move probabilities if not specified
    if not params.move_probs:
        params.move_probs = {
            'translate': 0.5,
            'rotate': 0.1 if params.allow_rotations else 0,
            'resize': 0.2,
            'vastu_hop': 0.1,
            'align': 0.1
        }

    # Select random room
    room_idx = np.random.randint(len(current))
    room = new_state[room_idx]

    # Choose move type based on probabilities
    move_keys = list(params.move_probs.keys())
    move_probs = np.array([params.move_probs[k] for k in move_keys], dtype=float)
    s = move_probs.sum()
    if s <= 0:
        # fallback to uniform
        move_probs = np.ones_like(move_probs) / len(move_probs)
    else:
        move_probs = move_probs / s
    move_type = np.random.choice(move_keys, p=move_probs)

    if move_type == 'translate':
        # Random translation
        dx = np.random.normal(0, params.trans_sigma)
        dy = np.random.normal(0, params.trans_sigma)
        room.polygon = affinity.translate(room.polygon, xoff=dx, yoff=dy)

    elif move_type == 'rotate' and params.allow_rotations:
        # Random rotation around centroid (angle in radians -> degrees for shapely)
        angle = np.random.normal(0, np.pi/6)
        angle_deg = np.degrees(angle)
        room.polygon = affinity.rotate(room.polygon, angle_deg, origin='centroid')

    elif move_type == 'resize':
        # Random scaling while preserving area
        scale_x = np.random.uniform(params.resize_min, params.resize_max)
        scale_y = 1.0 / scale_x
        room.polygon = affinity.scale(room.polygon, xfact=scale_x, yfact=scale_y, origin='centroid')

    elif move_type == 'vastu_hop':
        # Jump to a random valid location inside the plot
        bounds = req['plot'].bounds
        for _ in range(10):
            x = np.random.uniform(bounds[0], bounds[2])
            y = np.random.uniform(bounds[1], bounds[3])
            if req['plot'].contains(ShapelyPoint(x, y)):
                room.polygon = affinity.translate(
                    room.polygon,
                    xoff=(x - room.polygon.centroid.x),
                    yoff=(y - room.polygon.centroid.y)
                )
                break

    elif move_type == 'align':
        # Try to align with nearby room
        spatial_index = SpatialIndex(current)
        for other_idx in spatial_index.query_nearby(room.polygon, params.slide_step * 2):
            if other_idx == room_idx:
                continue
            other = current[other_idx]
            p1, p2 = closest_points_on_polygons(room.polygon, other.polygon)
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            dist = np.sqrt(dx*dx + dy*dy)
            if dist > 1e-8:
                step_dx = (dx / dist) * params.slide_step
                step_dy = (dy / dist) * params.slide_step
                room.polygon = affinity.translate(room.polygon, xoff=step_dx, yoff=step_dy)
            break

    # Snap to grid if enabled
    if params.grid_snap > 0:
        room.polygon = snap_to_grid(room.polygon, params.grid_snap)

    return new_state

def closest_points_on_polygons(poly1: Polygon, poly2: Polygon) -> Tuple[Point, Point]:
    """Find closest points between two polygons."""
    if poly1.intersects(poly2):
        return poly1.centroid, poly2.centroid
    
    min_dist = float('inf')
    closest_p1 = None
    closest_p2 = None
    
    # Check all vertex pairs
    for p1 in zip(*poly1.exterior.coords.xy):
        for p2 in zip(*poly2.exterior.coords.xy):
            dist = np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
            if dist < min_dist:
                min_dist = dist
                closest_p1 = ShapelyPoint(p1)
                closest_p2 = ShapelyPoint(p2)
                
    return closest_p1, closest_p2

def snap_to_grid(poly: Polygon, grid_size: float) -> ShapelyPolygon:
    """Snap polygon vertices to grid and return a shapely Polygon."""
    coords = list(poly.exterior.coords)
    snapped = []
    for x, y in coords:
        x_snapped = round(x / grid_size) * grid_size
        y_snapped = round(y / grid_size) * grid_size
        snapped.append((x_snapped, y_snapped))
    return ShapelyPolygon(snapped)

def deterministic_local_improve(state: List[RoomState], req: Dict,
                              phi: PhiGrid, params: SAParams) -> List[RoomState]:
    """Apply deterministic improvements (snap-to-grid, overlap removal)."""
    improved = [r.copy() for r in state]
    boundary = req['plot']
    spatial_index = SpatialIndex(improved)
    
    # Attempt to resolve overlaps
    for i, room in enumerate(improved):
        overlaps = spatial_index.query_overlaps(room.polygon)
        if overlaps:
            centroid = room.polygon.centroid
            repulsion = np.zeros(2)
            
            # Compute repulsion vectors from overlapping rooms
            for j in overlaps:
                if j != i:
                    other = improved[j]
                    other_centroid = other.polygon.centroid
                    
                    # Vector from other room to this room
                    dx = centroid.x - other_centroid.x
                    dy = centroid.y - other_centroid.y
                    dist = np.sqrt(dx*dx + dy*dy)
                    
                    if dist > 0:
                        # Normalize and scale by overlap area
                        overlap_area = room.polygon.intersection(other.polygon).area
                        scale = min(overlap_area, params.slide_step)
                        repulsion[0] += (dx/dist) * scale
                        repulsion[1] += (dy/dist) * scale
            
            # Apply repulsion movement
            if np.any(repulsion):
                room.polygon = affinity.translate(room.polygon, xoff=repulsion[0], yoff=repulsion[1])
    
    # Snap to grid
    if params.grid_snap > 0:
        for room in improved:
            room.polygon = snap_to_grid(room.polygon, params.grid_snap)
    
    # Ensure rooms stay in boundary
    for room in improved:
        if not boundary.contains(room.polygon):
            # Project back into boundary
            centroid = room.polygon.centroid
            boundary_centroid = boundary.centroid

            # Vector from boundary center to room
            dx = centroid.x - boundary_centroid.x
            dy = centroid.y - boundary_centroid.y

            # Scale down until contained
            scale = 0.9
            while not boundary.contains(room.polygon) and scale > 0.1:
                room.polygon = affinity.translate(
                    room.polygon,
                    xoff=-dx * (1-scale),
                    yoff=-dy * (1-scale)
                )
                scale *= 0.9
    
    return improved

def run_sa(initial_state: SolverState, req: Dict, phi: PhiGrid,
           params: Optional[SAParams] = None) -> SolverState:
    """Run simulated annealing to improve layout.
    
    Args:
        initial_state: Starting layout (e.g., from graph solver)
        req: Solver request with rooms, plot, etc.
        phi: Vastu potential field
        params: Optional SA parameters
        
    Returns:
        Improved SolverState
    """
    params = params or SAParams()
    
    # Initialize state
    current = [r.copy() for r in initial_state.rooms]
    current_energy = compute_energy(current, req, phi, params)
    
    best = current.copy()
    best_energy = current_energy
    
    temperature = params.T0
    iteration = 0
    stall_count = 0
    
    logger.info(f"Starting SA optimization with initial energy: {current_energy:.2f}")
    
    while iteration < params.max_iters and stall_count < params.stall_patience:
        # Periodic local improvement
        if iteration % params.local_repair_interval == 0:
            current = deterministic_local_improve(current, req, phi, params)
            current_energy = compute_energy(current, req, phi, params)
            
            if current_energy < best_energy:
                best = [r.copy() for r in current]
                best_energy = current_energy
                stall_count = 0
                logger.info(f"New best energy after local improve: {best_energy:.2f}")
        
        # Generate candidate state
        candidate = propose_move(current, req, params)
        candidate_energy = compute_energy(candidate, req, phi, params)
        
        # Metropolis acceptance criterion
        delta_e = candidate_energy - current_energy
        if delta_e < 0 or np.random.random() < np.exp(-delta_e / temperature):
            current = candidate
            current_energy = candidate_energy
            
            # Update best solution
            if current_energy < best_energy:
                best = [r.copy() for r in current]
                best_energy = current_energy
                stall_count = 0
                logger.info(f"New best energy: {best_energy:.2f}")
            else:
                stall_count += 1
        else:
            stall_count += 1
            
        # Cool system
        if iteration % params.cooling_step == 0:
            temperature *= params.alpha
            
        iteration += 1
        
        if iteration % 100 == 0:
            logger.debug(f"Iteration {iteration}: T={temperature:.3f}, "
                      f"E={current_energy:.2f}, Best={best_energy:.2f}")
    
    logger.info(f"SA optimization completed after {iteration} iterations")
    logger.info(f"Final energy: {best_energy:.2f}")
    
    # Return best solution found
    return SolverState(rooms=best)