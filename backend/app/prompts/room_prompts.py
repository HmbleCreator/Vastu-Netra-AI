"""
Room placement and Vastu compliance prompts for the layout generation system.
Handles room relationships, adjacency rules, and Vastu preferences for any plot shape.
"""

ROOM_PLACEMENT_SYSTEM_PROMPT = """You are a Vastu architecture expert with deep understanding of room placement optimization.
For any given plot shape, you must:

1. Separate indoor vs outdoor elements
2. Handle space constraints intelligently
3. Maintain Vastu compliance where possible
4. Ensure logical room relationships

Critical Rules:
1. Indoor rooms must form a connected cluster
2. Outdoor elements should wrap around appropriately
3. Respect minimum room sizes
4. Consider entrance and circulation paths
"""

VASTU_ADAPTATION_RULES = {
    "triangular": {
        "right_angle": {
            "preferred": ["living", "master_bedroom"],
            "reason": "Maximum usable space"
        },
        "hypotenuse": {
            "avoid": ["kitchen", "bathroom"],
            "reason": "Slanted walls create unusable spaces"
        },
        "short_side": {
            "suitable": ["bathroom", "store"],
            "reason": "Efficient use of narrow spaces"
        }
    },
    "l_shaped": {
        "inner_corner": {
            "preferred": ["living", "dining"],
            "reason": "Creates natural division"
        },
        "wings": {
            "private": ["bedrooms", "bathrooms"],
            "public": ["living", "kitchen"]
        }
    },
    "irregular": {
        "wide_zones": {
            "preferred": ["living", "master_bedroom"],
            "reason": "Needs regular shaped space"
        },
        "narrow_zones": {
            "suitable": ["corridor", "bathroom"],
            "reason": "Efficient use of challenging spaces"
        }
    }
}

ROOM_ADJACENCY_RULES = {
    "privacy_zones": {
        "public": ["entrance", "living", "dining"],
        "semi_private": ["kitchen", "study", "pooja"],
        "private": ["bedroom", "bathroom"]
    },
    "noise_zones": {
        "loud": ["living", "kitchen"],
        "medium": ["dining", "study"],
        "quiet": ["bedroom", "pooja"]
    },
    "preferred_adjacencies": {
        "kitchen": ["dining", "store"],
        "bedroom": ["bathroom"],
        "entrance": ["living"],
        "pooja": ["east_wall"]  # Vastu preference
    }
}

TWO_PHASE_SOLVER_PROMPT = """
Phase 1: Indoor Core Layout
- Group all indoor rooms
- Start with largest rooms at optimal positions
- Maintain minimum clearances
- Ensure door connectivity

Phase 2: Outdoor Element Placement
- Identify remaining plot area
- Place gardens along suitable edges
- Position utilities (bore well, tank) appropriately
- Maintain setbacks and access paths
"""

CHALLENGING_CASES = {
    "narrow_plots": {
        "min_width": 20,  # feet
        "solutions": [
            "Linear room arrangement",
            "Combine smaller functions",
            "Use vertical space efficiently"
        ]
    },
    "irregular_corners": {
        "treatment": [
            "Storage solutions",
            "Green spaces",
            "Utility areas"
        ]
    },
    "large_outdoor": {
        "strategy": [
            "Create activity zones",
            "Buffer spaces",
            "Green belt planning"
        ]
    }
}

ROOM_SIZE_ADJUSTMENTS = {
    "compress_factors": {
        "bedroom": 0.85,  # Can reduce to 85% if needed
        "living": 0.9,
        "kitchen": 0.8,
        "bathroom": 0.75
    },
    "minimum_absolute": {
        "bedroom": {"width": 8, "length": 10},
        "living": {"width": 10, "length": 12},
        "kitchen": {"width": 6, "length": 8},
        "bathroom": {"width": 4, "length": 6}
    }
}

EXAMPLE_ROOM_ARRANGEMENTS = {
    "triangular": {
        "description": "3BHK in triangular plot",
        "layout_strategy": {
            "phase1_indoor": [
                {
                    "zone": "right_angle",
                    "rooms": ["living", "master_bedroom"],
                    "reason": "Maximize rectangular space"
                },
                {
                    "zone": "middle",
                    "rooms": ["kitchen", "bedroom2"],
                    "reason": "Regular shaped area"
                },
                {
                    "zone": "narrow_end",
                    "rooms": ["bathroom", "store"],
                    "reason": "Efficient use of tapering space"
                }
            ],
            "phase2_outdoor": [
                {
                    "zone": "wide_edge",
                    "elements": ["garden", "parking"],
                    "reason": "Good access and visibility"
                },
                {
                    "zone": "back_corner",
                    "elements": ["utility", "tank"],
                    "reason": "Less premium space"
                }
            ]
        }
    }
}

FUNCTION_SCHEMA = {
    "name": "optimize_room_placement",
    "description": "Generate optimized room placement strategy for given plot",
    "parameters": {
        "type": "object",
        "properties": {
            "plot_info": {
                "type": "object",
                "properties": {
                    "shape": {"type": "string"},
                    "special_zones": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "zone_type": {"type": "string"},
                                "coordinates": {"type": "array"}
                            }
                        }
                    }
                }
            },
            "rooms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "min_size": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "number"},
                                "length": {"type": "number"}
                            }
                        },
                        "vastu_preference": {"type": "string"}
                    }
                }
            },
            "vastu_importance": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3,
                "description": "1=flexible, 2=preferred, 3=strict"
            }
        },
        "required": ["plot_info", "rooms"]
    }
}