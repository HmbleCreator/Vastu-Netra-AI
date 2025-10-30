"""
Script to run benchmarks and generate comparison reports.
"""
import argparse
import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from typing import List
from .runner import BenchmarkRunner, BenchmarkResult
from .test_cases import BENCHMARK_CASES
from ..impl.sa_solver_impl import SAParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def plot_results(results: List[BenchmarkResult], output_dir: Path):
    """Generate visualization plots of benchmark results."""
    if not results:
        logger.warning("No results to plot!")
        return
        
    # Convert results to DataFrame
    df = pd.DataFrame([
        {
            'case': r.case_name,
            'solver': r.solver_name,
            'runtime': r.runtime_seconds,
            'energy': r.final_energy,
            'overlap': r.overlap_area,
            'vastu_score': r.vastu_score,
            'adjacency_score': r.adjacency_score,
            'boundary_violation': r.boundary_violation
        }
        for r in results
    ])
    
    # Create plots directory
    plots_dir = output_dir / 'plots'
    plots_dir.mkdir(exist_ok=True)
    
    # Runtime comparison
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='case', y='runtime', hue='solver')
    plt.title('Solver Runtime Comparison')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(plots_dir / 'runtime_comparison.png')
    plt.close()
    
    # Energy convergence
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='case', y='energy', hue='solver')
    plt.title('Final Energy Comparison')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(plots_dir / 'energy_comparison.png')
    plt.close()
    
    # Quality metrics
    fig, axes = plt.subplots(2, 2, figsize=(15, 15))
    fig.suptitle('Quality Metrics Comparison')
    
    sns.boxplot(data=df, x='case', y='overlap', hue='solver', ax=axes[0,0])
    axes[0,0].set_title('Room Overlap')
    axes[0,0].tick_params(labelrotation=45)
    
    sns.boxplot(data=df, x='case', y='vastu_score', hue='solver', ax=axes[0,1])
    axes[0,1].set_title('Vastu Score')
    axes[0,1].tick_params(labelrotation=45)
    
    sns.boxplot(data=df, x='case', y='adjacency_score', hue='solver', ax=axes[1,0])
    axes[1,0].set_title('Adjacency Score')
    axes[1,0].tick_params(labelrotation=45)
    
    sns.boxplot(data=df, x='case', y='boundary_violation', hue='solver', ax=axes[1,1])
    axes[1,1].set_title('Boundary Violation')
    axes[1,1].tick_params(labelrotation=45)
    
    plt.tight_layout()
    plt.savefig(plots_dir / 'quality_metrics.png')
    plt.close()
    
    # Save raw data
    df.to_csv(output_dir / 'benchmark_results.csv', index=False)
    
    # Generate summary stats
    summary = df.groupby(['case', 'solver']).agg({
        'runtime': ['mean', 'std'],
        'energy': ['mean', 'std'],
        'overlap': 'mean',
        'vastu_score': 'mean',
        'adjacency_score': 'mean',
        'boundary_violation': 'mean'
    }).round(3)
    
    summary.to_csv(output_dir / 'summary_stats.csv')
    
def main():
    parser = argparse.ArgumentParser(description='Run Vastu solver benchmarks')
    parser.add_argument('--output', type=str, default='benchmark_results',
                      help='Output directory for results')
    parser.add_argument('--runs', type=int, default=5,
                      help='Number of runs per case')
    parser.add_argument('--timeout', type=int, default=300,
                      help='Timeout in seconds per solver run')
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Additional solver configurations for testing
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
            'name': 'graph_sa_aggressive',
            'use_sa': True,
            'sa_params': SAParams(
                T0=2.0,
                alpha=0.99,
                max_iters=5000,
                stall_patience=500,
                lambda_vastu=2.0,
                lambda_adjacency=1.5,
                lambda_circulation=1.0
            )
        },
        {
            'name': 'graph_sa_conservative',
            'use_sa': True,
            'sa_params': SAParams(
                T0=0.5,
                alpha=0.95,
                max_iters=2000,
                stall_patience=200,
                lambda_vastu=1.0,
                lambda_adjacency=0.5,
                lambda_circulation=0.8
            )
        }
    ]
    
    # Run benchmarks
    runner = BenchmarkRunner()
    results = runner.run_benchmark(
        solver_configs=solver_configs,
        runs_per_case=args.runs,
        timeout_seconds=args.timeout
    )
    
    # Generate plots and save results
    plot_results(results, output_dir)
    
    logger.info(f"Benchmark results saved to {output_dir}")

if __name__ == '__main__':
    main()