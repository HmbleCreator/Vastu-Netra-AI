"""
Benchmark harness for evaluating and comparing Vastu solver implementations.
Collects metrics on solution quality, runtime, and convergence.
"""
from typing import Dict, List, Optional, Tuple, Any
import time
import logging
from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon, box
from ..impl.graph_solver_impl import GraphSolver
from ..impl.sa_solver_impl import run_sa, SAParams
from ..impl.phi_grid import PhiGrid
from .test_cases import BenchmarkCase, BENCHMARK_CASES

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Results from a single solver run."""
    case_name: str
    solver_name: str
    runtime_seconds: float
    final_energy: float
    room_areas: Dict[str, float]
    overlap_area: float
    vastu_score: float
    adjacency_score: float
    boundary_violation: float
    metrics: Dict[str, Any]

class BenchmarkRunner:
    def __init__(self, cases: List[BenchmarkCase] = None):
        """Initialize with optional specific test cases."""
        self.cases = cases or BENCHMARK_CASES
        
    def run_benchmark(self, 
                     solver_configs: List[Dict] = None,
                     runs_per_case: int = 3,
                     timeout_seconds: int = 300) -> List[BenchmarkResult]:
        """Run full benchmark suite.
        
        Args:
            solver_configs: List of solver configurations to test
            runs_per_case: Number of runs per case (for statistical significance)
            timeout_seconds: Maximum runtime per solver attempt
        
        Returns:
            List of BenchmarkResults for all runs
        """
        results = []
        
        # Default solver configs if none provided
        if not solver_configs:
            solver_configs = [
                {
                    'name': 'graph_only',
                    'use_sa': False,
                    'sa_params': None
                },
                {
                    'name': 'graph_sa_default',
                    'use_sa': True,
                    'sa_params': SAParams()
                },
                {
                    'name': 'graph_sa_tuned',
                    'use_sa': True,
                    'sa_params': SAParams(
                        T0=2.0,
                        alpha=0.98,
                        max_iters=5000,
                        lambda_vastu=1.5,
                        lambda_adjacency=1.0
                    )
                }
            ]
            
        # Run benchmarks
        for case in self.cases:
            logger.info(f"\nRunning benchmark case: {case.name}")
            
            for config in solver_configs:
                logger.info(f"Testing solver: {config['name']}")
                
                for run in range(runs_per_case):
                    try:
                        result = self._run_single_case(
                            case, config, timeout_seconds)
                        results.append(result)
                        
                    except Exception as e:
                        # Log full traceback to help diagnose failures during benchmarks
                        logger.exception(f"Error in {case.name} with {config['name']}")
                        continue
                        
        return results
    
    def _run_single_case(self,
                        case: BenchmarkCase,
                        solver_config: Dict,
                        timeout_seconds: int) -> BenchmarkResult:
        """Run single benchmark case with given solver config."""
        start_time = time.time()
        
        # Set up solvers
        room_types = [room['name'] for room in case.rooms]
        phi_grid = PhiGrid(case.plot, room_types)
        # Allow passing GraphSolver params via solver_config['graph_params']
        graph_params = solver_config.get('graph_params', None)
        graph_solver = GraphSolver(
            [box(0, 0, r['min_dim'], r['area']/r['min_dim']) 
             for r in case.rooms],
            case.plot,
            case.adjacency,
            params=graph_params
        )
        
        # Initial solution from graph solver
        solution = graph_solver.solve(max_iterations=1000)
        
        # Optional SA refinement
        metrics = {'graph_energy': graph_solver.best_energy}
        if solver_config['use_sa']:
            solution = run_sa(
                solution,
                case.get_solver_request(),
                phi_grid,
                solver_config['sa_params']
            )
            metrics['sa_final_temp'] = solver_config['sa_params'].min_temp
            
        runtime = time.time() - start_time
        
        # Compute quality metrics
        room_areas = {
            case.rooms[i]['name']: room.polygon.area
            for i, room in enumerate(solution.rooms)
        }
        
        overlap = self._compute_total_overlap(solution.rooms)
        vastu_score = self._compute_vastu_score(
            solution.rooms, case.rooms, case.vastu_directions, phi_grid)
        adj_score = self._compute_adjacency_score(
            solution.rooms, case.adjacency)
        boundary_violation = self._compute_boundary_violation(
            solution.rooms, case.plot)
            
        return BenchmarkResult(
            case_name=case.name,
            solver_name=solver_config['name'],
            runtime_seconds=runtime,
            final_energy=metrics.get('sa_final_energy', metrics['graph_energy']),
            room_areas=room_areas,
            overlap_area=overlap,
            vastu_score=vastu_score,
            adjacency_score=adj_score,
            boundary_violation=boundary_violation,
            metrics=metrics
        )
    
    def _compute_total_overlap(self, rooms: List[Any]) -> float:
        """Compute total overlap area between rooms."""
        total = 0.0
        for i, room1 in enumerate(rooms):
            for j, room2 in enumerate(rooms[i+1:], i+1):
                if room1.polygon.intersects(room2.polygon):
                    total += room1.polygon.intersection(room2.polygon).area
        return total
    
    def _compute_vastu_score(self,
                           rooms: List[Any],
                           room_specs: List[Dict],
                           vastu_dirs: Dict[str, List[str]],
                           phi_grid: PhiGrid) -> float:
        """Compute how well rooms satisfy Vastu directional preferences."""
        if not vastu_dirs:
            return 1.0
            
        total_score = 0.0
        for i, room in enumerate(rooms):
            name = room_specs[i]['name']
            if name in vastu_dirs:
                centroid = room.polygon.centroid
                phi_value = phi_grid.sample_phi(centroid.x, centroid.y)
                total_score += phi_value
                
        return total_score / len(rooms)
    
    def _compute_adjacency_score(self,
                               rooms: List[Any],
                               adjacency: Dict[int, List[int]]) -> float:
        """Compute fraction of required adjacencies that are satisfied."""
        satisfied = 0
        total = 0
        
        for i, adj_list in adjacency.items():
            total += len(adj_list)
            for j in adj_list:
                if rooms[i].polygon.touches(rooms[j].polygon):
                    satisfied += 1
                    
        return satisfied / total if total > 0 else 1.0
    
    def _compute_boundary_violation(self,
                                  rooms: List[Any],
                                  boundary: Polygon) -> float:
        """Compute total area of rooms outside boundary."""
        total = 0.0
        for room in rooms:
            if not boundary.contains(room.polygon):
                total += room.polygon.difference(boundary).area
        return total