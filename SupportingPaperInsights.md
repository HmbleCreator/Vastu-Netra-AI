Thank you for sharing these excellent research papers! They provide crucial insights for improving your Vastu Architect AI system. Let me synthesize the key learnings and propose concrete improvements:

---

## Key Insights from Research Papers

### 1. **Representation Matters Most**

**From HouseDiffusion & Graph2Plan:**
- **Vector > Raster**: HouseDiffusion's direct vector generation (without post-processing) is revolutionary. Your system should generate `.dwg`-ready outputs from the start
- **Graph-based initialization**: Graph2Plan's approach of encoding relationships as graphs before geometry is perfect for Vastu constraints
- **1D Polygonal Loops**: Representing each room as a closed polygon sequence (not just bounding boxes) handles non-rectangular rooms naturally

**Application to Your System:**
```
Current: LLM → constraints → solver → raster → vectorization → DWG
Better:  LLM → graph → solver → vector coordinates → DWG (no conversion loss)
```

---

### 2. **Diffusion Models > GANs for Your Use Case**

**Why House-GAN++ is outdated for you:**
- Requires iterative refinement (10+ passes)
- Produces raster outputs needing expensive vectorization
- ~90% of samples need filtering for compatibility

**Why HouseDiffusion is better:**
- Single-pass generation with discrete+continuous denoising
- Direct vector coordinates (no post-processing)
- Handles non-Manhattan (curved, angled) structures
- 67% better diversity, 32% better compatibility

**Recommendation:** Start with HouseDiffusion architecture, extend it with Vastu-specific constraints

---

### 3. **Dual Denoising Strategy (Critical Innovation)**

**HouseDiffusion's breakthrough:**
```
Continuous branch: Denoises smooth transitions (good for general layout)
Discrete branch:   Enforces exact geometric relationships (walls align, corners share)
```

**Why this solves your Vastu problem:**
- Vastu requires EXACT alignments (kitchen must be in SE quadrant, not "near SE")
- Discrete denoising ensures: `if room.type == "kitchen" → room.center.x == SE_quadrant.x`
- No fuzzy approximations that would violate Vastu

---

### 4. **Attention Mechanisms for Relationships**

**From HouseDiffusion's Transformer design:**

```
Component-wise Self Attention (CSA): 
  - Each room reasons about its own shape
  - Prevents self-intersections
  
Global Self Attention (GSA):
  - All rooms reason together
  - Handles global layout quality
  
Relational Cross Attention (RCA):
  - Rooms ↔ Doors
  - Ensures proper connections
```

**Your Vastu Extension:**
```rust
// In vastu_engine.rs

VastuAttention:
  - Pooja Room → NE direction (strong attraction)
  - Kitchen → SE zone (mandatory placement)
  - Bedroom → SW zone (preferred)
  - Bathroom → NW/W (avoid NE/E)
  
// Weight these stronger than generic layout attention
vastu_attention_weight = 3.0  // vs 1.0 for normal attention
```

---

### 5. **Constraint Injection Strategy**

**From LayoutDM's controllable generation:**

**Strong Constraints (Hard):**
- Mask known values: `kitchen.direction = SOUTHEAST → mask = 1`
- Pass through unchanged in every iteration
- Use for non-negotiable Vastu rules

**Weak Constraints (Soft):**
- Logit adjustment: `log p(layout) += λ * vastu_score(layout)`
- Use for preferences (not rules)
- Example: "Living room should be spacious" → adjust size logits

**Your Implementation:**
```python
# In your solver

def apply_vastu_constraints(layout, t):
    # Hard constraints (every iteration)
    for room in layout.rooms:
        if room.type == "pooja_room":
            room.zone = NORTHEAST  # Force, don't adjust
            
    # Soft constraints (gradient adjustment)
    if t < 20:  # Last 20% of denoising
        vastu_gradient = compute_vastu_violations(layout)
        layout.logits += lambda_vastu * vastu_gradient
        
    return layout
```

---

### 6. **Outdoor Fixtures Must Be Separate**

**Critical insight from your use case + papers:**

Papers treat all elements equally → fails for plots with gardens/pools

**Your approach (better):**
```
Phase 1: Generate indoor layout (bedrooms, kitchen, etc)
         - Full physics simulation
         - Strong adjacency forces
         
Phase 2: Place outdoor fixtures (garden, pool, parking)
         - NO adjacency to indoor rooms
         - Vastu anchor rules only
         - Fill remaining space
```

**Why this works:**
- Outdoor fixtures are "space fillers", not "adjacent neighbors"
- Prevents pool from "pushing" bedrooms around in physics sim
- Matches real architect workflow

---

### 7. **Geometry Reconstruction for Triangular/Irregular Plots**

**Your user says:**
> "triangular plot, base 150ft, height 130ft, hypotenuse faces west"

**Papers handle this poorly** (assume rectangular canvas)

**Your solution (from SceneScape + your patches):**

