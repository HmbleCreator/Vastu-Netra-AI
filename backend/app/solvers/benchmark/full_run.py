"""Launcher to run full benchmark suite and save CSV + plots.
This script uses sys.path hacking to allow running from repository root or directly.
"""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo_root))

import logging
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from backend.app.solvers.benchmark.runner import BenchmarkRunner
from backend.app.solvers.benchmark.test_cases import BENCHMARK_CASES
from backend.app.solvers.impl.graph_solver_impl import GraphSolverParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parameter variations to test
param_sets = [
    GraphSolverParams(),
    GraphSolverParams(alpha_r=1.2, repulsion_radius=6.0),
    GraphSolverParams(alpha_a=1.0, alpha_b=2.5),
    GraphSolverParams(mu=0.7, dt=0.2),
    GraphSolverParams(repulsion_exponent=2.0, alpha_r=0.6),
]

# Build solver_configs matching BenchmarkRunner expected fields
solver_configs = []
for idx, p in enumerate(param_sets):
    # graph_only config
    solver_configs.append({
        'name': f'graph_only_variation_{idx}',
        'use_sa': False,
        'sa_params': None,
        'graph_params': p
    })
    # optionally include SA refinement variations (use default SAParams)
    from backend.app.solvers.impl.sa_solver_impl import SAParams
    solver_configs.append({
        'name': f'graph_sa_variation_{idx}',
        'use_sa': True,
        'sa_params': SAParams(),
        'graph_params': p
    })


def plot_results(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    # Ensure columns consistent
    if 'runtime_seconds' in df.columns:
        runtime_col = 'runtime_seconds'
    else:
        runtime_col = 'runtime'

    sns.set(style='whitegrid')
    plt.figure(figsize=(10,6))
    sns.boxplot(x='case_name', y=runtime_col, hue='solver_name', data=df)
    plt.title('Solver Runtime by Test Case')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir / 'benchmark_runtime.png')
    plt.close()

    plt.figure(figsize=(10,6))
    sns.boxplot(x='case_name', y='final_energy', hue='solver_name', data=df)
    plt.title('Final Energy by Test Case')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir / 'benchmark_energy.png')
    plt.close()

    plt.figure(figsize=(10,6))
    if 'room_overlaps' in df.columns:
        overlap_col = 'room_overlaps'
    elif 'overlap_area' in df.columns:
        overlap_col = 'overlap_area'
    else:
        overlap_col = 'overlap_area'
    sns.boxplot(x='case_name', y=overlap_col, hue='solver_name', data=df)
    plt.title('Room Overlaps by Test Case')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_dir / 'benchmark_overlaps.png')
    plt.close()

    plt.figure(figsize=(10,6))
    if 'adjacency_score' in df.columns:
        adj_col = 'adjacency_score'
        sns.boxplot(x='case_name', y=adj_col, hue='solver_name', data=df)
        plt.title('Adjacency Score by Test Case')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(out_dir / 'benchmark_adjacency.png')
        plt.close()


def main():
    logger.info('Starting full benchmark run')
    runner = BenchmarkRunner(cases=BENCHMARK_CASES)
    # run_benchmark in existing runner expects solver_configs list
    results = runner.run_benchmark(solver_configs=solver_configs, runs_per_case=3)

    # results is a list of BenchmarkResult objects
    df = pd.DataFrame([r.__dict__ for r in results])
    out_dir = repo_root / 'benchmarks_output'
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / 'benchmark_results.csv'
    df.to_csv(csv_path, index=False)
    logger.info(f'Wrote results to {csv_path}')

    plot_results(df, out_dir)
    logger.info(f'Plots written to {out_dir}')

if __name__ == '__main__':
    main()
