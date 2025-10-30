"""
Tests for Vastu layout solver implementations.
"""
import pytest
import numpy as np
from pathlib import Path
from ..solvers.impl.phi_grid import PhiGrid, Point, Polygon, PhiParams
from ..solvers.impl.graph_solver_impl import run_graph_solver, GraphSolverParams
from ..solvers.impl.sa_solver_impl import run_sa, SAParams
from ..solvers.metrics import compute_score, compute_total_overlap, count_violations

def test_phi_grid_basic():
    """Test basic PhiGrid initialization and sampling."""
    # Simple rectangular plot
    plot = Polygon([
        Point(0, 0),
        Point(10, 0),
        Point(10, 8),
        Point(0, 8)
    ])
    room_types = ["living", "kitchen", "bedroom"]
    
    phi = PhiGrid(plot, room_types, PhiParams(resolution=0.1))  # 10cm grid
    
    # Sample center point
    val = phi.sample_point(5.0, 4.0, "kitchen")
    assert isinstance(val, float)
    
    # Check SE preference for kitchen
    se_val = phi.sample_point(7.5, 2.0, "kitchen")  # SE corner
    nw_val = phi.sample_point(2.5, 6.0, "kitchen")  # NW corner
    assert se_val > nw_val, "Kitchen should prefer SE"
    
    # Gradient should point toward preferred direction
    gx, gy = phi.gradient(5.0, 4.0, "kitchen")
    assert isinstance(gx, float) and isinstance(gy, float)
    
def test_graph_solver_smoke():
    """Basic smoke test for graph solver."""
    plot = Polygon([Point(0,0), Point(10,0), Point(10,12), Point(0,12)])
    phi = PhiGrid(plot, ["living", "kitchen", "bedroom"])
    
    req = {
        "rooms": [
            {"id": "living", "type": "living", "target_area": 20.0},
            {"id": "kitchen", "type": "kitchen", "target_area": 12.0},
            {"id": "bed1", "type": "bedroom", "target_area": 16.0}
        ],
        "plot_polygon": [[0,0], [10,0], [10,12], [0,12]],
        "plot_width": 10.0,
        "plot_length": 12.0
    }
    
    result = run_graph_solver(req, phi)
    
    assert len(result.rooms) == 3
    assert all(r.polygon is not None for r in result.rooms)
    assert compute_total_overlap({"rooms": result.rooms}) < 1.0  # m²
    
def test_sa_improvement():
    """Test that SA improves upon graph solver result."""
    plot = Polygon([Point(0,0), Point(10,0), Point(10,12), Point(0,12)])
    phi = PhiGrid(plot, ["living", "kitchen", "bedroom"])
    
    req = {
        "rooms": [
            {"id": "living", "type": "living", "target_area": 20.0},
            {"id": "kitchen", "type": "kitchen", "target_area": 12.0},
            {"id": "bed1", "type": "bedroom", "target_area": 16.0}
        ],
        "plot_polygon": [[0,0], [10,0], [10,12], [0,12]],
        "plot_width": 10.0,
        "plot_length": 12.0
    }
    
    # First run graph solver
    graph_result = run_graph_solver(req, phi)
    graph_score = compute_score({"rooms": graph_result.rooms})
    
    # Then improve with SA
    sa_result = run_sa(graph_result, req, phi)
    sa_score = compute_score({"rooms": sa_result.rooms})
    
    assert sa_score > graph_score
    assert compute_total_overlap({"rooms": sa_result.rooms}) < 0.1  # m²
    
def test_vastu_preferences():
    """Test that rooms are placed in vastu-preferred locations."""
    plot = Polygon([Point(0,0), Point(10,0), Point(10,10), Point(0,10)])
    phi = PhiGrid(plot, ["pooja", "kitchen", "bedroom"])
    
    req = {
        "rooms": [
            {"id": "pooja", "type": "pooja", "target_area": 9.0},
            {"id": "kitchen", "type": "kitchen", "target_area": 12.0}
        ],
        "plot_polygon": [[0,0], [10,0], [10,10], [0,10]],
        "plot_width": 10.0,
        "plot_length": 10.0
    }
    
    result = run_graph_solver(req, phi)
    sa_result = run_sa(result, req, phi)
    
    # Check pooja room in NE quadrant
    pooja = next(r for r in sa_result.rooms if r.id == "pooja")
    assert pooja.center.x > 5.0 and pooja.center.y > 5.0, "Pooja should be in NE"
    
    # Check kitchen in SE quadrant
    kitchen = next(r for r in sa_result.rooms if r.id == "kitchen")
    assert kitchen.center.x > 5.0 and kitchen.center.y < 5.0, "Kitchen should be in SE"
    
if __name__ == "__main__":
    pytest.main([__file__])