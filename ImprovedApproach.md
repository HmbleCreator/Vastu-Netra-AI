# **Vastu Generative Framework: A Principled Approach for Compliant Layouts**

Version: 1.1 (Includes Math/Algo Details)  
Date: October 28, 2025

## **1\. Goal**

To develop a robust and innovative layout generation system for the Vastu Architect AI desktop application. This framework will produce architecturally sound and Vastu-compliant floor plans by:

1. Accurately interpreting diverse user inputs (plot descriptions, room requirements).  
2. Dynamically adapting Vastu principles to specific plot geometries.  
3. Synergizing fundamental Vastu principles with explicit, prioritized rules.  
4. Explicitly planning for circulation (Prana flow).  
5. Ensuring architectural coherence through iterative refinement.  
6. Generating direct vector outputs suitable for CAD export.  
7. Utilizing algorithms feasible for local desktop execution.

## **2\. Core Framework: 3-Step Process**

### **Step 1: Plot Definition & Geometric Analysis**

* **Objective:** Create a precise digital representation of the user's plot. **Accuracy is paramount.**  
* **How:**  
  * **Input Parsing (LLM \+ Logic):** Use LLM function calling (geometry\_prompts.py schema) to extract shape, dimensions, orientation. Implement validation logic and clarification dialogues for ambiguity. Convert units to feet.  
  * **Geometric Construction (Vector Representation):**  
    * Define plot as a polygon $P \= \\{v\_1, v\_2, ..., v\_n\\}$, where $v\_i \= (x\_i, y\_i)$ are vertex coordinates in counter-clockwise order.  
    * For special shapes (e.g., triangular), use geometric rules (plot.py, geometry\_utils.py) to calculate vertices from description (base, height, hypotenuse direction). Example: Right-angle triangle with base $b$, height $h$, hypotenuse West \-\> $v\_1=(0,0), v\_2=(b,0), v\_3=(0,h)$.  
  * **Shape Analysis (geometry\_analyzer.py, geometry\_utils.py):**  
    * **Area:** Shoelace formula: $A \= \\frac{1}{2} | \\sum\_{i=1}^{n} (x\_i y\_{i+1} \- x\_{i+1} y\_i) |$ (where $v\_{n+1}=v\_1$).  
    * **Centroid:** $C\_x \= \\frac{1}{6A} \\sum\_{i=1}^{n} (x\_i \+ x\_{i+1})(x\_i y\_{i+1} \- x\_{i+1} y\_i)$, $C\_y \= \\frac{1}{6A} \\sum\_{i=1}^{n} (y\_i \+ y\_{i+1})(x\_i y\_{i+1} \- x\_{i+1} y\_i)$.  
    * **Analysis:** Identify complexity, buildable zones (e.g., largest inscribed rectangle, polygon offsetting/insetting), concavities, narrow areas.  
* **Desired Outcome:** Validated plot\_polygon $P$, orientation $\\theta$, area $A$, centroid $C=(C\_x, C\_y)$, buildable\_zones (list of polygons).

### **Step 2: Vastu Potential Mapping (Fundamentals-Based)**

* **Objective:** Translate Vastu principles into a spatial map tailored to the plot geometry $P$.  
* **How:**  
  * **Map Rules to Fundamentals:** Associate rules in vastuRules.ts with principles (Agni SE, Isha NE, Stability SW, etc.).  
  * **Compute Potential Field(s):** For each key Vastu function type $k$ (e.g., kitchen, pooja, master bed), create a scalar field $\\Phi\_k(x, y)$ over the plot area.  
    * **Method 1 (Zone-based):** Define ideal Vastu zone centers $Z\_k$ (e.g., SE corner point relative to plot centroid $C$ and oriented axes). Calculate potential based on distance $d((x,y), Z\_k)$ and shape constraints. $\\Phi\_k(x, y) \= w\_k \\cdot f(d((x,y), Z\_k), \\text{plot shape}) \\cdot \\mathbb{I}((x,y) \\in P)$, where $w\_k$ is based on rule priority, $f$ is a decay function (e.g., Gaussian), and $\\mathbb{I}$ indicates point is inside the plot.  
    * **Method 2 (Grid-based Interpolation):** Define Vastu values at key points (corners, center) based on rules. Interpolate these values across a grid covering the plot.  
    * **Brahmasthan:** Explicitly set $\\Phi\_k(x, y)$ to a very low value (high penalty) near the plot centroid $C$ for construction-related functions $k$, based on rule V040.  
