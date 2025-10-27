# Layout Generation Tools - Implementation Specification

## Overview
Create three layout generation solvers that work together to generate floor plans. The LLM orchestrator will call these as tools via function calling.

---

## Tool 1: Graph-Based Solver (Primary, Fast)

### Purpose
Generate floor plans using physics simulation. Think of rooms as magnets - adjacent rooms attract, non-adjacent rooms repel.

### Algorithm: Force-Directed Layout (Fruchterman-Reingold)

#### Step 1: Initialize
```
Input:
  - rooms_needed: ["kitchen", "living", "master_bedroom", "bedroom_2", "bathroom"]
  - total_area: 2000 sqft
  - plot_dimensions: (40, 50) feet
  - vastu_constraints: {"kitchen_north": true}

Create:
  - Graph with rooms as nodes
  - Edges between adjacent rooms (kitchen ↔ living, bedroom ↔ bathroom, etc.)
  - Each node has: x, y position, width, height

Random initialization:
  - Place all rooms at random positions within plot
  - Give each room initial dimensions based on standard specs
```

#### Step 2: Calculate Room Sizes
```
For each room type:
  kitchen: 120-180 sqft (10x12 to 12x15 feet)
  living: 300-400 sqft (16x18 to 20x20 feet)
  master_bedroom: 200-250 sqft (14x14 to 16x16 feet)
  bedroom: 150-180 sqft (12x12 to 14x13 feet)
  bathroom: 40-60 sqft (6x7 to 8x8 feet)

Scale proportionally if total doesn't fit in plot
```

#### Step 3: Physics Simulation (100 iterations)
```python
For each iteration:
  forces = {}
  
  # Calculate pairwise forces between all rooms
  For each pair of rooms (room_a, room_b):
    distance = euclidean_distance(room_a.center, room_b.center)
    direction = unit_vector(room_b.center - room_a.center)
    
    If rooms are adjacent (connected by edge):
      # Attract to ideal distance (barely touching)
      ideal_distance = (room_a.width + room_b.width) / 2 + 1 foot gap
      force = 0.5 * (distance - ideal_distance) * direction
    Else:
      # Repel (push apart)
      force = -1.0 * (5 / distance) * direction
    
    forces[room_a] += force
    forces[room_b] -= force
  
  # Add Vastu directional forces
  If kitchen_north constraint:
    forces[kitchen] += (0, 2.0)  # Push north (positive y)
  
  If master_bedroom_southwest constraint:
    forces[master_bedroom] += (-1.5, -1.5)  # Push to SW corner
  
  # Update positions with damping
  For each room:
    velocity = (velocity + forces[room]) * 0.8  # 0.8 = damping
    room.x += velocity.x * 0.1  # 0.1 = time step
    room.y += velocity.y * 0.1
    
    # Keep within boundaries
    room.x = clamp(room.x, 0, plot_width - room.width)
    room.y = clamp(room.y, 0, plot_height - room.height)
  
  # Stop if converged (average velocity < 0.01)
```

#### Step 4: Resolve Overlaps
```
For each pair of overlapping rooms:
  overlap_x = how much they overlap horizontally
  overlap_y = how much they overlap vertically
  
  If overlapping:
    Push them apart by (overlap_x/2, overlap_y/2)
    Repeat until no overlaps
```

#### Step 5: Snap to Grid
```
For professional appearance:
  Round all positions to 0.5 foot increments
  room.x = round(room.x / 0.5) * 0.5
  room.width = round(room.width / 0.5) * 0.5
```

#### Step 6: Return Layout
```json
{
  "rooms": [
    {
      "id": "kitchen",
      "name": "Kitchen",
      "x": 25.5,
      "y": 38.0,
      "width": 12.0,
      "height": 14.5,
      "facing": "north",
      "area": 174
    },
    ...
  ],
  "walls": [...],
  "total_area": 1847,
  "generation_time": 1.2
}
```

