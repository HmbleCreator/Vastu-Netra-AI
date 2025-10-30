"""Run graph-only benchmarks across parameter variations and save CSV + plots.
This script avoids SA and PhiGrid to be compatible with the current GraphSolver implementation.
"""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo_root))

import time
import logging
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from backend.app.solvers.benchmark.test_cases import BENCHMARK_CASES
from backend.app.solvers.impl.graph_solver_impl import GraphSolver, GraphSolverParams
from shapely.geometry import box

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parameter variations
param_sets = [
    GraphSolverParams(),
    GraphSolverParams(alpha_r=1.2, repulsion_radius=6.0),
    GraphSolverParams(alpha_a=1.0, alpha_b=2.5),
    GraphSolverParams(mu=0.7, dt=0.2),
    GraphSolverParams(repulsion_exponent=2.0, alpha_r=0.6),
]

results = []

for case in BENCHMARK_CASES:
    logger.info(f"Running case: {case.name}")
    # Build room polygons from specs (same as original runner)
    base_polys = [box(0, 0, r['min_dim'], r['area']/r['min_dim']) for r in case.rooms]

    for i, params in enumerate(param_sets):
        logger.info(f"  Params set {i}")
        try:
            solver = GraphSolver(base_polys, case.plot, case.adjacency, params=params)
            start = time.time()
            state = solver.solve(max_iterations=800)
            runtime = time.time() - start

            # Compute overlaps
            overlap = 0.0
            for a_idx, a in enumerate(state.rooms):
                for b in state.rooms[a_idx+1:]:
                    if a.polygon.intersects(b.polygon):
                        overlap += a.polygon.intersection(b.polygon).area

            # adjacency score: fraction of required adjacencies that touch
            total_adj = sum(len(v) for v in case.adjacency.values())
            satisfied = 0
            for u, nbrs in case.adjacency.items():
                for v in nbrs:
                    if state.rooms[u].polygon.touches(state.rooms[v].polygon):
                        satisfied += 1
            adj_score = satisfied / total_adj if total_adj>0 else 1.0

            results.append({
                'case_name': case.name,
                'solver_name': 'graph_only',
                'param_set': i,
                'runtime_seconds': runtime,
                'final_energy': state.metrics.get('final_energy', float('nan')),
                'overlap_area': overlap,
                'adjacency_score': adj_score,
                'iterations': state.iterations,
                'converged': state.converged
            })
        except Exception as e:
            logger.error(f"Error running case {case.name} params {i}: {e}")

# Save results
out_dir = repo_root / 'benchmarks_output_graph_only'
out_dir.mkdir(parents=True, exist_ok=True)
df = pd.DataFrame(results)
csv_path = out_dir / 'graph_only_benchmark_results.csv'
df.to_csv(csv_path, index=False)
logger.info(f"Wrote CSV to {csv_path}")

# Plots
sns.set(style='whitegrid')
if not df.empty:
    plt.figure(figsize=(10,6))
    sns.boxplot(x='case_name', y='runtime_seconds', hue='param_set', data=df)
    plt.title('Graph-only runtime by case & param set')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir / 'graph_runtime.png')
    plt.close()

    plt.figure(figsize=(10,6))
    sns.boxplot(x='case_name', y='final_energy', hue='param_set', data=df)
    plt.title('Graph-only final energy by case & param set')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir / 'graph_energy.png')
    plt.close()

    plt.figure(figsize=(10,6))
    sns.boxplot(x='case_name', y='overlap_area', hue='param_set', data=df)
    plt.title('Graph-only overlap area by case & param set')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir / 'graph_overlap.png')
    plt.close()

logger.info('Graph-only benchmark run complete')
print(f"Outputs written to: {out_dir}")
