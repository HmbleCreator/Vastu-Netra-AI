# Vastu Architect AI - Product Requirements Document

**Version:** 2.0  
**Target Platforms:** Lovable.dev / Bolt.new  
**Last Updated:** October 2025

---

## Executive Summary

Vastu Architect AI is an intelligent design assistant that generates professional house floor plans through natural conversation. Users describe what they want ("Design a 3BHK house on an east-facing plot with good natural light"), and the system generates complete architectural layouts that respect traditional Vastu Shastra principles while meeting modern engineering standards.

**Core Value Proposition:** Replace weeks of back-and-forth with architects with a 5-minute conversation that produces professional-grade floor plans, complete with Vastu compliance scores and export-ready CAD files.

---

## What We're Building

### The Complete System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│  "Design a 3BHK house on 2000 sqft plot, kitchen facing north"  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CHAT INTERFACE (Frontend)                      │
│  • Clean conversation UI (like ChatGPT)                          │
│  • Real-time message streaming                                   │
│  • Interactive 2D/3D floor plan viewer                           │
│  • Export buttons (PDF, DXF, SVG, JSON)                          │
│  • Design adjustment controls                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              LLM ORCHESTRATOR (Backend Brain)                    │
│  • Understands user intent from natural language                 │
│  • Extracts design parameters (area, rooms, constraints)         │
│  • Decides which layout generator to use                         │
│  • Calls layout generation tools                                 │
│  • Interprets results back to user in plain English              │
│  • Maintains conversation context                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│               LAYOUT GENERATION TOOLS                            │
│                                                                   │
│  [Graph Solver]          [Hybrid Solver]                         │
│  Fast physics-based  →   Tries both approaches →  Best result   │
│  ~1-2 seconds           picks highest quality                    │
│                                                                   │
│  [Constraint Solver]                                             │
│  Mathematical optimizer                                          │
│  ~25-35 seconds (fallback)                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  VALIDATION SERVICES                             │
│  • Vastu Compliance Engine (scores 0-100%)                       │
│  • Structural Feasibility Checker                                │
│  • Export Generation (PDF/DXF/SVG/JSON)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FINAL OUTPUT                                  │
│  • Professional floor plan (vector graphics)                     │
│  • Vastu compliance report with suggestions                      │
│  • Structural feasibility assessment                             │
│  • Multiple export formats ready for architects                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## How It Works: User Journey

### Step 1: Initial Conversation
**User:** "I want to design a house on a 2000 square feet plot facing east. I need 3 bedrooms, a modern kitchen, and good Vastu compliance."

**System thinks:**
- Parse intent: New house design
- Extract parameters: 2000 sqft, east-facing, 3 bedrooms, kitchen, Vastu priority
- Estimate plot dimensions from area
- Set Vastu school to "modern" (user said "good compliance")

**LLM responds:** "I'll design a 3-bedroom house for your 2000 sqft east-facing plot with Vastu principles. Should the kitchen face north or east? Any preference for the master bedroom location?"

### Step 2: Refinement
**User:** "Kitchen should face north. Master bedroom in southwest corner please."

**System thinks:**
- Additional constraints: kitchen_north = true, master_bedroom_southwest = true
- Ready to generate
- Use hybrid solver (safest for first generation)

**LLM calls tool:** `generate_layout_hybrid(total_area=2000, orientation="east", ...)`

**System generates layout in 2 seconds**

### Step 3: Presentation
**LLM responds with:**
```
✓ Design complete! Here's your layout:

📐 Layout Details:
   • Kitchen (150 sqft) - Faces North ✓
   • Living Room (350 sqft) - Natural light from East
   • Master Bedroom (220 sqft) - Southwest corner ✓
   • Bedroom 2 (180 sqft) - North side
   • Bedroom 3 (170 sqft) - East side
   • 2 Bathrooms (60 sqft each)

🕉️ Vastu Compliance: 94%
   ✓ Kitchen orientation perfect
   ✓ Master bedroom placement ideal
   ⚠ Minor: Living room could be slightly more central

🏗️ Structural Score: 87/100
   ✓ All spans within safe limits
   ✓ Good wall distribution
   
[View 2D Floor Plan] [View 3D Model] [Download Files]

Would you like to adjust anything?
```

### Step 4: Iteration
**User:** "Can you make the living room bigger?"

**System thinks:**
- Modification request
- Target: living room
- Action: resize (increase)

**LLM calls tool:** `adjust_room(room_id="living", adjustment="resize", increase_by=10%)`

**System regenerates affected areas**

**LLM:** "Done! Living room is now 385 sqft (increased from 350). I slightly reduced Bedroom 2 to make space. Vastu score is still 94%. Better?"