### Implementation Requirements

**Dependencies:**
```
networkx: For graph structure
numpy: For vector math
```

**Key Functions:**
```python
class GraphBasedLayoutSolver:
    def solve(params) -> LayoutData:
        # Main entry point
        
    def _build_graph(rooms_needed):
        # Create nodes and edges
        
    def _physics_simulation(iterations=100):
        # Force-directed layout
        
    def _resolve_overlaps():
        # Push overlapping rooms apart
        
    def _snap_to_grid():
        # Round positions
```

**Performance:**
- Target: <2 seconds for 5-6 room layouts
- Should handle up to 10 rooms
- Gracefully fail if doesn't converge in 100 iterations

---

## Tool 2: Constraint Solver (Fallback, Slow but Guaranteed)

### Purpose
Generate floor plans using mathematical optimization. Guarantees exact constraints (no overlaps, exact sizes).

### Algorithm: Constraint Satisfaction (OR-Tools CP-SAT)

#### Step 1: Define Variables
```
For each room:
  x = IntVar(0, plot_width - room.min_width)
  y = IntVar(0, plot_height - room.min_height)
  width = IntVar(room.min_width, room.max_width)
  height = IntVar(room.min_height, room.max_height)
```

#### Step 2: Add Constraints
```
1. Area constraint:
   For each room:
     width * height >= min_area
     width * height <= max_area

2. No overlap constraint:
   For each pair (room_a, room_b):
     room_a ends before room_b starts (x-axis) OR
     room_b ends before room_a starts (x-axis) OR
     room_a ends before room_b starts (y-axis) OR
     room_b ends before room_a starts (y-axis)

3. Within boundaries:
   For each room:
     x + width <= plot_width
     y + height <= plot_height

4. Vastu constraints (if specified):
   If kitchen_north:
     kitchen.y >= plot_height * 0.7
```

#### Step 3: Solve
```
solver = CP-SAT Solver
solver.timeout = 30 seconds
status = solver.Solve(model)

If status == OPTIMAL or FEASIBLE:
  Extract solution
Else:
  Return error
```

### Implementation Requirements

**Dependencies:**
```
ortools: Google OR-Tools library
```

**Key Challenge: Integer Type Handling**
```python
# CRITICAL: All bounds must be int BEFORE creating variables
x_min = int(0)
x_max = int(plot_width - room.min_width)
x_var = model.NewIntVar(x_min, x_max, "kitchen_x")

# DO NOT pass floats to NewIntVar - causes "Not a number" error
```

**Performance:**
- Typical: 25-35 seconds
- Timeout: 30 seconds
- Falls back to graph solver if timeout

---

## Tool 3: Hybrid Solver (Smart Router)

### Purpose
Combines both solvers intelligently. Always returns a result.

### Algorithm: Try-Evaluate-Pick

#### Step 1: Try Graph Solver (0-5 seconds)
```python
try:
    start = time.now()
    graph_layout = graph_solver.solve(params)
    graph_score = evaluate_quality(graph_layout)
    graph_time = time.now() - start
    
    results.append({
        "layout": graph_layout,
        "score": graph_score,
        "solver": "graph",
        "time": graph_time
    })
except Exception as e:
    log("Graph solver failed: " + e)
```

#### Step 2: Try Constraint Solver (5-35 seconds)
```python
If time_remaining > 10 seconds:
    try:
        start = time.now()
        constraint_layout = constraint_solver.solve(params, timeout=25)
        constraint_score = evaluate_quality(constraint_layout)
        constraint_time = time.now() - start
        
        results.append({
            "layout": constraint_layout,
            "score": constraint_score,
            "solver": "constraint",
            "time": constraint_time
        })
    except Exception as e:
        log("Constraint solver failed: " + e)
```

