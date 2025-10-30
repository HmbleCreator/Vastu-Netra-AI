"""
Shape-aware solver that uses geometric analysis to optimize room placement
for any plot shape including complex polygons.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from .geometry_analyzer import (
    ShapeAnalyzer, CircularPlotHandler, RegularPolygonHandler,
    Point, Vertex, Edge, ShapeComplexity
)

class ShapeAwareSolver:
    """
    A solver that understands and adapts to any plot shape.
    Uses geometric analysis to make intelligent room placement decisions.
    """
    
    def __init__(self, plot_vertices: List[List[float]], 
                 room_requirements: List[Dict]):
        self.shape_analyzer = ShapeAnalyzer(plot_vertices)
        self.rooms = room_requirements
        self.zones = self.shape_analyzer.buildable_zones
        self.room_placements = []
        
        # Special handlers for specific shapes
        if self._is_circular():
            center = self._find_center()
            radius = self._calculate_radius()
            self.special_handler = CircularPlotHandler(center, radius)
        elif self._is_regular_polygon():
            center = self._find_center()
            radius = self._calculate_radius()
            num_sides = len(plot_vertices)
            self.special_handler = RegularPolygonHandler(num_sides, center, radius)
        else:
            self.special_handler = None

    def solve(self) -> Dict:
        """Main solving algorithm"""
        # 1. Analyze shape complexity
        complexity = self.shape_analyzer.complexity
        
        # 2. Choose appropriate strategy
        if complexity == ShapeComplexity.SIMPLE:
            return self._solve_simple_shape()
        elif complexity == ShapeComplexity.REGULAR:
            return self._solve_regular_polygon()
        elif complexity == ShapeComplexity.CURVED:
            return self._solve_curved_shape()
        else:
            return self._solve_irregular_shape()

    def _solve_simple_shape(self) -> Dict:
        """Handle simple shapes (rectangles, triangles)"""
        # Use main buildable zone
        primary_zone = self.zones[0]
        room_assignments = []
        
        # Sort rooms by size and importance
        sorted_rooms = self._sort_rooms_by_priority()
        
        # Place rooms in grid pattern
        grid = self._create_grid_layout(primary_zone, sorted_rooms)
        
        return {
            "layout": grid,
            "vastu_score": self._calculate_vastu_score(grid),
            "efficiency": self._calculate_space_efficiency(grid)
        }

    def _solve_regular_polygon(self) -> Dict:
        """Handle regular polygons using symmetry"""
        if not self.special_handler:
            return self._solve_irregular_shape()
            
        # Get symmetric zones
        zones = self.special_handler.get_symmetric_zones()
        
        # Place rooms respecting symmetry
        layout = self._place_rooms_symmetrically(zones)
        
        return {
            "layout": layout,
            "symmetry_score": self._calculate_symmetry_score(layout),
            "vastu_score": self._calculate_vastu_score(layout)
        }

    def _solve_curved_shape(self) -> Dict:
        """Handle circular or curved shapes"""
        if not self.special_handler:
            return self._solve_irregular_shape()
            
        # Get radial zones
        num_zones = len(self.rooms)
        zones = self.special_handler.get_radial_zones(num_zones)
        
        # Place rooms in radial pattern
        layout = self._place_rooms_radially(zones)
        
        return {
            "layout": layout,
            "circularity_score": self._calculate_circularity_score(layout),
            "flow_score": self._calculate_flow_score(layout)
        }

    def _solve_irregular_shape(self) -> Dict:
        """Handle irregular shapes using zone decomposition"""
        # Break down into simpler zones
        zones = self.shape_analyzer.buildable_zones
        
        # Place rooms optimally in each zone
        layout = self._place_rooms_in_zones(zones)
        
        return {
            "layout": layout,
            "efficiency": self._calculate_space_efficiency(layout),
            "connectivity": self._calculate_connectivity_score(layout)
        }

    def _create_grid_layout(self, zone: Dict, 
                          rooms: List[Dict]) -> List[Dict]:
        """Create a grid-based layout in a rectangular zone"""
        grid = []
        available_width = zone["width"]
        available_height = zone["height"]
        
        # Sort rooms by size
        rooms.sort(key=lambda x: x["area"], reverse=True)
        
        # Simple grid packing algorithm
        x, y = 0, 0
        row_height = 0
        
        for room in rooms:
            if x + room["width"] > available_width:
                # Move to next row
                x = 0
                y += row_height
                row_height = 0
            
            if y + room["height"] > available_height:
                break  # Out of space
                
            grid.append({
                "room": room["name"],
                "x": x,
                "y": y,
                "width": room["width"],
                "height": room["height"]
            })
            
            x += room["width"]
            row_height = max(row_height, room["height"])
            
        return grid

    def _place_rooms_symmetrically(self, zones: List[Dict]) -> List[Dict]:
        """Place rooms in symmetric zones"""
        placements = []
        rooms_per_zone = len(self.rooms) // len(zones)
        
        for i, zone in enumerate(zones):
            start_idx = i * rooms_per_zone
            zone_rooms = self.rooms[start_idx:start_idx + rooms_per_zone]
            
            # Calculate zone centroid
            centroid = self._calculate_zone_centroid(zone)
            
            # Place rooms around centroid
            for j, room in enumerate(zone_rooms):
                angle = zone["orientation"] + (j * 360 / rooms_per_zone)
                distance = room["area"] ** 0.5  # Approximate room size
                
                x = centroid.x + distance * np.cos(np.radians(angle))
                y = centroid.y + distance * np.sin(np.radians(angle))
                
                placements.append({
                    "room": room["name"],
                    "x": x,
                    "y": y,
                    "rotation": angle
                })
                
        return placements

    def _place_rooms_radially(self, zones: List[Dict]) -> List[Dict]:
        """Place rooms in radial pattern"""
        placements = []
        
        # Sort rooms by Vastu direction preference
        rooms_by_direction = self._group_rooms_by_direction()
        
        for zone in zones:
            # Find rooms that prefer this direction
            preferred_rooms = rooms_by_direction.get(
                self._angle_to_direction(zone["start_angle"]), []
            )
            
            if not preferred_rooms:
                continue
                
            # Place room in zone
            room = preferred_rooms.pop(0)
            radius_ratio = 0.7  # Place at 70% of radius for spacing
            angle = (zone["start_angle"] + zone["end_angle"]) / 2
            
            x = self.special_handler.center.x + \
                self.special_handler.radius * radius_ratio * np.cos(angle)
            y = self.special_handler.center.y + \
                self.special_handler.radius * radius_ratio * np.sin(angle)
                
            placements.append({
                "room": room["name"],
                "x": x,
                "y": y,
                "rotation": np.degrees(angle)
            })
            
        return placements

    def _place_rooms_in_zones(self, zones: List[Dict]) -> List[Dict]:
        """Place rooms in irregular zones"""
        placements = []
        
        # Sort zones by area
        zones.sort(key=lambda x: x["area"], reverse=True)
        
        # Sort rooms by size and importance
        rooms = self._sort_rooms_by_priority()
        
        for zone in zones:
            # Find rooms that fit in this zone
            fitting_rooms = [
                r for r in rooms 
                if r["area"] <= zone["area"] * 0.8  # 80% fill ratio
            ]
            
            if not fitting_rooms:
                continue
                
            # Place largest fitting room
            room = fitting_rooms[0]
            rooms.remove(room)
            
            # Calculate best position in zone
            position = self._find_best_position_in_zone(room, zone)
            placements.append({
                "room": room["name"],
                "position": position
            })
            
        return placements

    def _calculate_vastu_score(self, layout: List[Dict]) -> float:
        """Calculate Vastu compliance score"""
        score = 0.0
        total_weights = 0
        
        for placement in layout:
            room = self._get_room_by_name(placement["room"])
            if not room or "vastu_preference" not in room:
                continue
                
            # Check direction alignment
            actual_direction = self._calculate_direction(
                placement["x"], placement["y"]
            )
            preferred_direction = room["vastu_preference"]
            
            direction_score = self._calculate_direction_match(
                actual_direction, preferred_direction
            )
            
            weight = room.get("vastu_importance", 1)
            score += direction_score * weight
            total_weights += weight
            
        return score / total_weights if total_weights > 0 else 0.0

    def _calculate_space_efficiency(self, layout: List[Dict]) -> float:
        """Calculate how efficiently space is used"""
        total_room_area = sum(
            placement.get("width", 0) * placement.get("height", 0)
            for placement in layout
        )
        plot_area = self.shape_analyzer.area
        return total_room_area / plot_area

    def _find_best_position_in_zone(self, room: Dict, 
                                  zone: Dict) -> Point:
        """Find optimal position for room in zone"""
        # Start with zone centroid
        centroid = self._calculate_zone_centroid(zone)
        
        # Adjust based on Vastu preference if any
        if "vastu_preference" in room:
            preferred_angle = self._direction_to_angle(room["vastu_preference"])
            radius = min(zone["width"], zone["height"]) * 0.3
            
            x = centroid.x + radius * np.cos(preferred_angle)
            y = centroid.y + radius * np.sin(preferred_angle)
            
            # Ensure point is inside zone
            if self._point_in_polygon([x, y], zone["vertices"]):
                return Point(x, y)
        
        return centroid

    @staticmethod
    def _calculate_direction_match(actual: str, preferred: str) -> float:
        """Calculate how well actual direction matches preferred"""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        actual_idx = directions.index(actual)
        preferred_idx = directions.index(preferred)
        
        # Calculate minimum angular difference
        diff = min(
            abs(actual_idx - preferred_idx),
            8 - abs(actual_idx - preferred_idx)
        )
        
        # Convert to score (0 to 1)
        return 1 - (diff / 4)  # Maximum difference is 4 steps

# Example usage:
"""
plot_vertices = [
    [0, 0], [100, 0], [100, 50],
    [70, 50], [70, 100], [0, 100]
]

rooms = [
    {
        "name": "living",
        "area": 300,
        "vastu_preference": "E",
        "vastu_importance": 3
    },
    {
        "name": "kitchen",
        "area": 150,
        "vastu_preference": "SE",
        "vastu_importance": 2
    }
]

solver = ShapeAwareSolver(plot_vertices, rooms)
solution = solver.solve()
"""