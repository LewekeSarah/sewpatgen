"""Unit tests for the outline helper functions in the geometry package.

These tests exercise the small facade around Shapely that was extracted
into `sewpat.geometry._outline` so they can be validated independently of
`PatternPart`.
"""

from sewpat.geometry import (
    Point,
    Segment,
    nudge_point_inside,
    outline_area_cm2,
    outline_bounding_box,
    outline_centroid,
    outline_contains_point,
    outline_width_at_y,
)


def _square_geoms(size: float):
    return [
        Segment(Point(0, 0), Point(size, 0)),
        Segment(Point(size, 0), Point(size, size)),
        Segment(Point(size, size), Point(0, size)),
        Segment(Point(0, size), Point(0, 0)),
    ]


def test_outline_centroid_none_on_empty():
    assert outline_centroid([]) is None


def test_outline_centroid_square():
    c = outline_centroid(_square_geoms(10.0))
    assert c is not None
    assert abs(c.x - 5.0) < 1e-3
    assert abs(c.y - 5.0) < 1e-3


def test_outline_area_square_10mm():
    assert abs(outline_area_cm2(_square_geoms(10.0)) - 1.0) < 1e-4


def test_outline_bounding_box_none_on_empty():
    assert outline_bounding_box([]) is None


def test_outline_bounding_box_rectangle():
    geoms = [
        Segment(Point(5, 15), Point(45, 15)),
        Segment(Point(45, 15), Point(45, 70)),
        Segment(Point(45, 70), Point(5, 70)),
        Segment(Point(5, 70), Point(5, 15)),
    ]
    bb = outline_bounding_box(geoms)
    assert bb is not None
    mn, mx = bb
    assert abs(mn.x - 5.0) < 1e-6 and abs(mn.y - 15.0) < 1e-6
    assert abs(mx.x - 45.0) < 1e-6 and abs(mx.y - 70.0) < 1e-6


def test_outline_contains_point():
    geoms = _square_geoms(100.0)
    assert outline_contains_point(geoms, Point(50, 50))
    assert not outline_contains_point(geoms, Point(0, 0))


def test_outline_width_at_y_and_nudge():
    geoms = _square_geoms(100.0)
    # width at midslice
    mnx, mxx = outline_width_at_y(geoms, 50.0)
    assert abs(mnx - 0.0) < 1e-6 and abs(mxx - 100.0) < 1e-6

    # no outline -> raises
    import pytest

    with pytest.raises(ValueError, match="No outline polygon"):
        outline_width_at_y([], 10.0)

    # nudge: a point outside should be moved inside
    p_out = Point(-10.0, 50.0)
    nudged = nudge_point_inside(geoms, p_out, Point(50, 50), step=1.0)
    # nudged x should be between 0 and 5 (snapped then small nudge)
    assert 0.0 <= nudged.x < 5.0


def test_nudge_point_on_boundary_preserved():
    geoms = _square_geoms(100.0)
    p_on = Point(50.0, 0.0)
    nudged = nudge_point_inside(geoms, p_on, Point(50, 50))
    assert abs(nudged.x - p_on.x) < 1e-6 and abs(nudged.y - p_on.y) < 1e-6
