from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field, validator
from .plot import Direction, RoomType

class RoomRequirement(BaseModel):
    """Single room requirement with Vastu preferences"""
    room_type: RoomType
    name: Optional[str] = None  # Custom name (e.g., "Kids Bedroom")
    preferred_direction: Optional[Direction] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    adjacent_to: Optional[List[RoomType]] = None
    vastu_importance: int = Field(1, ge=1, le=3, description="1=flexible, 2=preferred, 3=strict")

class VastuConstraint(BaseModel):
    """Single Vastu rule or constraint"""
    room_type: RoomType
    direction: Direction
    strength: int = Field(1, ge=1, le=3, description="1=preferred, 2=strong, 3=mandatory")
    reason: Optional[str] = None

class BHKExpansion(BaseModel):
    """Expands '3BHK' into actual room requirements"""
    bhk_count: int = Field(..., ge=1, le=6)
    include_pooja_room: bool = True
    include_study: bool = False
    bathrooms_per_bedroom: float = Field(0.75, ge=0.5, le=2.0)
    
    def expand(self) -> List[RoomRequirement]:
        """Expand BHK count into actual rooms needed"""
        rooms = []
        
        # Always included
        rooms.extend([
            RoomRequirement(
                room_type=RoomType.LIVING,
                min_area=250 if self.bhk_count >= 4 else 180,
                vastu_importance=2
            ),
            RoomRequirement(
                room_type=RoomType.KITCHEN,
                preferred_direction=Direction.SOUTHEAST,
                min_area=100,
                vastu_importance=3
            ),
            RoomRequirement(
                room_type=RoomType.DINING,
                min_area=120,
                adjacent_to=[RoomType.KITCHEN],
                vastu_importance=1
            )
        ])
        
        # Master bedroom
        rooms.append(RoomRequirement(
            room_type=RoomType.MASTER_BEDROOM,
            preferred_direction=Direction.SOUTHWEST,
            min_area=180,
            vastu_importance=2
        ))
        
        # Additional bedrooms
        for i in range(self.bhk_count - 1):
            rooms.append(RoomRequirement(
                room_type=RoomType.BEDROOM,
                name=f"Bedroom {i+2}",
                min_area=140,
                vastu_importance=1
            ))
        
        # Bathrooms
        bathroom_count = max(2, int(self.bhk_count * self.bathrooms_per_bedroom))
        for i in range(bathroom_count):
            rooms.append(RoomRequirement(
                room_type=RoomType.BATHROOM,
                name=f"Bathroom {i+1}",
                preferred_direction=Direction.NORTHWEST,
                min_area=40,
                vastu_importance=2
            ))
        
        # Optional rooms
        if self.include_pooja_room:
            rooms.append(RoomRequirement(
                room_type=RoomType.POOJA,
                preferred_direction=Direction.NORTHEAST,
                min_area=50,
                vastu_importance=3
            ))
            
        if self.include_study:
            rooms.append(RoomRequirement(
                room_type=RoomType.STUDY,
                preferred_direction=Direction.WEST,
                min_area=100,
                vastu_importance=1
            ))
        
        return rooms

class LayoutRequest(BaseModel):
    """Complete layout generation request after LLM parsing"""
    rooms: List[RoomRequirement]
    plot_specs: Dict  # Will be validated by PlotSpecs
    vastu_constraints: List[VastuConstraint] = []
    style_preferences: Optional[Dict[str, Union[str, float, bool]]] = None
    
    @validator('rooms')
    def validate_room_counts(cls, v):
        """Ensure we have minimum required rooms"""
        room_types = [r.room_type for r in v]
        
        # Must have at least one bedroom
        if not any(rt in room_types for rt in [RoomType.MASTER_BEDROOM, RoomType.BEDROOM]):
            raise ValueError("Layout must include at least one bedroom")
            
        # Must have kitchen
        if RoomType.KITCHEN not in room_types:
            raise ValueError("Layout must include a kitchen")
            
        return v