### Step 5: Export
**User:** "Perfect! Can I download this?"

**LLM:** "Absolutely! Your design is ready in 4 formats:

📄 **PDF Report** - Complete with floor plan, Vastu analysis, and structural notes. Share with your architect.

📐 **DXF File** - Professional CAD format. Open in AutoCAD, Revit, or any CAD software for detailed refinement.

🖼️ **SVG Floor Plan** - Web-friendly vector graphic. Easy to view and share online.

📊 **JSON Data** - Complete design data for future editing or integration.

[Download All] [Email to Architect]"

---

## Technical Architecture

### Frontend (React + TypeScript)

**Main Components:**

1. **Chat Interface**
   - Message list with user/assistant bubbles
   - Input field with send button
   - Real-time streaming (WebSocket connection)
   - Typing indicators
   - Message history

2. **Design Viewer**
   - 2D floor plan (SVG rendering)
   - 3D walkthrough (Three.js/React Three Fiber)
   - Toggle between views
   - Pan, zoom, rotate controls
   - Room labels and dimensions overlay

3. **Score Cards**
   - Vastu Compliance card (percentage, status indicator)
   - Structural Feasibility card (pass/warning/fail)
   - Detailed breakdowns on click

4. **Export Panel**
   - Four download buttons (PDF, DXF, SVG, JSON)
   - Preview thumbnails
   - Copy shareable link option

**Tech Stack:**
- React 18 with TypeScript
- Tailwind CSS for styling
- Three.js for 3D visualization
- WebSocket for real-time chat
- Axios for HTTP requests

---

### Backend (Python FastAPI)

**Core Services:**

1. **LLM Orchestrator Service**
   - Runs Mistral 7B locally via Ollama
   - Function calling / tool use capability
   - Maintains conversation context per session
   - Routes user intent to appropriate tools
   - Formats technical results into natural language

2. **Layout Generation Tools**
   
   **Graph-Based Solver:**
   - Uses physics simulation (force-directed layout)
   - Rooms are nodes, adjacencies are edges
   - Attractive/repulsive forces position rooms
   - Fast: 1-2 seconds for typical 3-5 bedroom house
   - Works well for standard layouts
   
   **Constraint Solver (Fallback):**
   - Uses mathematical optimization (OR-Tools)
   - Guarantees no overlaps, exact constraints
   - Slower: 25-35 seconds
   - Used when graph solver can't find good solution
   
   **Hybrid Approach:**
   - Tries graph solver first (fast)
   - Falls back to constraint solver if needed
   - Compares quality scores
   - Returns best result
   - Has grid fallback if both fail (always succeeds)

3. **Vastu Compliance Engine**
   - Database of 40+ Vastu rules from classical texts
   - Three tradition modes: Classical, Modern, Mayamata
   - Scores each rule (satisfied/violated)
   - Weighted scoring system
   - Generates specific suggestions
   - Supports multiple strictness levels

4. **Structural Validation Service**
   - Rule-based feasibility checks
   - Verifies room dimensions are practical
   - Checks span lengths (no room >20ft wide without support)
   - Ensures adequate wall distribution
   - Validates door/window placement
   - Returns pass/warning/risk status

5. **Export Service**
   - PDF: 3-4 page report with floor plan, analysis, disclaimers
   - DXF: CAD-compatible vector format
   - SVG: Web-viewable vector graphic
   - JSON: Complete data for re-editing

**Tech Stack:**
- Python 3.11+
- FastAPI for API framework
- Ollama + Mistral 7B for LLM
- NetworkX for graph algorithms
- NumPy for physics simulation
- OR-Tools for constraint solving
- ReportLab for PDF generation
- WebSocket support for real-time chat

---

## Data Flow: Complete Request Cycle

### User Input → Final Output

