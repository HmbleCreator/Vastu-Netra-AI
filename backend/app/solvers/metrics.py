"""
Helper functions for computing layout metrics and scores.
"""
from typing import List, Dict, Union
import numpy as np
from .impl.phi_grid import Point, Polygon

def compute_overlap_area(poly1: Polygon, poly2: Polygon) -> float:
    """Compute intersection area of two polygons."""
    # TODO: Implement polygon intersection
    # For now return 0 as placeholder
    return 0.0

def compute_total_overlap(state: Dict) -> float:
    """Compute total overlap area between all room pairs."""
    total = 0.0
    rooms = state.get("rooms", [])
    for i, r1 in enumerate(rooms):
        for j, r2 in enumerate(rooms[i+1:], i+1):
            total += compute_overlap_area(r1.get("polygon"), r2.get("polygon"))
    return total

def count_violations(state: Dict) -> int:
    """Count number of hard constraint violations."""
    # TODO: Check vastu rules, boundary containment, etc
    return 0

def compute_score(state: Dict) -> float:
    """Compute overall layout score (0-100)."""
    # Components (weights should sum to 1.0)
    w_overlap = 0.4
    w_vastu = 0.3
    w_adjacency = 0.2
    w_other = 0.1
    
    # Overlap penalty (0 if no overlap, decreases with overlap area)
    overlap_area = compute_total_overlap(state)
    overlap_score = 100.0 * np.exp(-overlap_area)
    
    # Vastu score (from solver's internal metrics)
    vastu_score = state.get("vastu_score", 50.0)
    
    # Adjacency score (from solver's internal metrics)
    adj_score = state.get("adjacency_score", 50.0)
    
    # Other metrics (boundary containment, etc)
    other_score = 100.0 - count_violations(state) * 10.0
    
    # Weighted sum
    total_score = (w_overlap * overlap_score + 
                  w_vastu * vastu_score +
                  w_adjacency * adj_score +
                  w_other * other_score)
    
    return max(0.0, min(100.0, total_score))