"""
Vastu potential field computation and sampling.
Provides grid-based Φ_k(x,y) computation and efficient sampling/gradient methods.
"""
from typing import List, Dict, Tuple, Optional, Union
import numpy as np
from dataclasses import dataclass
from enum import Enum
import logging
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box as shapely_box
from shapely.affinity import rotate, translate

logger = logging.getLogger(__name__)

@dataclass
class Point:
    x: float
    y: float
    
    def to_shapely(self) -> ShapelyPoint:
        return ShapelyPoint(self.x, self.y)

@dataclass
class Polygon:
    vertices: List[Point]  # CCW order
    
    def to_shapely(self) -> ShapelyPolygon:
        return ShapelyPolygon([(v.x, v.y) for v in self.vertices])
    
    @classmethod
    def from_shapely(cls, poly: ShapelyPolygon) -> 'Polygon':
        return cls(vertices=[Point(x, y) for x, y in poly.exterior.coords[:-1]])

@dataclass
class PhiParams:
    resolution: float = 0.05  # meters
    gaussian_sigma: float = 2.0  # spread parameter
    cache_enabled: bool = True
    interpolation: str = 'bilinear'  # or 'nearest'
    vastu_weights: Dict[str, float] = None  # room_type -> weight

# Vastu directional preferences (normalized to plot dimensions)
VASTU_ZONES = {
    'pooja_room': {'preferred': [(0.75, 0.75)], 'weight': 1.0},  # NE
    'kitchen': {'preferred': [(0.75, 0.25)], 'weight': 0.9},     # SE
    'master_bedroom': {'preferred': [(0.25, 0.25)], 'weight': 0.8},  # SW
    'bedroom': {'preferred': [(0.25, 0.5)], 'weight': 0.6},      # W
    'living': {'preferred': [(0.5, 0.75)], 'weight': 0.7},       # N/NE
    'dining': {'preferred': [(0.5, 0.5)], 'weight': 0.5},        # Center-E
    'bathroom': {'preferred': [(0.25, 0.75)], 'weight': 0.7},    # NW
}

