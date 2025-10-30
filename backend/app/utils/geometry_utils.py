"""
Geometry utility helpers for polygon operations used by solvers.

Provides:
- point_in_polygon(point, polygon)
- project_point_inside(point, polygon)
- calculate_polygon_centroid(polygon)
- calculate_polygon_inradius(polygon)
- polygon_to_safe_zones(polygon)

These functions are lightweight and have no external dependencies beyond numpy.
"""
from typing import List, Tuple, Dict
import numpy as np
import math


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """Return True if point is inside polygon using ray-casting algorithm."""
    if not polygon:
        return True
    x, y = point
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def calculate_polygon_centroid(polygon: List[List[float]]) -> Tuple[float, float]:
    """Compute centroid of a polygon using shoelace formula."""
    pts = np.array(polygon)
    n = len(pts)
    if n == 0:
        return (0.0, 0.0)
    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        j = (i + 1) % n
        cross = pts[i,0] * pts[j,1] - pts[j,0] * pts[i,1]
        area += cross
        cx += (pts[i,0] + pts[j,0]) * cross
        cy += (pts[i,1] + pts[j,1]) * cross
    area = area / 2.0
    if abs(area) < 1e-9:
        # degenerate polygon: average
        return (float(np.mean(pts[:,0])), float(np.mean(pts[:,1])))
    cx = cx / (6.0 * area)
    cy = cy / (6.0 * area)
    return (float(cx), float(cy))


def calculate_polygon_area(polygon: List[List[float]]) -> float:
    pts = np.array(polygon)
    n = len(pts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i,0] * pts[j,1] - pts[j,0] * pts[i,1]
    return abs(area) / 2.0


def calculate_polygon_inradius(polygon: List[List[float]]) -> float:
    """Approximate inradius (radius of inscribed circle) using area and semiperimeter (works for triangles reliably)."""
    area = calculate_polygon_area(polygon)
    # compute perimeter
    pts = polygon
    perim = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        perim += math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
    s = perim / 2.0
    if s <= 0:
        return 0.0
    return area / s


def _project_point_to_segment(pt: np.ndarray, a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, float]:
    v = b - a
    l2 = np.dot(v, v)
    if l2 == 0:
        return a, float(np.linalg.norm(pt - a))
    t = max(0.0, min(1.0, np.dot(pt - a, v) / l2))
    proj = a + t * v
    return proj, float(np.linalg.norm(pt - proj))


def project_point_inside(point: Tuple[float, float], polygon: List[List[float]]) -> Tuple[float, float]:
    """If point is outside polygon, project it to nearest point on polygon boundary."""
    if not polygon:
        return point
    if point_in_polygon(point, polygon):
        return point
    pt = np.array(point)
    min_dist = float('inf')
    best = pt
    n = len(polygon)
    for i in range(n):
        a = np.array(polygon[i])
        b = np.array(polygon[(i+1) % n])
        proj, d = _project_point_to_segment(pt, a, b)
        if d < min_dist:
            min_dist = d
            best = proj
    return (float(best[0]), float(best[1]))


def polygon_to_safe_zones(polygon: List[List[float]]) -> Dict:
    """Return centroid, area, inradius and a simple inset polygon for safe buildable zone."""
    centroid = calculate_polygon_centroid(polygon)
    area = calculate_polygon_area(polygon)
    inradius = calculate_polygon_inradius(polygon)
    # Safe inset distance: 70% of inradius or 10ft (converted to meters if needed) cap
    safe_inset = max(0.0, min(inradius * 0.7, 10.0))

    # Create inset polygon by moving each vertex toward centroid by safe_inset
    pts = np.array(polygon, dtype=float)
    c = np.array(centroid)
    inset_pts = []
    for p in pts:
        vec = p - c
        norm = np.linalg.norm(vec)
        if norm < 1e-6:
            inset = p
        else:
            inset = p - (vec / norm) * safe_inset
        inset_pts.append([float(inset[0]), float(inset[1])])

    return {
        "centroid": centroid,
        "area": area,
        "inradius": inradius,
        "safe_inset": safe_inset,
        "inset_polygon": inset_pts
    }