#### Step 3: Evaluate Quality (0-100 score)
```python
def evaluate_quality(layout):
    score = 100
    
    # Penalty for overlaps
    For each pair of overlapping rooms:
        overlap_area = calculate_overlap(room_a, room_b)
        score -= overlap_area / 10
    
    # Penalty for poor space utilization
    utilization = layout.total_area / layout.construction_area
    If utilization < 0.8:
        score -= (1 - utilization) * 20
    
    # Penalty for rooms outside boundaries
    For each room:
        If room.x < 0 or room.y < 0:
            score -= 5
    
    # Penalty for insufficient walls
    If len(layout.walls) < 4:
        score -= 10
    
    return max(0, score)
```

#### Step 4: Pick Best Result
```python
If results is not empty:
    Sort results by score (highest first)
    return results[0].layout
Else:
    # Both solvers failed - use fallback
    return generate_grid_fallback(params)
```

#### Step 5: Grid Fallback (Always Succeeds)
```python
def generate_grid_fallback(params):
    rooms = []
    x = 2.0
    y = 2.0
    cols = 3
    
    For each room in params.rooms_needed:
        room = {
            "x": x,
            "y": y,
            "width": 12.0,
            "height": 15.0,
            "area": 180.0
        }
        rooms.append(room)
        
        x += 12.0 + 1.5  # room width + gap
        
        If x > plot_width - 12:
            x = 2.0
            y += 15.0 + 1.5  # move to next row
    
    return LayoutData(rooms=rooms, ...)
```

### Implementation Requirements

**Key Functions:**
```python
class HybridSolver:
    def solve(params) -> LayoutData:
        # Try both solvers, pick best
        
    def _evaluate_quality(layout) -> float:
        # Score 0-100
        
    def _generate_fallback(params) -> LayoutData:
        # Grid-based backup
```

---

## Integration: How LLM Calls These Tools

### Function Definitions for LLM
```json
{
  "name": "generate_layout_hybrid",
  "description": "Generate floor plan using hybrid solver (fast graph + reliable constraint fallback)",
  "parameters": {
    "total_area": {"type": "number", "description": "Building area in sqft"},
    "plot_dimensions": {"type": "array", "items": {"type": "number"}},
    "orientation": {"type": "string", "enum": ["north", "south", "east", "west"]},
    "rooms_needed": {"type": "array", "items": {"type": "string"}},
    "vastu_constraints": {
      "type": "object",
      "properties": {
        "kitchen_north": {"type": "boolean"},
        "master_bedroom_southwest": {"type": "boolean"}
      }
    }
  }
}
```

### LLM Workflow
```
User: "Design a 3BHK house with kitchen facing north"

LLM Understands:
  - 3BHK = 3 bedrooms + hall + kitchen
  - rooms_needed = ["kitchen", "living", "master_bedroom", 
                    "bedroom_2", "bedroom_3", "bathroom_1", "bathroom_2"]
  - vastu_constraints = {"kitchen_north": true}

LLM Calls Tool:
  generate_layout_hybrid({
    "total_area": 2000,  // LLM estimates from 3BHK
    "plot_dimensions": [40, 50],  // LLM estimates
    "orientation": "east",  // Default if not specified
    "rooms_needed": [...],
    "vastu_constraints": {"kitchen_north": true}
  })

Tool Returns:
  {
    "status": "success",
    "solver_used": "graph",
    "generation_time": 1.2,
    "layout": {...},
    "vastu_score": 92,
    "structural_score": 85
  }

LLM Responds:
  "I've designed your 3BHK layout! The kitchen faces north 
   as requested (Vastu compliant). Vastu score: 92%.
   Would you like to see the floor plan?"
```

---

## Expected Outputs

