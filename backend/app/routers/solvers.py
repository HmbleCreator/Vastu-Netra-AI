from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import sys
import os

# Import solver entry points
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solvers.graph_solver import SolverRequest as GraphSolverRequest, solve_floor_plan as graph_solve
from solvers.constraint_solver import SolverRequest as ConstraintSolverRequest, solve_floor_plan as constraint_solve

router = APIRouter()

class Room(BaseModel):
    id: str
    name: str
    type: str
    width: float
    height: float
    x: Optional[float] = None
    y: Optional[float] = None
    direction: Optional[str] = None
    color: Optional[str] = None

class GenerationRequest(BaseModel):
    rooms: List[Dict[str, Any]]
    plotWidth: float = Field(30.0, gt=0)
    plotLength: float = Field(30.0, gt=0)
    plotShape: str = "rectangular"
    constraints: Optional[Dict[str, Any]] = None
    solver_type: str = "graph"  # "graph" or "constraint"
    seed: Optional[int] = None

class GenerationResponse(BaseModel):
    rooms: List[Room]
    success: bool
    message: str
    score: Optional[float] = None
    solver_type: Optional[str] = None
    warnings: Optional[List[str]] = None

@router.post("/generate", response_model=GenerationResponse)
async def generate_floor_plan(request: GenerationRequest):
    """Generate a floor plan using the selected solver."""
    try:
        # Prepare solver-specific request and call solver
        if request.solver_type == "graph":
            solver_req = GraphSolverRequest(
                rooms=request.rooms,
                plot_width=request.plotWidth,
                plot_length=request.plotLength,
                plot_shape=request.plotShape,
                constraints=request.constraints,
                seed=request.seed,
            )
            result = graph_solve(solver_req)
        elif request.solver_type == "constraint":
            solver_req = ConstraintSolverRequest(
                rooms=request.rooms,
                plot_width=request.plotWidth,
                plot_length=request.plotLength,
                plot_shape="rectangular",
                constraints=request.constraints,
                seed=request.seed,
            )
            result = constraint_solve(solver_req)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown solver type: {request.solver_type}")

        rooms = [
            Room(
                id=r.id,
                name=r.name,
                type=r.type,
                width=r.width or 0,
                height=r.height or 0,
                x=r.x or 0,
                y=r.y or 0,
                direction=r.direction,
            )
            for r in result.rooms
        ]

        return GenerationResponse(
            rooms=rooms,
            success=True,
            message="Floor plan generated successfully",
            score=getattr(result, "score", None),
            solver_type=getattr(result, "solver_type", None),
            warnings=getattr(result, "warnings", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")