from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import math

router = APIRouter()

class Room(BaseModel):
    id: str
    name: str
    width: float
    height: float
    x: float
    y: float
    color: Optional[str] = None

class FloorPlanValidationRequest(BaseModel):
    rooms: List[Room]
    constraints: Optional[Dict[str, Any]] = None

class ValidationResponse(BaseModel):
    is_valid: bool
    issues: List[str] = []
    suggestions: List[str] = []
    vastu_score: Optional[float] = None
    entrance_compliance: Optional[float] = None
    room_placement_score: Optional[float] = None
    direction_alignment_score: Optional[float] = None

@router.post("/validate", response_model=ValidationResponse)
async def validate_floor_plan(request: FloorPlanValidationRequest):
    """
    Validate a floor plan against Vastu principles and design constraints
    """
    try:
        # Basic validation logic
        issues = []
        suggestions = []
        
        # Check for overlapping rooms
        for i, room1 in enumerate(request.rooms):
            for j, room2 in enumerate(request.rooms):
                if i != j:
                    # Check if rooms overlap
                    if (room1.x < room2.x + room2.width and
                        room1.x + room1.width > room2.x and
                        room1.y < room2.y + room2.height and
                        room1.y + room1.height > room2.y):
                        issues.append(f"Room '{room1.name}' overlaps with '{room2.name}'")

        # Boundary checks for polygon/circle plots if provided
        def point_in_polygon(point: List[float], polygon: List[List[float]]) -> bool:
            x, y = point
            inside = False
            if not polygon or len(polygon) < 3:
                return True
            p1x, p1y = polygon[0]
            n = len(polygon)
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

        constraints = request.constraints or {}
        plot_polygon = constraints.get("plot_polygon") if isinstance(constraints, dict) else None
        circle = constraints.get("circle") if isinstance(constraints, dict) else None

        if plot_polygon or circle:
            for r in request.rooms:
                corners = [
                    [r.x, r.y],
                    [r.x + r.width, r.y],
                    [r.x + r.width, r.y + r.height],
                    [r.x, r.y + r.height],
                ]
                for cx, cy in corners:
                    if plot_polygon:
                        if not point_in_polygon([cx, cy], plot_polygon):
                            issues.append(f"Room '{r.name}' extends outside polygon boundary")
                            break
                    elif circle and isinstance(circle, dict):
                        center = circle.get("center", [0, 0])
                        radius = float(circle.get("radius", 0))
                        dx = cx - center[0]
                        dy = cy - center[1]
                        if math.hypot(dx, dy) > radius:
                            issues.append(f"Room '{r.name}' extends outside circular boundary")
                            break
        
        # Direction preferences (simplified)
        # Allow overrides from constraints (e.g., house facing west prefers west entrance)
        constraints = request.constraints or {}
        house_facing = str(constraints.get("house_facing", "")).lower() if isinstance(constraints, dict) else ""

        preferences = {
            "entrance": {
                "preferred": {"north", "east", "northeast"} | ({"west"} if house_facing == "west" else set()),
                "acceptable": {"northwest"},
            },
            "kitchen": {
                "preferred": {"southeast"},
                "acceptable": {"east", "northwest"},
            },
            "master_bedroom": {
                "preferred": {"southwest"},
                "acceptable": {"south", "west"},
            },
            "bedroom": {
                "preferred": {"west", "northwest", "southwest"},
                "acceptable": {"south"},
            },
            "living": {
                "preferred": {"north", "east", "northeast"},
                "acceptable": {"northwest", "center"},
            },
            "bathroom": {
                "preferred": {"northwest", "west"},
                "acceptable": {"south"},
            },
        }

        def score_direction(room_type: str, direction: Optional[str]) -> float:
            if not direction:
                return 50.0
            prefs = preferences.get(room_type)
            if not prefs:
                return 60.0
            d = direction.lower()
            if d in prefs["preferred"]:
                return 100.0
            if d in prefs["acceptable"]:
                return 75.0
            return 40.0

        # Entrance compliance
        entrance_rooms = [r for r in request.rooms if r.name.lower() in {"main entrance", "entrance"} or r.id.lower() in {"entrance", "main_door"} or r.name.lower().startswith("entrance")]
        if entrance_rooms:
            entrance_dir = getattr(entrance_rooms[0], "direction", None)
            entrance_compliance = score_direction("entrance", entrance_dir)
        else:
            entrance_compliance = 0.0

        # Room placement and direction alignment aggregate
        dir_scores = []
        type_scores = []
        OUTDOOR_TYPES = {"garden", "lawn", "car_parking", "carport", "swimming_pool", "driveway", "deck", "patio", "terrace"}
        for r in request.rooms:
            rt = r.name.lower() if r.name else r.id.lower()
            # normalize type key if available
            if hasattr(r, "type") and isinstance(getattr(r, "type"), str):
                rt = getattr(r, "type").lower()
            # Skip outdoor fixtures from direction/type scoring
            if rt in OUTDOOR_TYPES:
                continue
            s = score_direction(rt, getattr(r, "direction", None))
            dir_scores.append(s)
            if rt in preferences:
                type_scores.append(s)

        direction_alignment_score = round(sum(dir_scores) / len(dir_scores), 2) if dir_scores else 60.0
        room_placement_score = round(sum(type_scores) / len(type_scores), 2) if type_scores else 60.0

        # Overall Vastu score combines overlap penalty and alignment metrics
        base_score = (entrance_compliance * 0.3) + (room_placement_score * 0.4) + (direction_alignment_score * 0.3)
        overlap_penalty = min(len(issues) * 8, 40)  # penalize overlaps
        vastu_score = max(0, min(100, round(base_score - overlap_penalty, 2)))

        return ValidationResponse(
            is_valid=len(issues) == 0,
            issues=issues,
            suggestions=suggestions,
            vastu_score=vastu_score,
            entrance_compliance=round(entrance_compliance, 2),
            room_placement_score=room_placement_score,
            direction_alignment_score=direction_alignment_score,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")