"""
Benchmark harness for Vastu layout solvers.
"""
import time
from pathlib import Path
import json
import argparse
from typing import List, Dict, Tuple
import numpy as np
from dataclasses import dataclass

from ..solvers.impl.phi_grid import PhiGrid, Point, Polygon, PhiParams
from ..solvers.impl.graph_solver_impl import run_graph_solver, GraphSolverParams
from ..solvers.impl.sa_solver_impl import run_sa, SAParams
from ..solvers.graph_solver import solve_layout as solve_graph_baseline
from ..solvers.constraint_solver import solve_layout as solve_sa_baseline

@dataclass
class BenchmarkFixture:
    name: str
    plot_polygon: List[List[float]]  # [[x,y], ...] CCW vertices
    plot_width: float
    plot_length: float
    rooms: List[Dict]  # [{id, type, target_area, ...}, ...]
    
class Metrics:
    def __init__(self):
        self.times = {}  # stage -> seconds
        self.scores = {}  # stage -> score
        self.overlaps = {}  # stage -> total_overlap_area
        self.violations = {}  # stage -> num_violations
        self.energies = []  # list of (iter, energy) tuples
    
    def to_dict(self) -> Dict:
        return {
            "times": self.times,
            "scores": self.scores,
            "overlaps": self.overlaps,
            "violations": self.violations,
            "energy_history": self.energies
        }

def load_fixtures() -> List[BenchmarkFixture]:
    """Load benchmark test cases."""
    fixtures = []
    
    # Rectangular 10x12m control case
    fixtures.append(BenchmarkFixture(
        name="rectangular_control",
        plot_polygon=[[0,0], [10,0], [10,12], [0,12]],
        plot_width=10.0,
        plot_length=12.0,
        rooms=[
            {"id": "living", "type": "living", "target_area": 20.0},
            {"id": "kitchen", "type": "kitchen", "target_area": 12.0},
            {"id": "master", "type": "master_bedroom", "target_area": 16.0},
            {"id": "bed2", "type": "bedroom", "target_area": 12.0},
            {"id": "bath", "type": "bathroom", "target_area": 6.0},
        ]
    ))
    
    # Triangular case
    fixtures.append(BenchmarkFixture(
        name="triangular",
        plot_polygon=[[0,0], [8,0], [0,6]],  # right triangle
        plot_width=8.0,
        plot_length=6.0,
        rooms=[
            {"id": "living", "type": "living", "target_area": 12.0},
            {"id": "kitchen", "type": "kitchen", "target_area": 9.0},
            {"id": "master", "type": "master_bedroom", "target_area": 12.0},
        ]
    ))
    
    # L-shaped case
    fixtures.append(BenchmarkFixture(
        name="l_shaped",
        plot_polygon=[[0,0], [12,0], [12,6], [6,6], [6,12], [0,12]],
        plot_width=12.0,
        plot_length=12.0,
        rooms=[
            {"id": "living", "type": "living", "target_area": 20.0},
            {"id": "kitchen", "type": "kitchen", "target_area": 12.0},
            {"id": "dining", "type": "dining", "target_area": 12.0},
            {"id": "master", "type": "master_bedroom", "target_area": 16.0},
            {"id": "bed2", "type": "bedroom", "target_area": 12.0},
            {"id": "bath1", "type": "bathroom", "target_area": 6.0},
            {"id": "bath2", "type": "bathroom", "target_area": 4.0},
        ]
    ))
    
    return fixtures

def prepare_solver_request(fixture: BenchmarkFixture) -> Dict:
    """Convert fixture to solver request format."""
    return {
        "rooms": fixture.rooms,
        "plot_polygon": fixture.plot_polygon,
        "plot_width": fixture.plot_width,
        "plot_length": fixture.plot_length,
        "plot_shape": "irregular",  # let solver handle via polygon
        "optimization_level": 2
    }

