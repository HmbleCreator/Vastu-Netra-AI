"""
LLM Prompt Templates for Vastu Layout Generation

These prompts are designed to:
1. Extract structured data from natural language
2. Handle special cases (triangular plots)
3. Expand terminology (3BHK → room list)
4. Parse dimensions and units
5. Capture Vastu preferences
"""

BASE_SYSTEM_PROMPT = """You are a Vastu architecture expert who helps users design home layouts. 
Your task is to understand user requirements and convert them into structured data for the layout generator.

Follow these steps:
1. Extract plot shape and dimensions
2. Identify room requirements (expand terms like "3BHK")
3. Note any Vastu preferences or constraints
4. Parse orientation and directions
5. Convert all measurements to feet

Important rules:
- Always clarify ambiguous directions
- For triangular plots, identify which side is the hypotenuse
- Convert approximate measurements ("around 30x40") to exact numbers
- Expand Indian terms (1BHK = 1 bedroom + hall + kitchen)
- Flag any Vastu violations early
"""

TRIANGULAR_PLOT_SYSTEM_PROMPT = """You are a Vastu architecture expert specializing in triangular plot layouts.

Key requirements for triangular plots:
1. Must identify hypotenuse direction clearly
2. Right angle position is crucial - infer from hypotenuse
3. Base and height must be specified
4. Area calculation must be correct (base * height / 2)
5. Room placement should maximize space near right angle

Example good input: "triangular plot with 40ft base, 30ft height, hypotenuse facing west"
Example unclear input: "triangle plot roughly 1200 sqft" (need to clarify dimensions)

Always clarify:
- Which side is the hypotenuse
- Where is the right angle
- Exact dimensions (not just area)
"""

FUNCTION_SCHEMAS = {
    "parse_plot_requirements": {
        "name": "parse_plot_requirements",
        "description": "Extract plot specifications from user input",
        "parameters": {
            "type": "object",
            "properties": {
                "shape": {
                    "type": "string",
                    "enum": ["rectangular", "triangular", "l-shaped", "irregular"],
                    "description": "Shape of the plot"
                },
                "dimensions": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["exact", "approximate"]
                        },
                        "width": {"type": "number"},
                        "length": {"type": "number"},
                        "base": {"type": "number"},
                        "height": {"type": "number"},
                        "unit": {
                            "type": "string",
                            "enum": ["feet", "meters", "yards"]
                        }
                    },
                    "required": ["type", "unit"]
                },
                "orientation": {
                    "type": "string",
                    "enum": ["north", "northeast", "east", "southeast", 
                            "south", "southwest", "west", "northwest"]
                },
                "triangular_details": {
                    "type": "object",
                    "properties": {
                        "hypotenuse_direction": {
                            "type": "string",
                            "enum": ["north", "northeast", "east", "southeast",
                                    "south", "southwest", "west", "northwest"]
                        },
                        "right_angle_position": {
                            "type": "string",
                            "enum": ["north", "northeast", "east", "southeast",
                                    "south", "southwest", "west", "northwest"]
                        }
                    }
                }
            },
            "required": ["shape", "dimensions", "orientation"]
        }
    },
    
    "parse_room_requirements": {
        "name": "parse_room_requirements",
        "description": "Extract room requirements and Vastu preferences",
        "parameters": {
            "type": "object",
            "properties": {
                "bhk_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 6,
                    "description": "Number of bedrooms (from XBH specification)"
                },
                "room_list": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["pooja_room", "kitchen", "master_bedroom", "bedroom",
                                        "bathroom", "living", "dining", "entrance", "study", "store"]
                            },
                            "name": {"type": "string"},
                            "preferred_direction": {
                                "type": "string",
                                "enum": ["north", "northeast", "east", "southeast",
                                        "south", "southwest", "west", "northwest", "center"]
                            },
                            "min_area": {"type": "number"},
                            "vastu_importance": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 3
                            }
                        },
                        "required": ["type"]
                    }
                },
                "vastu_constraints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "room_type": {"type": "string"},
                            "direction": {"type": "string"},
                            "strength": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 3
                            }
                        }
                    }
                }
            },
            "required": ["room_list"]
        }
    }
}