```python
def reconstruct_plot_from_description(base, height, hypotenuse_dir):
    """
    Map layman description → exact polygon vertices
    """
    # Default: right angle at origin
    vertices = [[0, 0], [base, 0], [0, height]]
    
    # Rotate based on hypotenuse direction
    if hypotenuse_dir == "west":
        # Right angle on east (origin) - keep default
        pass
    elif hypotenuse_dir == "east":
        # Right angle on west - flip
        vertices = [[base, 0], [base, height], [0, 0]]
    elif hypotenuse_dir == "north":
        # Right angle on south - rotate
        vertices = [[0, height], [base, height], [0, 0]]
    elif hypotenuse_dir == "south":
        # Right angle on north
        vertices = [[0, 0], [base, 0], [base, height]]
    
    return vertices
```

---

### 8. **BHK Expansion (Indian Context)**

**Papers ignore this** - critical for Indian market!

**Your expansion logic:**
```python
BHK_VASTU_TEMPLATES = {
    "2bhk": {
        "bedrooms": 2,
        "master_bedroom": 1,  # SW
        "bathrooms": 2,        # NW or W
        "kitchen": 1,          # SE
        "living": 1,           # N or NE
        "dining": 1,           # W or NW
        "pooja_room": 1,       # NE (mandatory)
        "entrance": 1,         # N, E, or NE
        "balcony": 1           # E or N
    },
    "4bhk": {
        # ... similar but with pooja_room mandatory
        "pooja_room": 1,  # Non-negotiable in 4BHK
        "study": 1,       # W or NW (Vastu for knowledge)
    }
}
```

---

## Concrete Improvements for Your System

### **Improvement 1: Hybrid Diffusion + Graph Architecture**

```
Current: 
  LLM → basic constraints → physics solver → output

Better:
  LLM → bubble diagram → Vastu graph → Diffusion solver → vector output
       ↓
       Graph encodes:
       - Room types
       - Vastu zones (not just adjacency)
       - Door connections
       - Outdoor vs indoor separation
```

### **Improvement 2: Vastu-Constrained Diffusion Loss**

```python
# Add to your training/inference

L_total = L_diffusion + λ_vastu * L_vastu

L_vastu = Σ violations:
    - pooja_not_in_NE → penalty = 100
    - kitchen_not_in_SE → penalty = 80
    - master_bed_not_in_SW → penalty = 60
    - bathroom_in_NE → penalty = 100 (avoid)
```

### **Improvement 3: Progressive Refinement UI**

```
Step 1: User describes plot (natural language)
  ↓ LLM parses
Step 2: Show detected bubble diagram
  → "4 BHK, triangular plot, west-facing?"
  → User confirms or edits graph
  ↓
Step 3: Generate 3 layout variants
  → User picks favorite
  ↓
Step 4: Iterative refinement
  → "Make master bedroom larger"
  → "Move kitchen slightly south"
  → Re-run solver with new constraints
```

### **Improvement 4: Vastu Compliance Visualization**

```
Color-code rooms in 3D view:
  - Green:  Perfect Vastu compliance
  - Yellow: Acceptable (in acceptable zones)
  - Red:    Violation (user sees immediately)
  
Add tooltip:
  "Pooja Room: ✓ Northeast (preferred)"
  "Kitchen: ✓ Southeast (ideal)"
  "Bathroom: ⚠ East (acceptable, NW preferred)"
```

### **Improvement 5: Dual-Mode Generation**

```rust
// In your Rust backend

enum GenerationMode {
    StrictVastu,      // All hard constraints, may fail
    FlexibleVastu,    // Soft constraints, always succeeds
}

impl Solver {
    fn solve(&self, mode: GenerationMode) -> Layout {
        match mode {
            StrictVastu => {
                // All Vastu rules as hard constraints
                // May return error if impossible
            },
            FlexibleVastu => {
                // Vastu rules as soft preferences
                // Always generates, shows violations
            }
        }
    }
}
```

---

## Recommended Reading Order

1. **Start:** HouseDiffusion (your foundation)
2. **Next:** Graph2Plan (relationship encoding)
3. **Then:** LayoutDM (constraint injection)
4. **Finally:** SceneScape (3D consistency), Instruct-NeRF2NeRF (editing)

---

## Your Unique Competitive Advantages

After analyzing these papers against your system:

1. **Vastu Integration** - None of these have it, you own this domain
2. **Triangular/Irregular Plots** - You handle, they don't
3. **BHK Expansion** - Indian context, they ignore
4. **Outdoor Fixture Separation** - Your two-phase approach is novel
5. **Conversational Refinement** - LLM-driven editing loop is unique
6. **Offline-First** - Privacy + no cloud costs

---

## Next Steps

**Phase 1 (Foundation):**
- Replace current solver with HouseDiffusion architecture
- Add discrete+continuous denoising branches
- Implement Vastu attention weights

**Phase 2 (Enhancement):**
- Add graph-based constraint encoding
- Implement two-phase indoor/outdoor solving
- Add BHK template expansion

**Phase 3 (Polish):**
- Add real-time Vastu compliance visualization
- Implement iterative refinement loop
- Add vector-direct CAD export

