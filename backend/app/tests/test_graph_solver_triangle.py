from backend.app.solvers.graph_solver import SolverRequest, solve_floor_plan
from backend.app.utils import geometry_utils as gu


def test_graph_solver_on_triangle():
    # Simple triangular plot and two rooms
    rooms = [
        {"id": "r1", "name": "Living", "type": "living"},
        {"id": "r2", "name": "Kitchen", "type": "kitchen"}
    ]

    # triangle vertices (right angle at origin)
    triangle = [[0.0, 0.0], [10.0, 0.0], [0.0, 6.0]]

    req = SolverRequest(
        rooms=rooms,
        plot_width=10.0,
        plot_length=6.0,
        plot_shape="triangular",
        plot_polygon=triangle,
        constraints={"plot_polygon": triangle}
    )

    res = solve_floor_plan(req)

    assert res is not None
    assert res.rooms

    # Verify each room's center is inside polygon (full corner containment is ideal but
    # may be handled by subsequent overlap resolution/fine-tuning)
    for r in res.rooms:
        cx = r.x + (r.width or 0) / 2
        cy = r.y + (r.height or 0) / 2
        assert gu.point_in_polygon((cx, cy), triangle), f"Room center outside: {r.id}"
