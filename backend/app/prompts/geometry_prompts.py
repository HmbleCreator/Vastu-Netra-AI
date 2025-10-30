"""
Prompts for handling geometric aspects of plot layouts, including polygon calculations
and coordinate generation for various plot shapes.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional

PLOT_SHAPE_ANALYSIS_PROMPT = """You are a geometry expert helping convert plot descriptions into precise geometric coordinates.
For ANY plot shape, you must:

1. Calculate exact vertices
2. Identify plot boundaries
3. Determine optimal room placement zones
4. Consider entrance and orientation

Critical Rules:
1. ALL plots must have plot_polygon with exact coordinates
2. Starting point (0,0) is bottom-left for consistency
3. Provide safe placement zones for rooms
4. Include entrance and orientation details
"""

POLYGON_CALCULATION_SYSTEM_PROMPT = """For each plot type, follow these rules:

1. Triangular Plots:
   - Right angle is origin point (0,0)
   - Base extends along x-axis
   - Height extends along y-axis
   - Calculate hypotenuse endpoints precisely
   - Define safe interior zones (70% of inradius)

2. L-Shaped Plots:
   - Treat as two rectangles
   - Calculate intersection point
   - Ensure continuous boundary
   - Mark interior corner as challenge zone

3. Irregular Plots:
   - Break down into basic geometric shapes
   - Ensure vertex ordering is counter-clockwise
   - Calculate centroid and safe zones
   - Mark narrow/wide areas

4. Any Custom Shape:
   - Must provide complete vertex list
   - Calculate area and centroid
   - Identify buildable zones
   - Mark challenging areas
"""

GEOMETRIC_CONSTRAINTS = {
    "min_room_size": {
        "bedroom": {"width": 10, "length": 12},
        "living": {"width": 12, "length": 15},
        "kitchen": {"width": 8, "length": 10},
        "bathroom": {"width": 5, "length": 7}
    },
    "safe_distance": {
        "from_boundary": 3.0,  # feet
        "between_rooms": 2.0,
        "from_corners": 4.0
    },
    "area_ratios": {
        "max_coverage": 0.65,  # 65% of plot area
        "min_circulation": 0.15  # 15% for movement
    }
}

EXAMPLE_GEOMETRY_OUTPUTS = {
    "triangular": {
        "user_input": "Triangular plot, base 150ft, height 130ft, hypotenuse faces west",
        "system_output": {
            "plot_type": "triangular",
            "dimensions": {
                "base": 150,
                "height": 130,
                "unit": "feet"
            },
            "plot_polygon": [
                [0, 0],      # Right angle at origin
                [150, 0],    # Base endpoint
                [0, 130]     # Height endpoint
            ],
            "safe_zones": {
                "centroid": [50, 43.33],
                "inradius": 37.5,
                "buildable_vertices": [
                    [30, 26],    # 70% of inradius points
                    [105, 26],
                    [30, 91]
                ]
            },
            "orientation": {
                "right_angle_at": "east",
                "hypotenuse": "west",
                "entrance_zone": [[60, 0], [90, 0]]  # Along base
            }
        }
    },
    "l_shaped": {
        "user_input": "L-shaped plot, main wing 60x40ft, side wing 30x20ft",
        "system_output": {
            "plot_type": "l_shaped",
            "dimensions": {
                "main": {"width": 60, "length": 40},
                "side": {"width": 30, "length": 20},
                "unit": "feet"
            },
            "plot_polygon": [
                [0, 0],      # Origin
                [60, 0],     # Main wing width
                [60, 20],    # Side wing height
                [30, 20],    # Inner corner
                [30, 40],    # Main wing height
                [0, 40]      # Back to origin
            ],
            "safe_zones": {
                "main_area": {"x": [5, 55], "y": [25, 35]},
                "side_area": {"x": [35, 55], "y": [5, 15]},
                "challenge_points": [[30, 20]]  # Inner corner
            },
            "recommended_flow": {
                "entrance": {"x": [10, 20], "y": 0},
                "living_zone": {"x": [5, 25], "y": [25, 35]},
                "private_zone": {"x": [35, 55], "y": [5, 15]}
            }
        }
    }
}

def calculate_safe_zones(polygon: List[List[float]]) -> Dict:
    """
    Calculate safe placement zones within any polygon
    
    Args:
        polygon: List of [x,y] vertex coordinates
    
    Returns:
        Dict with safe zones, centroid, and buildable areas
    """
    # Convert to numpy for calculations
    points = np.array(polygon)
    
    # Calculate centroid
    centroid = points.mean(axis=0)
    
    # Calculate area
    area = 0.0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    area = abs(area) / 2.0
    
    # Calculate safe inset (15% from boundaries)
    inset = min(area ** 0.5 * 0.15, 10.0)  # Max 10ft
    
    # Calculate buildable zone vertices (inset from edges)
    buildable = []
    for i in range(n):
        prev = points[i-1]
        curr = points[i]
        next_pt = points[(i+1) % n]
        
        # Calculate angle bisector
        v1 = prev - curr
        v2 = next_pt - curr
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)
        bisector = v1 + v2
        bisector = bisector / np.linalg.norm(bisector)
        
        # Inset point along bisector
        buildable.append(curr + bisector * inset)
    
    return {
        "centroid": centroid.tolist(),
        "area": area,
        "safe_inset": inset,
        "buildable_polygon": buildable,
        "min_dimension": min(area ** 0.5 * 0.1, 8.0)  # Minimum room dimension
    }

FUNCTION_SCHEMA = {
    "name": "analyze_plot_geometry",
    "description": "Convert plot description to geometric coordinates and safe zones",
    "parameters": {
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["triangular", "rectangular", "l_shaped", "irregular"],
                "description": "Basic shape category of the plot"
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "measurements": {
                        "type": "array",
                        "items": {
                            "type": "number"
                        },
                        "description": "Key measurements in feet (base, height, width etc)"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["feet", "meters"]
                    }
                }
            },
            "plot_polygon": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    },
                    "minItems": 2,
                    "maxItems": 2
                },
                "description": "Ordered list of [x,y] vertices defining the plot boundary"
            },
            "orientation": {
                "type": "object",
                "properties": {
                    "entrance_direction": {
                        "type": "string",
                        "enum": ["north", "south", "east", "west", 
                                "northeast", "northwest", "southeast", "southwest"]
                    },
                    "reference_point": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Starting point for layout [x,y]"
                    }
                }
            }
        },
        "required": ["plot_type", "dimensions", "plot_polygon"]
    }
}