```
1. USER TYPES MESSAGE
   "Design a 3BHK with north-facing kitchen"
   
2. FRONTEND SENDS VIA WEBSOCKET
   { session_id: "abc123", message: "..." }
   
3. BACKEND LLM ORCHESTRATOR RECEIVES
   - Loads conversation history for session
   - Sends to Mistral LLM with tool definitions
   
4. LLM ANALYZES & DECIDES
   - Intent: Generate new layout
   - Parameters: 3BHK, kitchen_north=true
   - Tool to use: generate_layout_hybrid
   
5. LLM CALLS TOOL (Function Call)
   generate_layout_hybrid({
     total_area: 2000,
     rooms_needed: ["kitchen", "living", "master_bedroom", 
                    "bedroom_2", "bedroom_3", "bathroom_1", "bathroom_2"],
     vastu_constraints: { kitchen_north: true },
     ...
   })
   
6. HYBRID SOLVER EXECUTES
   - Tries graph solver → Success in 1.2s
   - Skips constraint solver (graph was good enough)
   - Returns LayoutData object
   
7. VALIDATION SERVICES RUN
   - Vastu engine: 92% compliance
   - Structural checker: Pass (score 0.85)
   
8. TOOL RETURNS RESULT TO LLM
   {
     status: "success",
     vastu_score: 92,
     structural_score: 85,
     rooms: [...],
     ...
   }
   
9. LLM INTERPRETS & RESPONDS
   "I've designed a 3BHK layout for you! 
    Kitchen faces north as requested.
    Vastu compliance: 92%
    [Details...]"
   
10. FRONTEND RECEIVES RESPONSE
    - Displays LLM message in chat
    - Renders floor plan in viewer
    - Shows score cards
    - Enables export buttons
```

---

## Key Features & Capabilities

### 1. Natural Language Understanding
- Parse intent from conversational input
- Handle variations ("3BHK" = "3 bedroom house" = "3 bedrooms and hall kitchen")
- Extract implicit constraints ("modern family" → likely needs living room)
- Maintain context across conversation

### 2. Intelligent Layout Generation
- **Fast first attempt** (graph solver ~1-2s)
- **Guaranteed success** (hybrid fallback system)
- **Quality optimization** (picks best among multiple attempts)
- **Vastu-native** (rules embedded in generation, not added later)

### 3. Vastu Compliance
- **40+ rules** covering all major principles
- **Three traditions**: Classical (strict), Modern (practical), Mayamata (South Indian)
- **Weighted scoring** (critical rules count more)
- **Actionable suggestions** (not just "bad", but "move kitchen 3ft north")
- **Flexible strictness** (strict/moderate/flexible modes)

### 4. Real-Time Iteration
- Modify existing designs without full regeneration
- "Make kitchen bigger" → adjusts room, re-validates, responds
- "Move bedroom to the left" → shifts position, checks constraints
- "Can you improve Vastu score?" → identifies violations, suggests fixes

### 5. Professional Outputs
- **PDF Report**: Printable, shareable with family/architect
- **DXF File**: Import into AutoCAD, Revit, ArchiCAD for professional refinement
- **SVG Plan**: Embed in websites, presentations, proposals
- **JSON Data**: Re-import for future editing, version control

### 6. Visual Exploration
- **2D Floor Plan**: Clear, labeled, dimensioned
- **3D Walkthrough**: Navigate through the house, get spatial sense
- **Toggle views**: Switch between 2D and 3D instantly
- **Interactive**: Click rooms for details, hover for tooltips

---

## What It Does NOT Do (Scope Boundaries)

### Out of Scope for MVP:
❌ Multi-story buildings (future: Phase 2)  
❌ Irregular plot shapes (supports rectangular plots only)  
❌ Structural engineering calculations (FEA, load analysis)  
❌ Building code compliance verification (local regulations vary)  
❌ Material cost estimation  
❌ Interior design / furniture placement  
❌ Landscape design beyond basic garden zones  
❌ 3D rendering with photorealistic materials  
❌ VR/AR visualization  

### Clear Disclaimers:
The system makes this clear to users:
> "This is a preliminary design tool. Before construction:
> 1. Hire a licensed architect to refine the design
> 2. Hire a structural engineer for load analysis
> 3. Verify local building codes and get permits
> 4. Consult a Vastu expert if strict compliance is critical"

---

## Success Metrics

### Technical Performance:
- **Response time**: <3 seconds for initial generation
- **Vastu accuracy**: 90%+ compliance for well-constrained designs
- **Success rate**: 99%+ (hybrid + fallback ensures always generates something)
- **Uptime**: 99.5%+

### User Experience:
- **Time to first floor plan**: <2 minutes from conversation start
- **Iterations per design**: Average 2-3 adjustments before satisfaction
- **Export rate**: 70%+ of generated designs get exported

### Business Goals (Phase 2):
- 1,000+ designs generated in first 3 months
- 50+ architects signing up for premium API access
- 10+ developer partnerships for API integration

---

## Implementation Phases

### Phase 1: MVP (8 weeks)
- Chat interface with LLM orchestrator
- Graph-based layout solver (primary)
- Hybrid approach with fallback
- Vastu compliance engine (15 core rules)
- Basic structural validation
- PDF + SVG export
- 2D floor plan viewer
- Rectangular plots only
- Single-story buildings

### Phase 2: Enhanced (Months 4-6)
- 40+ Vastu rules (complete database)
- 3D walkthrough viewer
- DXF + JSON export
- Room adjustment without regeneration
- Irregular plot shapes support
- Landscape zones
- User accounts & design history
- Premium API for developers

