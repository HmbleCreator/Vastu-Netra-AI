# Vastu Netra AI

**Vastu Netra AI** is an intelligent, Vastu-compliant floor plan generator that combines modern architectural constraints with ancient Indian design principles (Vastu Shastra). It features an interactive conversational interface that allows users to generate, visualize, and modify floor plans in real-time.

<img width="2879" height="1567" alt="Screenshot 2025-12-25 151615" src="https://github.com/user-attachments/assets/70e43ba0-c769-4b51-a12a-8bf12f9237e7" />

## Key Features

- **Interactive Conversational AI**: Chat naturally with the AI to design your home ("Design a 3BHK", "Move the kitchen to SE").
- **VGF-SA Solver**: Powered by a custom **Vastu-aware Graph Framework with Simulated Annealing** that achieves ~94% compliance scores (vs 45% for standard graph solvers).
- **Real-time Visualization**: Instantly view generated 2D floor plans and 3D mockups.
- **Smart Fallback**: Automatically switches between fast graph-based generation and robust constraint-based optimization.
- **Vastu Compliance Scoring**: Detailed scoring for every room placement (e.g., Agni corner for Kitchen, Nairutya for Master Bedroom).

---

## Architecture

The system consists of three main components:

1.  **Frontend (React + TypeScript)**: specialized UI for chat and floor plan rendering.
2.  **AI Engine (Ollama/LLM)**: Parses natural language, manages conversation context, and calls solver tools.
3.  **Backend (FastAPI + Python)**: Hosts the VGF-SA solver and graph algorithms to generate coordinate geometry.

---

## VGF-SA Workflow

The core magic happens in our **Vastu-aware Graph Framework with Simulated Annealing (VGF-SA)** solver:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VGF-SA SOLVER WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

  USER INPUT                          VASTU MAPS                    
      │                                   │                         
      ▼                                   ▼                         
┌──────────────┐                  ┌───────────────────┐            
│ Plot Size    │                  │ NE → Pooja/Living │            
│ BHK Config   │──────────────────│ SE → Kitchen      │            
│ Orientation  │                  │ SW → Master Bed   │            
└──────────────┘                  │ NW → Bathroom     │            
      │                           └───────────────────┘            
      │                                   │                         
      └─────────────┬─────────────────────┘                         
                    ▼                                               
         ┌──────────────────────┐                                   
         │   CONSTRAINT GRAPH   │                                   
         │  ├─ Adjacency Rules  │                                   
         │  ├─ No Overlaps      │                                   
         │  ├─ Stay in Bounds   │                                   
         │  └─ Aspect Ratios    │                                   
         └──────────────────────┘                                   
                    │                                               
                    ▼                                               
         ┌──────────────────────┐                                   
         │ SIMULATED ANNEALING  │◄─────────────┐                    
         │  1. Random Start     │              │                    
         │  2. Calculate Score  │              │ Repeat until       
         │  3. Perturb Rooms    │              │ converged          
         │  4. Accept/Reject    │──────────────┘                    
         │  5. Cool Down        │                                   
         └──────────────────────┘                                   
                    │                                               
                    ▼                                               
         ┌──────────────────────┐                                   
         │   SCORING FUNCTION   │                                   
         │  Vastu Score (94%)   │                                   
         │  - Overlap Penalty   │                                   
         │  - Boundary Penalty  │                                   
         └──────────────────────┘                                   
                    │                                               
                    ▼                                               
         ┌──────────────────────┐                                   
         │       OUTPUT         │                                   
         │  Optimized Layout    │                                   
         │  Room Positions      │                                   
         │  Vastu Compliance    │                                   
         └──────────────────────┘                                   
```

---

## Installation & Setup

### Prerequisites
- Node.js & npm
- Python 3.8+
- [Ollama](https://ollama.com/) (running locally)

### 1. Backend Setup (Solver Engine)
 Navigate to the backend directory and start the FastAPI server:

```bash
cd backend
# Create virtual env (optional but recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup (UI)
In a new terminal, start the React application:

```bash
cd . # Root directory
npm install
npm run dev
```

### 3. LLM Setup
Ensure Ollama is running effectively. The application defaults to `gpt-oss:20b-cloud`, but you can configure this in the UI settings.

```bash
# Ensure ollama is serving
ollama serve
```

---

## Usage Guide

1.  **Open the App**: Go to `http://localhost:8080`.
2.  **Start Designing**: Type a request like:
    > "Design a 4BHK home in 600 sq m area facing North"
3.  **Refine**: Interactive with the chatbot to modify the layout:
    - *"Move the master bedroom to the Southwest"*
    - *"Add a large Pooja room"*
    - *"Make the living room bigger"*
4.  **Visualize**: Toggle between **2D** and **3D** tabs to see the layout.

---

## License
APACHE 2.0 License. Built with love for Vastu Shastra & AI.
