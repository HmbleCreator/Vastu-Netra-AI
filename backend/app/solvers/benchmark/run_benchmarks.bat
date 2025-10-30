@echo off
echo Running Vastu AI Benchmarks...

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or later.
    exit /b 1
)

:: Ensure we're in the correct directory
cd /d "%~dp0"

:: Install required packages
echo Installing dependencies...
python -m pip install -q pandas seaborn matplotlib shapely
if errorlevel 1 (
    echo Error installing dependencies. Please check your Python installation.
    exit /b 1
)

:: Optional rtree installation
python -m pip install -q rtree
if errorlevel 1 (
    echo Note: rtree installation failed. Continuing with grid-based spatial indexing...
)

echo Running full benchmark suite...
python full_run.py
if errorlevel 1 (
    echo Error running benchmarks.
    exit /b 1
)

echo Benchmark complete! Results available in:
echo - benchmarks_output/benchmark_results.csv
echo - benchmarks_output/*.png

pause