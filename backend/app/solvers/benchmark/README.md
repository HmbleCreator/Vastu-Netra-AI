# Vastu AI Benchmark Suite

This directory contains the benchmark suite for evaluating the performance of different solver implementations and parameter configurations.

## Prerequisites

- Python 3.8+ 
- Required packages:
  - pandas
  - seaborn
  - matplotlib
  - shapely
  - rtree (optional, for enhanced spatial indexing)

Install dependencies using:
```bash
pip install pandas seaborn matplotlib shapely
pip install rtree  # Optional, for enhanced performance
```

## Running Benchmarks

### Quick Start
Use the provided batch script on Windows:
```bash
run_benchmarks.bat
```

### Manual Execution
1. Full benchmark suite (all solvers):
```bash
python full_run.py
```

2. Graph solver parameter variations only:
```bash
python run_graph_variations.py
```

## Output
Benchmarks generate the following outputs:

- `benchmarks_output/` directory:
  - `benchmark_results.csv`: Raw performance data
  - `runtime.png`: Runtime comparison plots
  - `energy.png`: Final energy level plots
  - `overlaps.png`: Room overlap metrics
  - `adjacency.png`: Room adjacency scores

- `benchmarks_output_graph_only/` directory (for graph solver variations):
  - Similar structure with focus on graph solver parameter impacts

## Test Cases
Benchmark cases are defined in `test_cases.py` and include various room configurations to test solver performance across different scenarios.

## Customization
- Modify parameter variations in script preambles
- Adjust logging level using `logging.basicConfig(level=logging.INFO)`
- See individual script docstrings for additional options