class PhiGrid:
    """Efficient grid-based Vastu potential field computation and sampling."""
    
    def __init__(self, plot_polygon: Polygon, room_types: List[str], 
                 params: Optional[PhiParams] = None):
        """Initialize potential field grids for each room type."""
        # Accept either our internal Polygon or a shapely.geometry.Polygon
        if isinstance(plot_polygon, ShapelyPolygon):
            self.plot = Polygon.from_shapely(plot_polygon)
        else:
            self.plot = plot_polygon
        self.plot_shapely = self.plot.to_shapely()
        self.room_types = room_types
        self.params = params or PhiParams()
        
        # Compute bounding box and set up grid
        self.bounds = self.plot_shapely.bounds
        self.xmin, self.ymin, self.xmax, self.ymax = self.bounds
        self.width = self.xmax - self.xmin
        self.height = self.ymax - self.ymin
        
        # Grid dimensions
        self.nx = int(np.ceil(self.width / self.params.resolution))
        self.ny = int(np.ceil(self.height / self.params.resolution))
        
        # Initialize grids for each room type
        self._init_grids()
        
        # Cache
        self._cache = {} if self.params.cache_enabled else None
    
    def _init_grids(self):
        """Initialize phi grids for each room type."""
        self.grids = {}
        
        # Create mask grid (1 inside plot, 0 outside)
        x = np.linspace(self.xmin, self.xmax, self.nx)
        y = np.linspace(self.ymin, self.ymax, self.ny)
        self.X, self.Y = np.meshgrid(x, y)
        
        # Build mask using shapely contains
        points = np.column_stack((self.X.flatten(), self.Y.flatten()))
        mask = np.array([self.plot_shapely.contains(ShapelyPoint(px, py)) 
                        for px, py in points]).reshape(self.ny, self.nx)
        self.mask = mask
        
        # For each room type, compute potential field
        for room_type in self.room_types:
            grid = np.zeros((self.ny, self.nx))
            
            # Get vastu preferences
            vastu_info = VASTU_ZONES.get(room_type, {'preferred': [(0.5, 0.5)], 'weight': 0.5})
            centers = vastu_info['preferred']
            weight = vastu_info['weight']
            
            # For each preferred location
            for cx, cy in centers:
                # Map normalized (0-1) coords to actual dimensions
                center_x = self.xmin + cx * self.width
                center_y = self.ymin + cy * self.height
                
                # Compute Gaussian potential centered here
                sigma = self.params.gaussian_sigma
                grid += weight * np.exp(-((self.X - center_x)**2 + 
                                        (self.Y - center_y)**2) / (2 * sigma**2))
            
            # Apply mask and normalize
            grid *= mask
            if grid.max() > 0:
                grid /= grid.max()
            
            self.grids[room_type] = grid
    
    def _bilinear_interpolate(self, x: float, y: float, grid: np.ndarray) -> float:
        """Bilinear interpolation from grid."""
        # Map to grid coordinates
        gx = (x - self.xmin) / self.params.resolution
        gy = (y - self.ymin) / self.params.resolution
        
        # Grid indices
        i0 = int(np.floor(gx))
        j0 = int(np.floor(gy))
        i1 = i0 + 1
        j1 = j0 + 1
        
        # Clamp indices
        i0 = max(0, min(i0, self.nx-1))
        i1 = max(0, min(i1, self.nx-1))
        j0 = max(0, min(j0, self.ny-1))
        j1 = max(0, min(j1, self.ny-1))
        
        # Interpolation weights
        wx = gx - i0
        wy = gy - j0
        
        # Interpolate
        val = ((1-wx)*(1-wy)*grid[j0,i0] + 
               wx*(1-wy)*grid[j0,i1] + 
               (1-wx)*wy*grid[j1,i0] + 
               wx*wy*grid[j1,i1])
        
        return float(val)
    
    def sample_point(self, x: float, y: float, room_type: str) -> float:
        """Sample Φ_k at a single point (x,y)."""
        # Check cache
        if self._cache is not None:
            key = (x, y, room_type)
            if key in self._cache:
                return self._cache[key]
        
        # Check if point is inside plot
        if not self.plot_shapely.contains(ShapelyPoint(x, y)):
            val = 0.0
        else:
            grid = self.grids.get(room_type)
            if grid is None:
                val = 0.5  # default neutral value
            else:
                val = self._bilinear_interpolate(x, y, grid)
        
        # Cache and return
        if self._cache is not None:
            self._cache[key] = val
        return val

    def sample_phi(self, x: float, y: float) -> float:
        """Compatibility wrapper: return a single scalar potential at (x,y).

        When caller doesn't specify a room type, return the mean potential
        across available room type grids (or 0.0 if none).
        """
        if not self.room_types:
            return 0.0
        vals = [self.sample_point(x, y, rt) for rt in self.room_types]
        return float(np.mean(vals))
    
    def sample_polygon(self, poly: Polygon, room_type: str, 
                      sampling: str = 'center') -> float:
        """Approximate integral of Φ_k over polygon area."""
        # Accept either our Polygon wrapper or a shapely Polygon
        if isinstance(poly, ShapelyPolygon):
            shapely_poly = poly
        else:
            shapely_poly = poly.to_shapely()

        if sampling == 'center':
            # Fast approximation using center point
            centroid = shapely_poly.centroid
            return self.sample_point(centroid.x, centroid.y, room_type)
        else:
            # Grid sampling (more accurate but slower)
            bounds = shapely_poly.bounds
            xmin, ymin, xmax, ymax = bounds
            
            # Create sampling grid (3x3 or 4x4)
            nx = ny = 3 if sampling == 'coarse' else 4
            x = np.linspace(xmin, xmax, nx)
            y = np.linspace(ymin, ymax, ny)
            X, Y = np.meshgrid(x, y)
            
            # Sample points inside polygon
            total = 0.0
            count = 0
            for i in range(nx):
                for j in range(ny):
                    pt = ShapelyPoint(X[j,i], Y[j,i])
                    if shapely_poly.contains(pt):
                        total += self.sample_point(pt.x, pt.y, room_type)
                        count += 1
            
            return total / max(1, count)
    
    def gradient(self, x: float, y: float, room_type: str) -> Tuple[float, float]:
        """Compute gradient ∇Φ_k at point (x,y) using central differences."""
        eps = self.params.resolution * 0.1
        right = self.sample_point(x + eps, y, room_type)
        left = self.sample_point(x - eps, y, room_type)
        up = self.sample_point(x, y + eps, room_type)
        down = self.sample_point(x, y - eps, room_type)
        
        gx = (right - left) / (2 * eps)
        gy = (up - down) / (2 * eps)
        return (gx, gy)
    
    def argmax_nearby(self, room_type: str, bbox: Tuple[float, float, float, float],
                      radius: float) -> Point:
        """Find high-potential point for room_type within radius of bbox."""
        xmin, ymin, xmax, ymax = bbox
        
        # Sample grid points within bbox
        nx = ny = max(10, int(radius / self.params.resolution))
        x = np.linspace(xmin, xmax, nx)
        y = np.linspace(ymin, ymax, ny)
        X, Y = np.meshgrid(x, y)
        
        # Evaluate potential at all points
        values = np.zeros((ny, nx))
        for i in range(nx):
            for j in range(ny):
                values[j,i] = self.sample_point(X[j,i], Y[j,i], room_type)
        
        # Find maximum
        j, i = np.unravel_index(values.argmax(), values.shape)
        return Point(X[j,i], Y[j,i])
    
    def is_in_buildable(self, poly_or_point: Union[Polygon, Point]) -> bool:
        """Test if polygon/point lies within buildable region."""
        if isinstance(poly_or_point, Point):
            return self.plot_shapely.contains(poly_or_point.to_shapely())
        else:
            return self.plot_shapely.contains(poly_or_point.to_shapely())