def run_benchmark(fixture: BenchmarkFixture, pipeline: str = "graph_sa",
                 params: Dict = None) -> Metrics:
    """Run solvers on fixture and collect metrics.
    
    Args:
        fixture: Test case
        pipeline: Solver sequence ("graph", "sa", "graph_sa")
        params: Optional parameter overrides
        
    Returns:
        Collected metrics
    """
    metrics = Metrics()
    req = prepare_solver_request(fixture)
    
    # Initialize Vastu potential field
    room_types = set(r["type"] for r in fixture.rooms)
    phi = PhiGrid(
        plot_polygon=Polygon([Point(x,y) for x,y in fixture.plot_polygon]),
        room_types=list(room_types),
        params=PhiParams(resolution=0.05)  # 5cm grid
    )
    
    if pipeline in ("graph", "graph_sa"):
        # Run graph solver
        t0 = time.time()
        graph_result = run_graph_solver(req, phi)
        metrics.times["graph"] = time.time() - t0
        metrics.scores["graph"] = compute_score(graph_result)
        metrics.overlaps["graph"] = compute_total_overlap(graph_result)
        metrics.violations["graph"] = count_violations(graph_result)
        
        if pipeline == "graph_sa":
            # Run SA with graph result as seed
            t0 = time.time()
            sa_result = run_sa(graph_result, req, phi)
            metrics.times["sa"] = time.time() - t0
            metrics.scores["sa"] = compute_score(sa_result)
            metrics.overlaps["sa"] = compute_total_overlap(sa_result)
            metrics.violations["sa"] = count_violations(sa_result)
            metrics.energies = sa_result.metrics.get("energy_history", [])
    
    elif pipeline == "sa":
        # Run SA from random start
        t0 = time.time()
        sa_result = run_sa(None, req, phi)  # None -> random init
        metrics.times["sa"] = time.time() - t0
        metrics.scores["sa"] = compute_score(sa_result)
        metrics.overlaps["sa"] = compute_total_overlap(sa_result)
        metrics.violations["sa"] = count_violations(sa_result)
        metrics.energies = sa_result.metrics.get("energy_history", [])
    
    return metrics

def run_baseline(fixture: BenchmarkFixture) -> Metrics:
    """Run existing solver implementations for comparison."""
    metrics = Metrics()
    req = prepare_solver_request(fixture)
    
    # Run existing graph solver
    t0 = time.time()
    graph_result = solve_graph_baseline(req)
    metrics.times["graph_baseline"] = time.time() - t0
    metrics.scores["graph_baseline"] = graph_result.get("score", 0)
    
    # Run existing SA solver
    t0 = time.time()
    sa_result = solve_sa_baseline(req)
    metrics.times["sa_baseline"] = time.time() - t0
    metrics.scores["sa_baseline"] = sa_result.get("score", 0)
    
    return metrics

def main():
    parser = argparse.ArgumentParser(description="Vastu solver benchmark tool")
    parser.add_argument("--fixture", choices=["all", "rectangular", "triangular", "l_shaped"],
                      default="all", help="Benchmark fixture to run")
    parser.add_argument("--pipeline", choices=["graph", "sa", "graph_sa"],
                      default="graph_sa", help="Solver pipeline to test")
    parser.add_argument("--compare-baseline", action="store_true",
                      help="Also run existing solver implementations")
    parser.add_argument("--output", type=str, default="benchmark_results.json",
                      help="Output file for results")
    args = parser.parse_args()
    
    fixtures = load_fixtures()
    if args.fixture != "all":
        fixtures = [f for f in fixtures if f.name == args.fixture]
    
    results = {}
    for fixture in fixtures:
        print(f"Running benchmark: {fixture.name}")
        metrics = run_benchmark(fixture, args.pipeline)
        if args.compare_baseline:
            baseline = run_baseline(fixture)
            # Merge metrics
            metrics.times.update(baseline.times)
            metrics.scores.update(baseline.scores)
        results[fixture.name] = metrics.to_dict()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {args.output}")

if __name__ == "__main__":
    main()