EXAMPLE_CONVERSATIONS = [
    # Regular rectangular plot
    {
        "user": "I want to design a 3BHK house on a 40x60 plot facing east",
        "assistant": "I'll help you design a 3BHK house. Let me extract the key details:\n\n1. Plot Specifications:\n- Shape: Rectangular\n- Dimensions: 40 feet × 60 feet\n- Orientation: East-facing\n- Total Area: 2400 square feet\n\n2. Room Requirements (3BHK means):\n- 1 Master Bedroom (preferably Southwest)\n- 2 Regular Bedrooms\n- Living Room\n- Kitchen (preferably Southeast)\n- Dining Area\n- 2-3 Bathrooms\n\nShall I proceed with the layout generation with these specifications? I'll ensure good Vastu compliance with the east-facing orientation.",
        "function_calls": [
            {
                "name": "parse_plot_requirements",
                "arguments": {
                    "shape": "rectangular",
                    "dimensions": {
                        "type": "exact",
                        "width": 40,
                        "length": 60,
                        "unit": "feet"
                    },
                    "orientation": "east"
                }
            },
            {
                "name": "parse_room_requirements",
                "arguments": {
                    "bhk_count": 3,
                    "room_list": [
                        {
                            "type": "master_bedroom",
                            "preferred_direction": "southwest",
                            "vastu_importance": 2
                        },
                        {
                            "type": "bedroom",
                            "name": "Bedroom 2"
                        },
                        {
                            "type": "bedroom",
                            "name": "Bedroom 3"
                        },
                        {
                            "type": "kitchen",
                            "preferred_direction": "southeast",
                            "vastu_importance": 2
                        },
                        {
                            "type": "living",
                            "preferred_direction": "east",
                            "vastu_importance": 2
                        },
                        {
                            "type": "dining"
                        },
                        {
                            "type": "bathroom",
                            "name": "Bathroom 1",
                            "preferred_direction": "northwest"
                        },
                        {
                            "type": "bathroom",
                            "name": "Bathroom 2",
                            "preferred_direction": "northwest"
                        }
                    ]
                }
            }
        ]
    },
    
    # Triangular plot example
    {
        "user": "I have a triangular plot with 50 feet base and 40 feet height. The longest side (hypotenuse) faces west. Need a 2BHK house.",
        "assistant": "I'll help design a 2BHK for your triangular plot. Let me confirm the specifications:\n\n1. Plot Details:\n- Shape: Triangular\n- Base: 50 feet\n- Height: 40 feet\n- Hypotenuse: Faces west\n- Right angle: Will be on the east side (opposite to hypotenuse)\n- Area: 1000 square feet (50 × 40 ÷ 2)\n\n2. For a 2BHK, we'll need:\n- Master Bedroom (preferably Southwest)\n- Second Bedroom\n- Living Room (towards East/Northeast)\n- Kitchen (preferably Southeast)\n- 2 Bathrooms\n\nSince this is a triangular plot with the hypotenuse facing west, I'll ensure:\n1. Larger rooms (living, master bedroom) near the right angle (east)\n2. Smaller rooms (bathroom, kitchen) in the narrower portions\n3. Good Vastu alignment despite the triangular constraints\n\nShall I proceed with the layout generation?",
        "function_calls": [
            {
                "name": "parse_plot_requirements",
                "arguments": {
                    "shape": "triangular",
                    "dimensions": {
                        "type": "exact",
                        "base": 50,
                        "height": 40,
                        "unit": "feet"
                    },
                    "orientation": "west",
                    "triangular_details": {
                        "hypotenuse_direction": "west",
                        "right_angle_position": "east"
                    }
                }
            },
            {
                "name": "parse_room_requirements",
                "arguments": {
                    "bhk_count": 2,
                    "room_list": [
                        {
                            "type": "master_bedroom",
                            "preferred_direction": "southwest",
                            "vastu_importance": 2
                        },
                        {
                            "type": "bedroom",
                            "name": "Bedroom 2"
                        },
                        {
                            "type": "kitchen",
                            "preferred_direction": "southeast",
                            "vastu_importance": 2
                        },
                        {
                            "type": "living",
                            "preferred_direction": "east",
                            "vastu_importance": 2
                        },
                        {
                            "type": "dining"
                        },
                        {
                            "type": "bathroom",
                            "name": "Bathroom 1",
                            "preferred_direction": "northwest"
                        },
                        {
                            "type": "bathroom",
                            "name": "Bathroom 2",
                            "preferred_direction": "northwest"
                        }
                    ],
                    "vastu_constraints": [
                        {
                            "room_type": "living",
                            "direction": "east",
                            "strength": 2,
                            "reason": "Maximize space near right angle"
                        }
                    ]
                }
            }
        ]
    }
]

CLARIFICATION_QUESTIONS = {
    "triangular_plot": [
        "Which side of the triangle is the longest (hypotenuse)?",
        "Where would you like the right angle to be?",
        "Can you specify the base and height measurements?",
        "Which direction should the entrance face?"
    ],
    "rectangular_plot": [
        "Which direction should the plot face?",
        "Would you prefer the entrance on the longer or shorter side?",
        "Are these dimensions including setback requirements?"
    ],
    "vastu_preferences": [
        "Would you like strict Vastu compliance or flexible guidelines?",
        "Do you need a Pooja room? (Important for Vastu)",
        "Any specific direction preferences for the kitchen?",
        "Should the master bedroom follow Vastu guidelines (Southwest preferred)?"
    ]
}