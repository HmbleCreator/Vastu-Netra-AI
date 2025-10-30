from enum import Enum
from typing import List, Optional, Dict, Tuple, Union
from pydantic import BaseModel, Field, validator
import numpy as np

class PlotShape(str, Enum):
    """Available plot shapes with special handling for each"""
    RECTANGULAR = "rectangular"
    TRIANGULAR = "triangular"
    L_SHAPED = "l-shaped"
    IRREGULAR = "irregular"

class Direction(str, Enum):
    """Cardinal and intercardinal directions for Vastu"""
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"
    CENTER = "center"

class RoomType(str, Enum):
    """Standard room types with Vastu significance"""
    POOJA = "pooja_room"
    KITCHEN = "kitchen"
    MASTER_BEDROOM = "master_bedroom"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    LIVING = "living"
    DINING = "dining"
    ENTRANCE = "entrance"
    STUDY = "study"
    STORE = "store"

class TriangularPlot(BaseModel):
    """Special handling for triangular plots"""
    base: float = Field(..., gt=0, description="Base length in feet")
    height: float = Field(..., gt=0, description="Height in feet")
    hypotenuse_direction: Direction = Field(..., description="Direction the hypotenuse faces")
    right_angle_position: Optional[Direction] = Field(None, description="Position of right angle (inferred from hypotenuse)")
    
    @validator('right_angle_position', always=True)
    def infer_right_angle(cls, v, values):
        """Infer right angle position from hypotenuse direction"""
        if v is not None:
            return v
            
        hyp_dir = values.get('hypotenuse_direction')
        if not hyp_dir:
            return Direction.EAST  # Default
            
        # Right angle is opposite to hypotenuse
        right_angle_map = {
            Direction.WEST: Direction.EAST,
            Direction.EAST: Direction.WEST,
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.NORTHEAST: Direction.SOUTHWEST,
            Direction.SOUTHWEST: Direction.NORTHEAST,
            Direction.NORTHWEST: Direction.SOUTHEAST,
            Direction.SOUTHEAST: Direction.NORTHWEST,
        }
        return right_angle_map.get(hyp_dir, Direction.EAST)
    
    def calculate_vertices(self) -> List[Tuple[float, float]]:
        """Calculate vertices based on dimensions and orientation"""
        base, height = self.base, self.height
        
        # Default: Right angle at origin (0,0)
        vertices = [(0, 0), (base, 0), (0, height)]
        
        # Rotate based on right angle position
        if self.right_angle_position == Direction.WEST:
            vertices = [(base, 0), (base, height), (0, 0)]
        elif self.right_angle_position == Direction.NORTH:
            vertices = [(0, height), (base, height), (0, 0)]
        elif self.right_angle_position == Direction.SOUTH:
            vertices = [(0, 0), (base, 0), (base, height)]
            
        return vertices

class PlotSpecs(BaseModel):
    """Complete plot specifications with special handling for different shapes"""
    shape: PlotShape
    area: float = Field(..., gt=0, description="Total plot area in square feet")
    width: Optional[float] = Field(None, gt=0, description="Plot width in feet (for rectangular)")
    length: Optional[float] = Field(None, gt=0, description="Plot length in feet (for rectangular)")
    triangular_specs: Optional[TriangularPlot] = Field(None, description="Details for triangular plot")
    orientation: Direction = Field(..., description="Main plot orientation (which direction it faces)")
    
    @validator('triangular_specs')
    def validate_triangular(cls, v, values):
        """Ensure triangular specs are present for triangular plots"""
        if values.get('shape') == PlotShape.TRIANGULAR and v is None:
            raise ValueError("Triangular plot requires triangular_specs")
        return v
    
    @validator('width', 'length')
    def validate_rectangular(cls, v, values):
        """Ensure width/length are present for rectangular plots"""
        if values.get('shape') == PlotShape.RECTANGULAR and v is None:
            raise ValueError("Rectangular plot requires width and length")
        return v