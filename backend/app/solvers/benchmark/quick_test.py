"""
Quick test of graph solver with rectangular case.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from shapely.geometry import box
from backend.app.solvers.impl.graph_solver_impl import GraphSolver, GraphSolverParams
from backend.app.solvers.benchmark.test_cases import create_rectangular_case

def main():
    # Create test case
    case = create_rectangular_case()
    
    # Construct room polygons from room requirements (simple rectangles)
    room_polygons = []
    for r in case.rooms:
        w = r.get('min_dim', 3)
        area = r.get('area', w * w)
        h = max(0.5, area / w)
        # create box centered at origin
        poly = box(-w/2, -h/2, w/2, h/2)
        room_polygons.append(poly)

    # Initialize solver
    solver = GraphSolver(
        room_polygons=room_polygons,
        boundary_polygon=case.plot,
        adjacency_graph=case.adjacency,
        params=GraphSolverParams()
    )
    
    # Run solver
    print("Running solver...")
    result = solver.solve()
    
    # Print metrics
    print("\nResults:")
    print(f"Final energy: {result.metrics['final_energy']:.2f}")
    print(f"Iterations: {result.iterations}")
    print(f"Converged: {result.converged}")
    
    # Check room overlaps
    total_overlap = 0.0
    for i, room in enumerate(result.rooms):
        for j, other in enumerate(result.rooms[i+1:], i+1):
            if room.polygon.intersects(other.polygon):
                overlap = room.polygon.intersection(other.polygon).area
                total_overlap += overlap
                print(f"Room {i} and {j} overlap by {overlap:.2f} sq m")
    print(f"\nTotal overlap area: {total_overlap:.2f} sq m")

if __name__ == "__main__":
    main()