* **Desired Outcome:** One or more data structures (e.g., 2D NumPy arrays aligned with the plot's bounding box, masked by $P$) representing the Vastu potential $\\Phi\_k(x, y)$ for relevant room types $k$.

### **Step 3: Rule-Guided Placement, Circulation & Detailing**

* **Objective:** Position rooms, plan circulation, and generate architectural details respecting Vastu, user needs, and geometry.  
* **How (Sub-steps):**  
  * **A. Zone Prioritization:** Identify regions within $P$ where $\\Phi\_k(x, y)$ is high for each required room $k$.  
  * **B. Circulation Planning:**  
    * Represent key locations (entrance, living hub, bedroom areas) as nodes in a graph.  
    * Find shortest paths within $P$, avoiding the Brahmasthan penalty zone. Define corridor polygons along these paths with minimum width constraints. Add these corridors to the placement constraints.  
  * **C. Placement Algorithm (Choose one or hybrid):**  
    * **Agent-Based:**  
      * State: Agent $i$ has position $p\_i$, size $s\_i$, type $k\_i$.  
      * Forces: $F\_i \= F\_{vastu} \+ F\_{repel} \+ F\_{adj} \+ F\_{circ} \+ F\_{boundary}$.  
        * $F\_{vastu} \\propto \\nabla \\Phi\_{k\_i}(p\_i)$ (moves agent towards higher potential).  
        * $F\_{repel}$ pushes agents apart based on overlap area/distance.  
        * $F\_{adj}$ pulls preferred adjacent rooms closer.  
        * $F\_{circ}$ repels agents from predefined corridor polygons.  
        * $F\_{boundary}$ keeps agents within $P$.  
      * Simulate agent movement until equilibrium.  
    * **Enhanced SA:**  
      * State: Configuration of room parameters $X \= \\{ (x\_i, y\_i, w\_i, h\_i) \\}$.  
      * Energy Function: $E(X) \= \\sum w\_j E\_j$, where $E\_j$ are penalty terms:  
        * $E\_{overlap} \= \\sum\_{i \\neq j} \\text{Area}(R\_i \\cap R\_j)$.  
        * $E\_{vastu} \= \-\\sum\_{i} \\int\_{R\_i} \\Phi\_{k\_i}(x, y) dA \+ \\sum\_{i} \\text{Penalty}(\\text{RuleViolations}\_i)$. Calculate penalties based on vastuRules.ts priorities (Critical \= large finite penalty or constraint violation, High/Medium \= smaller penalty).  
        * $E\_{adjacency} \= \\sum\_{(i,j) \\in \\text{prefs}} \\| \\text{center}(R\_i) \- \\text{center}(R\_j) \\|^2$.  
        * $E\_{circulation} \= \\sum\_{i} \\text{Area}(R\_i \\cap \\text{Corridors})$.  
        * $E\_{boundary} \= \\sum\_{i} \\text{Area}(R\_i \\setminus P)$.  
      * Moves: Translate, resize, swap, rotate, Vastu-zone hop.  
      * Acceptance: $P(\\Delta E, T) \= \\exp(-\\Delta E / T)$.  
    * **Constraint Integration:**  
      * Hard Constraints (critical rules): Directly enforce during state generation or check validity (e.g., If type is Pooja, $p\_i$ must be in region where $\\Phi\_{pooja}$ is max). Reject invalid states/moves immediately or use large penalties in SA.  
      * Soft Constraints (high/medium rules): Incorporate into SA energy $E\_{vastu}$ with weights based on priority, or use in Agent forces $F\_{vastu}$.  
  * **D. Detailing (Vector Output):**  
    * **Rooms:** Final output of placement is typically room polygons $R\_i \= \\{v\_{i,1}, ..., v\_{i,m}\\}$.  
    * **Walls:** Compute wall segments $W\_{ij}$ by finding shared edges between adjacent room polygons $R\_i, R\_j$. Perform polygon offsetting/clipping for exterior walls relative to $P$. Merge collinear segments.  
    * **Doors:** Identify adjacent rooms $(i,j)$ needing connection. Find intersection of $R\_i, R\_j$ (shared wall $W\_{ij}$). Place door $D\_{ij}$ as a line segment on $W\_{ij}$ respecting rules (V002) and circulation.  
    * **Windows:** Identify exterior wall segments $W\_{i,\\text{ext}}$. Place windows $Win\_k$ based on rules (V031, V032), room type, and segment length/orientation.  
  * **E. Feedback Loop:**  
    * Define coherence score $S\_{coherence}$ (e.g., sum of wall alignment penalties, corridor width violations, door access checks).  
    * If $S\_{coherence} \< \\tau\_{threshold}$: Calculate adjustment $\\Delta X$ for room parameters $X$ (e.g., based on gradient $-\\nabla\_X S\_{coherence}$ if differentiable, or heuristic shifts). Apply $\\Delta X$, go back to (C) or (D) for refinement.  
* **Desired Outcome:** Vector data: List\[Room{id, type, polygon\_vertices}\], List\[WallSegment{start, end}\], List\[Door{position, wall\_segment\_id}\], List\[Window{position, wall\_segment\_id}\].

## **3\. Hierarchy (Future Consideration)**

Apply Steps 1-3 recursively. Define macro-zones $M\_j \\subset P$. Solve for placement of $M\_j$. Then, for each $M\_j$, treat it as a new plot and apply Steps 1-3 within it to place rooms $R\_i$.

## **4\. Key Innovations & Benefits**

* **Shape Adaptability:** Vastu principles applied intelligently via potential map $\\Phi\_k(x, y)$ derived from plot $P$.  
* **Principled Design:** Synergizes fundamentals ($\\Phi\_k$) with specific rules (vastuRules.ts) for placement guidance and constraints.  
* **Integrated Circulation:** Circulation planned explicitly, influencing placement.  
* **Architectural Coherence:** Feedback loop refines geometry for practical wall/door layouts.  
* **Desktop Feasibility:** Focuses on algorithms (Agents, SA, Neuro-Symbolic) suitable for local CPU execution.  
* **Direct Vector Output:** Generates CAD-ready vector data.