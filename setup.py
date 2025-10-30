from setuptools import setup, find_packages

setup(
    name="vastu-ai-architect",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "shapely",
        "matplotlib",
        "seaborn"
    ]
)