### LayoutData Structure
```typescript
interface LayoutData {
  rooms: Room[];
  walls: Wall[];
  doors: Door[];
  windows: Window[];
  total_area: number;
  circulation_area: number;
  construction_area: number;
}

interface Room {
  id: string;              // "kitchen", "master_bedroom"
  name: string;            // "Kitchen", "Master Bedroom"
  room_type: string;       // "kitchen", "bedroom"
  x: number;               // Position (feet)
  y: number;
  width: number;           // Dimensions (feet)
  height: number;
  facing: string;          // "north", "east", "interior"
  area: number;            // Square feet
  doors?: Door[];
  windows?: Window[];
}

interface Wall {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  is_load_bearing: boolean;
  thickness: number;       // Default: 0.75 ft (9 inches)
}
```

### Performance Targets
```
Graph Solver:
  ✓ 3-4 room layout: 0.5-1 second
  ✓ 5-6 room layout: 1-2 seconds
  ✓ 7-10 room layout: 2-4 seconds
  ✗ Fails: Fall back to constraint solver

Constraint Solver:
  ✓ Any layout: 25-35 seconds
  ✗ Timeout after 30 seconds

Hybrid:
  ✓ Always succeeds (fallback grid)
  ✓ Average time: 2-5 seconds (graph usually wins)
```

---

## Testing Requirements

### Test Cases

**Test 1: Simple 3BHK**
```json
{
  "total_area": 1500,
  "plot_dimensions": [35, 45],
  "orientation": "east",
  "rooms_needed": ["kitchen", "living", "master_bedroom", "bedroom_2", "bathroom"],
  "vastu_constraints": {}
}
```
Expected: Graph solver succeeds in <1 second

**Test 2: Complex 5BHK with Vastu**
```json
{
  "total_area": 3000,
  "plot_dimensions": [50, 60],
  "orientation": "north",
  "rooms_needed": ["kitchen", "living", "dining", "master_bedroom", 
                   "bedroom_2", "bedroom_3", "bedroom_4", "bedroom_5",
                   "bathroom_1", "bathroom_2", "study"],
  "vastu_constraints": {
    "kitchen_north": true,
    "master_bedroom_southwest": true
  }
}
```
Expected: Graph solver tries, might fail → Constraint solver succeeds

**Test 3: Edge Case - Tiny Plot**
```json
{
  "total_area": 800,
  "plot_dimensions": [20, 40],
  "orientation": "south",
  "rooms_needed": ["kitchen", "living", "bedroom", "bathroom"],
  "vastu_constraints": {}
}
```
Expected: Both might struggle → Fallback grid layout

---

## Error Handling

### Graph Solver Failures
```
Scenario: Doesn't converge in 100 iterations
Action: Log warning, fall back to constraint solver
Message: "Graph solver didn't converge, trying constraint solver..."
```

### Constraint Solver Failures
```
Scenario: Timeout after 30 seconds
Action: Log warning, use fallback grid
Message: "Constraint solver timed out, using fallback layout..."

Scenario: "Not a number: kitchen_h" error
Cause: Float passed to IntVar
Action: Log error, use fallback grid
Message: "Constraint solver failed (type error), using fallback..."
```

### Both Fail
```
Action: Generate grid fallback (always succeeds)
Message: "Generating fallback layout..."
Result: Simple 3x3 grid arrangement of rooms
```

---

## File Structure

```
app/
└── services/
    ├── graph_solver_service.py         # Tool 1
    │   └── GraphBasedLayoutSolver
    │
    ├── solver_service.py                # Tool 2
    │   └── ConstraintSolverService
    │
    └── hybrid_solver.py                 # Tool 3
        └── HybridSolver
            ├── solve()
            ├── _evaluate_quality()
            └── _generate_fallback()
```

---

## Success Criteria

✅ Graph solver completes in <2 seconds for typical layouts
✅ Constraint solver provides guaranteed correct solutions
✅ Hybrid never fails (fallback always works)
✅ Quality scoring differentiates good/bad layouts
✅ Vastu constraints are enforced
✅ No type errors from OR-Tools
✅ Output format matches LayoutData schema
✅ All test cases pass