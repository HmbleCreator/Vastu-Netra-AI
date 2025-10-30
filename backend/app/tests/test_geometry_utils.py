import pytest
from backend.app.utils import geometry_utils as gu


def test_triangle_centroid_and_inradius():
    # Right triangle with points (0,0), (4,0), (0,3)
    tri = [[0,0],[4,0],[0,3]]
    centroid = gu.calculate_polygon_centroid(tri)
    area = gu.calculate_polygon_area(tri)
    inradius = gu.calculate_polygon_inradius(tri)

    # Area should be 6 (4*3/2)
    assert pytest.approx(area, rel=1e-6) == 6.0

    # Centroid for right triangle at ( (0+4+0)/3, (0+0+3)/3 )
    assert pytest.approx(centroid[0], rel=1e-6) == pytest.approx((0+4+0)/3)
    assert pytest.approx(centroid[1], rel=1e-6) == pytest.approx((0+0+3)/3)

    # Inradius for right triangle r = (a+b-c)/2 where a=3,b=4,c=5 => r = (3+4-5)/2 = 1.0
    assert pytest.approx(inradius, rel=1e-6) == 1.0


def test_point_in_polygon_and_projection():
    square = [[0,0],[10,0],[10,10],[0,10]]
    assert gu.point_in_polygon((5,5), square) is True
    assert gu.point_in_polygon((11,5), square) is False

    proj = gu.project_point_inside((11,5), square)
    # projected point should be on right edge x=10
    assert pytest.approx(proj[0], rel=1e-6) == 10.0
    assert 0.0 <= proj[1] <= 10.0