### Phase 3: Professional (Months 7-12)
- Multi-story buildings
- Material cost estimation
- Building code checker (major Indian cities)
- Architect collaboration features
- White-label options
- Mobile apps (iOS/Android)
- AR preview via phone camera

---

## Technology Choices & Rationale

### Why Mistral 7B (via Ollama)?
- **Local inference**: Privacy (designs never leave your server)
- **Function calling**: Native support for tool use
- **Good balance**: Smart enough for intent understanding, fast enough for real-time chat
- **Cost**: Free, no API fees

### Why Graph-Based Solver?
- **Fast**: Physics simulation converges in seconds
- **Intuitive**: Relationships (adjacencies) are natural to express
- **Vastu-friendly**: Directional forces map perfectly to Vastu zones
- **Avoids type errors**: Uses Python native types (no constraint variable complexity)

### Why Hybrid Approach?
- **Best of both worlds**: Speed + correctness
- **Always succeeds**: Multiple fallback layers
- **Adaptive**: Learns which solver works for which layouts

### Why WebSocket for Chat?
- **Real-time**: Streaming responses (better UX)
- **Bidirectional**: Server can push updates
- **Connection reuse**: Less overhead than HTTP polling

---

## Deployment Architecture

### Development:
```
Local Machine:
  - Frontend: Vite dev server (http://localhost:5173)
  - Backend: Uvicorn (http://localhost:8000)
  - LLM: Ollama (http://localhost:11434)
  - Database: SQLite
```

### Production (Simple):
```
Single Server (AWS EC2 / DigitalOcean):
  - Nginx (reverse proxy)
  - Frontend (React build served by Nginx)
  - Backend (FastAPI via Gunicorn)
  - Ollama (Mistral 7B)
  - PostgreSQL
```

### Production (Scalable - Phase 2):
```
- Frontend: Vercel / Netlify CDN
- Backend: AWS ECS / Kubernetes (multiple replicas)
- LLM: Dedicated GPU instance (for faster inference)
- Database: AWS RDS PostgreSQL
- File Storage: S3 for exports
- Cache: Redis for session management
```

---

## Risk Mitigation

### Risk: LLM Hallucination
**Mitigation:**
- Constrain LLM to only use defined tools
- Validate all tool parameters before execution
- Show technical data alongside LLM responses (users can verify)

### Risk: Solver Timeout/Failure
**Mitigation:**
- Hybrid approach with multiple solvers
- Grid fallback always succeeds
- Time limits on each solver attempt

### Risk: Poor Vastu Compliance
**Mitigation:**
- Embed Vastu as constraints in generation (not post-check)
- Multiple strictness levels (users choose trade-offs)
- Clear explanations of violations

### Risk: Legal Liability
**Mitigation:**
- Strong disclaimers in every export
- Clear messaging: "Preliminary design, not construction-ready"
- Recommend professional review
- Terms of service limiting liability

---

## MVP User Stories

1. **As a homeowner**, I want to describe my house needs in plain English and get a floor plan in minutes, so I can explore design options quickly.

2. **As a Vastu-conscious buyer**, I want the system to automatically generate Vastu-compliant layouts, so I don't need to hire separate consultants.

3. **As an architect**, I want to download DXF files of AI-generated layouts, so I can refine them in my CAD software instead of starting from scratch.

4. **As a user uncertain about design**, I want to iterate ("make kitchen bigger", "move bedroom left"), so I can explore variations easily.

5. **As a developer**, I want an API to batch-generate layouts, so I can integrate this into my real-estate platform.

---

## Final Deliverables (MVP)

### For Users:
- Web application (desktop browser)
- Chat-based interface
- 2D floor plan viewer
- Vastu compliance report
- Structural feasibility assessment
- PDF + SVG export

### For Developers:
- REST API for design generation
- WebSocket API for real-time chat
- API documentation (Swagger/OpenAPI)
- Example integrations

### For Business:
- Usage analytics dashboard
- Design history per user
- Export tracking
- Performance metrics

---

## Conclusion

Vastu Architect AI transforms the traditional house design process by combining:
1. **AI conversation** for natural user interaction
2. **Intelligent layout generation** with multiple solving approaches
3. **Cultural sensitivity** through embedded Vastu principles
4. **Professional outputs** ready for architect refinement

The result: What used to take 4-6 weeks and ₹2-5 lakhs now takes 5 minutes and costs nothing (freemium model). The system doesn't replace architects—it empowers them and democratizes access to good design.

**Next Step:** Build MVP in Lovable.dev or Bolt.new using this PRD as the specification.