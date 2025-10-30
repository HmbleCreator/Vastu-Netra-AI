"""
OR-Tools CP-SAT based constraint solver scaffold.

This module provides a best-effort implementation that builds a small integer grid model
and enforces non-overlap and boundary constraints. If ortools is not installed, the
module raises an informative error.

Notes:
- Coordinates are converted to integer centimeters for CP-SAT.
- This is a pragmatic, lightweight formulation suitable for small layouts.
"""
from typing import List, Dict, Any
import math
import logging

logger = logging.getLogger(__name__)

try:
    from ortools.sat.python import cp_model
except Exception as e:
    cp_model = None


def _to_cm(value_m: float) -> int:
    return max(0, int(round(value_m * 100)))


def _to_m(value_cm: int) -> float:
    return float(value_cm) / 100.0


def solve_floor_plan(request) -> Dict[str, Any]:
    """Solve floor plan using OR-Tools CP-SAT.

    Args:
        request: object with attributes rooms (list of dicts), plot_width, plot_length

    Returns:
        dict-like response similar to other solvers: {"rooms": [...], "score": x, "iterations": 0}
    """
    if cp_model is None:
        raise RuntimeError("OR-Tools is not installed. Install with: pip install ortools")

    rooms = request.rooms
    plot_w_cm = _to_cm(request.plot_width)
    plot_h_cm = _to_cm(request.plot_length)

    n = len(rooms)
    model = cp_model.CpModel()

    # Vars
    x_vars = []
    y_vars = []
    w_cm = []
    h_cm = []

    for r in rooms:
        w = _to_cm(r.get("width", max(1.0, request.plot_width / 10)))
        h = _to_cm(r.get("height", max(1.0, request.plot_length / 10)))
        w_cm.append(w)
        h_cm.append(h)

        x = model.NewIntVar(0, max(0, plot_w_cm - w), f"x_{r['id']}")
        y = model.NewIntVar(0, max(0, plot_h_cm - h), f"y_{r['id']}")
        x_vars.append(x)
        y_vars.append(y)

    # Non-overlap constraints (disjunctive with booleans)
    for i in range(n):
        for j in range(i + 1, n):
            b0 = model.NewBoolVar(f"sep_x_i{ i }_j{ j }_0")
            b1 = model.NewBoolVar(f"sep_x_i{ i }_j{ j }_1")
            b2 = model.NewBoolVar(f"sep_y_i{ i }_j{ j }_2")
            b3 = model.NewBoolVar(f"sep_y_i{ i }_j{ j }_3")

            # If b0 true -> x_i + w_i <= x_j
            model.Add(x_vars[i] + w_cm[i] <= x_vars[j]).OnlyEnforceIf(b0)
            model.Add(x_vars[j] + w_cm[j] <= x_vars[i]).OnlyEnforceIf(b1)
            model.Add(y_vars[i] + h_cm[i] <= y_vars[j]).OnlyEnforceIf(b2)
            model.Add(y_vars[j] + h_cm[j] <= y_vars[i]).OnlyEnforceIf(b3)

            # At least one separation must hold
            model.AddBoolOr([b0, b1, b2, b3])

    # Boundary constraints already enforced by var bounds

    # Soft objective: encourage placement near plot center (manhattan distance)
    center_x = plot_w_cm // 2
    center_y = plot_h_cm // 2
    dist_vars = []
    for i in range(n):
        dx = model.NewIntVar(0, plot_w_cm, f"dx_{i}")
        dy = model.NewIntVar(0, plot_h_cm, f"dy_{i}")
        model.AddAbsEquality(dx, x_vars[i] - center_x)
        model.AddAbsEquality(dy, y_vars[i] - center_y)
        dist_vars.append(dx)
        dist_vars.append(dy)

    # objective: minimize sum of distances (heuristic)
    model.Minimize(sum(dist_vars))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0
    solver.parameters.num_search_workers = 8
    solver.parameters.maximize = False

    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result_rooms = []
        for idx, r in enumerate(rooms):
            x_cm = solver.Value(x_vars[idx])
            y_cm = solver.Value(y_vars[idx])
            result_rooms.append({
                "id": r["id"],
                "name": r.get("name", r["id"]),
                "type": r.get("type", ""),
                "x": _to_m(x_cm),
                "y": _to_m(y_cm),
                "width": _to_m(w_cm[idx]),
                "height": _to_m(h_cm[idx])
            })

        return {
            "rooms": result_rooms,
            "score": 0.0,
            "iterations": 0,
            "solver": "ortools",
            "status": solver.StatusName(status)
        }
    else:
        raise RuntimeError(f"OR-Tools solver failed to find a solution: {solver.StatusName(status)}")
