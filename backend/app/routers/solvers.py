from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
import time

# Import solver entry points using absolute package imports to preserve correct
# package context. Relative imports or manipulating sys.path can cause
# "attempted relative import beyond top-level package" when uvicorn loads
# this module via the package path.
from backend.app.solvers.graph_solver import SolverRequest as GraphSolverRequest, solve_floor_plan as graph_solve
from backend.app.solvers.constraint_solver import SolverRequest as ConstraintSolverRequest, solve_floor_plan as constraint_solve

router = APIRouter()
logger = logging.getLogger(__name__)

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
    # Optional explicit polygon and metadata (snake/camel tolerances handled by router)
    plotPolygon: Optional[List[List[float]]] = None
    orientation: Optional[Dict[str, Any]] = None
    outdoorFixtures: Optional[List[str]] = None
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
        t0 = time.time()
        logger.info(
            "[generate] request received: rooms=%d, plot=(%s, %s, shape=%s), solver=%s",
            len(request.rooms or []), request.plotWidth, request.plotLength, request.plotShape, request.solver_type
        )
        if request.constraints:
            logger.debug("[generate] constraints: %s", request.constraints)
        if request.plotPolygon:
            logger.debug("[generate] plotPolygon vertices: %d", len(request.plotPolygon))
        if request.orientation:
            logger.debug("[generate] orientation: %s", request.orientation)
        # Prepare solver-specific request and call solver
        if request.solver_type == "graph":
            solver_req = GraphSolverRequest(
                rooms=request.rooms,
                plot_width=request.plotWidth,
                plot_length=request.plotLength,
                plot_shape=request.plotShape,
                plot_polygon=request.plotPolygon or (request.constraints or {}).get("plot_polygon"),
                orientation=request.orientation or (request.constraints or {}).get("orientation"),
                outdoor_fixtures=request.outdoorFixtures or (request.constraints or {}).get("outdoor_fixtures"),
                constraints=request.constraints,
                seed=request.seed,
            )
            logger.info("[generate] invoking graph solver")
            result = graph_solve(solver_req)
            logger.info("[generate] graph solver finished")
        elif request.solver_type == "constraint":
            solver_req = ConstraintSolverRequest(
                rooms=request.rooms,
                plot_width=request.plotWidth,
                plot_length=request.plotLength,
                plot_shape=request.plotShape,
                plot_polygon=request.plotPolygon or (request.constraints or {}).get("plot_polygon"),
                orientation=request.orientation or (request.constraints or {}).get("orientation"),
                outdoor_fixtures=request.outdoorFixtures or (request.constraints or {}).get("outdoor_fixtures"),
                constraints=request.constraints,
                seed=request.seed,
            )
            logger.info("[generate] invoking constraint solver")
            result = constraint_solve(solver_req)
            logger.info("[generate] constraint solver finished")
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

        resp = GenerationResponse(
            rooms=rooms,
            success=True,
            message="Floor plan generated successfully",
            score=getattr(result, "score", None),
            solver_type=getattr(result, "solver_type", None),
            warnings=getattr(result, "warnings", []),
        )
        logger.info(
            "[generate] success: rooms=%d, time=%.2fs, score=%s, solver=%s",
            len(resp.rooms), time.time() - t0, str(resp.score), str(resp.solver_type)
        )
        return resp
    except Exception as e:
        logger.exception("[generate] error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")