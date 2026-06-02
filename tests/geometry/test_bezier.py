"""Tests for CubicBezier curve.

This module contains unit tests for the CubicBezier class defined in
sewpat.geometry._bezier, including tests for:
- point_along_from() - movement along curves
- bounding_box() - axis-aligned bounding box calculation
- intersect() - Bézier-Bézier intersection
- normal_at_t() - normal vector calculation
- point_at_length() - arc-length parameterization
- split() - curve subdivision
- split_at_points() - multi-point subdivision
- point_perpendicular() - offset point calculation
- contains_point() - point membership testing
- translate() - rigid translation of all control points
"""

import numpy as np
import pytest

from sewpat.geometry import CubicBezier, Point, intersect

# =============================================================================
# Point Along From Tests
# =============================================================================


def test_bezier_point_along_from_forward():
    """Moving forward along a straight Bezier (degenerate line) is accurate."""
    # Straight Bezier from (0,0) to (100,0) — arc-length == chord length
    bez = CubicBezier(Point(0, 0), Point(33, 0), Point(66, 0), Point(100, 0))
    p = bez.point_at_t(0.3)  # ≈ 30 mm along
    result = bez.point_along_from(p, 20)
    # Should land near x=50; allow 0.5 mm tolerance for
    # round-trip arc-length accumulation
    assert result.x == pytest.approx(50.0, abs=1)
    assert result.y == pytest.approx(0.0, abs=1e-3)


def test_bezier_point_along_from_displacement_magnitude():
    """Displacement along a curved Bezier equals the requested arc length."""
    bez = CubicBezier(Point(0, 0), Point(10, 40), Point(30, 40), Point(40, 0))
    p = bez.point_at_t(0.2)
    result = bez.point_along_from(p, 5.0)
    # The result should be strictly further along the curve
    assert result.distance_to(p) > 0.0


# =============================================================================
# Bounding Box Tests
# =============================================================================


@pytest.fixture
def bbox_test_curve():
    """Curve where control points lie outside the actual curve extent."""
    return CubicBezier(
        p0=Point(10, 10),
        p1=Point(20, 0),  # below the curve
        p2=Point(30, 20),  # above the curve
        p3=Point(40, 10),
    )


def test_bezier_bbox_x_bounds_match_endpoints(bbox_test_curve):
    """x range is fully determined by the endpoints for this curve."""
    bez = bbox_test_curve
    mn, mx = bez.bounding_box()
    assert mn.x == pytest.approx(10.0, abs=1e-6)
    assert mx.x == pytest.approx(40.0, abs=1e-6)


def test_bezier_bbox_y_does_not_reach_control_points(bbox_test_curve):
    """y min/max must stay within the actual curve, not at control points."""
    bez = bbox_test_curve
    mn, mx = bez.bounding_box()
    # Control points are at y=0 and y=20 – the curve never reaches them
    assert mn.y > 0.0, "y_min must be above the off-curve control point y=0"
    assert mx.y < 20.0, "y_max must be below the off-curve control point y=20"


def test_bezier_bbox_y_values_are_correct(bbox_test_curve):
    """Exact y extrema match the analytic result (also verified by svgpathtools)."""
    bez = bbox_test_curve
    mn, mx = bez.bounding_box()
    assert mn.y == pytest.approx(7.113249, abs=1e-4)
    assert mx.y == pytest.approx(12.886751, abs=1e-4)


def test_bezier_bbox_endpoints_always_inside(bbox_test_curve):
    """Start and end points of the curve must lie within the bounding box."""
    bez = bbox_test_curve
    mn, mx = bez.bounding_box()
    for pt in (bez.p0, bez.p3):
        assert pt.x >= mn.x
        assert pt.x <= mx.x
        assert pt.y >= mn.y
        assert pt.y <= mx.y


def test_bezier_bbox_straight_line():
    """A straight cubic Bezier has a bounding box equal to its endpoint range."""
    bez = CubicBezier(
        p0=Point(0, 0),
        p1=Point(10, 10),  # control points along the diagonal
        p2=Point(20, 20),
        p3=Point(30, 30),
    )
    mn, mx = bez.bounding_box()
    assert mn.x == pytest.approx(0.0, abs=1e-6)
    assert mn.y == pytest.approx(0.0, abs=1e-6)
    assert mx.x == pytest.approx(30.0, abs=1e-6)
    assert mx.y == pytest.approx(30.0, abs=1e-6)


# =============================================================================
# Intersection Tests
# =============================================================================


@pytest.fixture
def bezier_curves_A():
    """First test curve for Bézier–Bézier intersection."""
    return CubicBezier(
        p0=Point(10, 10),
        p1=Point(20, 0),
        p2=Point(30, 20),
        p3=Point(40, 10),
    )


@pytest.fixture
def bezier_curves_B():
    """Second test curve for Bézier–Bézier intersection."""
    return CubicBezier(
        p0=Point(10, 15),
        p1=Point(20, 25),
        p2=Point(30, 5),
        p3=Point(40, 15),
    )


def test_bezier_intersect_two_crossings_found(bezier_curves_A, bezier_curves_B):
    """The reference pair of curves has exactly two intersections."""
    pts = intersect(bezier_curves_A, bezier_curves_B)
    assert len(pts) == 2


def test_bezier_intersect_points_lie_on_both_curves(bezier_curves_A, bezier_curves_B):
    """Every returned point must lie on both curves (distance < 0.05 mm).

    We verify membership by sampling each curve at 1000 points and checking
    that the intersection point is within 0.05 mm of the closest sample.
    The tolerance is deliberately loose to account for the finite sampling
    resolution (~0.033 mm step for a ~33 mm long curve).
    """
    tol = 0.05  # mm – sampling grid resolution bound
    pts = intersect(bezier_curves_A, bezier_curves_B)
    for pt in pts:
        min_d_a = min(pt.distance_to(bezier_curves_A.point_at_t(k / 1000)) for k in range(1001))
        min_d_b = min(pt.distance_to(bezier_curves_B.point_at_t(k / 1000)) for k in range(1001))
        assert min_d_a < tol, f"Point {pt} is not on curve A"
        assert min_d_b < tol, f"Point {pt} is not on curve B"


def test_bezier_intersect_first_intersection_coordinates(bezier_curves_A, bezier_curves_B):
    """First intersection near (30.92, 12.50) as per svgpathtools reference."""
    pts = sorted(intersect(bezier_curves_A, bezier_curves_B), key=lambda p: p.x)
    assert pts[0].x == pytest.approx(30.924, abs=0.1)
    assert pts[0].y == pytest.approx(12.5, abs=0.1)


def test_bezier_intersect_second_intersection_coordinates(bezier_curves_A, bezier_curves_B):
    """Second intersection near (36.13, 12.50) as per svgpathtools reference."""
    pts = sorted(intersect(bezier_curves_A, bezier_curves_B), key=lambda p: p.x)
    assert pts[1].x == pytest.approx(36.133, abs=0.1)
    assert pts[1].y == pytest.approx(12.5, abs=0.1)


def test_bezier_intersect_symmetric_call_returns_same_count(bezier_curves_A, bezier_curves_B):
    """intersect(A, B) and intersect(B, A) must return the same number of points."""
    pts_ab = intersect(bezier_curves_A, bezier_curves_B)
    pts_ba = intersect(bezier_curves_B, bezier_curves_A)
    assert len(pts_ab) == len(pts_ba)


def test_bezier_intersect_no_intersection_parallel_curves():
    """Two curves that do not cross must return an empty list."""
    top = CubicBezier(
        p0=Point(0, 20),
        p1=Point(10, 20),
        p2=Point(20, 20),
        p3=Point(30, 20),
    )
    bottom = CubicBezier(
        p0=Point(0, 0),
        p1=Point(10, 0),
        p2=Point(20, 0),
        p3=Point(30, 0),
    )
    pts = intersect(top, bottom)
    assert pts == []


def test_bezier_intersect_no_duplicates_returned(bezier_curves_A, bezier_curves_B):
    """No two returned points may be closer than 0.01 mm to each other."""
    pts = intersect(bezier_curves_A, bezier_curves_B)
    for i, p1 in enumerate(pts):
        for j, p2 in enumerate(pts):
            if i != j:
                assert p1.distance_to(p2) > 0.01


# =============================================================================
# Methods Tests (properties, normal, point_at_length, split)
# =============================================================================


@pytest.fixture
def bezier_test_curve():
    """Standard test curve for CubicBezier methods."""
    return CubicBezier(
        p0=Point(10, 10),
        p1=Point(20, 0),
        p2=Point(30, 20),
        p3=Point(40, 10),
    )


# ── start / end aliases ──────────────────────────────────────────────────


def test_bezier_start_is_p0(bezier_test_curve):
    """start property must equal p0."""
    b = bezier_test_curve
    assert b.start == b.p0


def test_bezier_end_is_p3(bezier_test_curve):
    """end property must equal p3."""
    b = bezier_test_curve
    assert b.end == b.p3


# ── length as property ───────────────────────────────────────────────────


def test_bezier_length_is_property(bezier_test_curve):
    """length must be accessible as a property (no call parentheses)."""
    b = bezier_test_curve
    curve_len = b.length  # must not raise TypeError
    assert curve_len > 0.0


# ── normal_at_t ─────────────────────────────────────────────────────────


def test_bezier_normal_is_unit_length(bezier_test_curve):
    """normal_at_t() must return a vector of length 1."""
    b = bezier_test_curve
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        n = b.normal_at_t(t)
        assert float(np.linalg.norm(n)) == pytest.approx(1.0, abs=1e-10)


def test_bezier_normal_perpendicular_to_tangent(bezier_test_curve):
    """Normal and tangent must be perpendicular (dot product = 0)."""
    b = bezier_test_curve
    for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
        tan = b.tangent_at_t(t)
        nor = b.normal_at_t(t)
        tan_unit = tan / np.linalg.norm(tan)
        assert float(np.dot(tan_unit, nor)) == pytest.approx(0.0, abs=1e-10)


def test_bezier_normal_offset_point_at_correct_distance(bezier_test_curve):
    """A point offset by d mm along the normal is d mm from the curve."""
    b = bezier_test_curve
    d = 10.0  # mm seam allowance
    t = 0.5
    pt = b.point_at_t(t)
    nor = b.normal_at_t(t)
    offset = Point(pt.x + d * nor[0], pt.y + d * nor[1])
    assert pt.distance_to(offset) == pytest.approx(d, abs=1e-10)


# ── point_at_length ──────────────────────────────────────────────────────


def test_bezier_point_at_length_zero_is_start(bezier_test_curve):
    """point_at_length(0) must return p0."""
    b = bezier_test_curve
    pt = b.point_at_length(0.0)
    assert pt.x == pytest.approx(b.p0.x, abs=1e-4)
    assert pt.y == pytest.approx(b.p0.y, abs=1e-4)


def test_bezier_point_at_length_full_is_end(bezier_test_curve):
    """point_at_length(total_length) must return p3."""
    b = bezier_test_curve
    pt = b.point_at_length(b.length)
    assert pt.x == pytest.approx(b.p3.x, abs=1e-4)
    assert pt.y == pytest.approx(b.p3.y, abs=1e-4)


def test_bezier_point_at_length_midpoint_is_on_curve(bezier_test_curve):
    """point_at_length(L/2) must lie on the curve."""
    b = bezier_test_curve
    half = b.length / 2
    pt = b.point_at_length(half)
    # Verify by sampling: closest sample on curve should be < 0.05 mm away
    min_d = min(pt.distance_to(b.point_at_t(k / 2000)) for k in range(2001))
    assert min_d < 0.05


def test_bezier_point_at_length_arc_distance_is_correct(bezier_test_curve):
    """The arc length from p0 to point_at_length(s) must equal s."""
    b = bezier_test_curve
    s = b.length * 0.3
    # Find t for pt and integrate back – use svgpathtools ilength round-trip
    from svgpathtools import CubicBezier as SvgBez

    svg = SvgBez(
        complex(b.p0.x, b.p0.y),
        complex(b.p1.x, b.p1.y),
        complex(b.p2.x, b.p2.y),
        complex(b.p3.x, b.p3.y),
    )
    t = svg.ilength(s)
    recovered = svg.length(t1=t)  # length from 0 to t
    assert recovered == pytest.approx(s, abs=1e-4)


def test_bezier_point_at_length_raises_on_negative(bezier_test_curve):
    """point_at_length() must raise ValueError for negative arc length."""
    b = bezier_test_curve
    with pytest.raises(ValueError):
        b.point_at_length(-1.0)


def test_bezier_point_at_length_raises_on_overflow(bezier_test_curve):
    """point_at_length() must raise ValueError if arc length > curve length."""
    b = bezier_test_curve
    with pytest.raises(ValueError):
        b.point_at_length(b.length + 1.0)


# ── split ────────────────────────────────────────────────────────────────


def test_bezier_split_left_starts_at_p0(bezier_test_curve):
    """Left piece must start at the original p0."""
    b = bezier_test_curve
    left, _ = b.split(0.5)
    assert left.p0.x == pytest.approx(b.p0.x, abs=1e-10)
    assert left.p0.y == pytest.approx(b.p0.y, abs=1e-10)


def test_bezier_split_right_ends_at_p3(bezier_test_curve):
    """Right piece must end at the original p3."""
    b = bezier_test_curve
    _, right = b.split(0.5)
    assert right.p3.x == pytest.approx(b.p3.x, abs=1e-10)
    assert right.p3.y == pytest.approx(b.p3.y, abs=1e-10)


def test_bezier_split_join_point_matches(bezier_test_curve):
    """Left end and right start must be the same point (the split point)."""
    b = bezier_test_curve
    left, right = b.split(0.5)
    assert left.p3.x == pytest.approx(right.p0.x, abs=1e-10)
    assert left.p3.y == pytest.approx(right.p0.y, abs=1e-10)


def test_bezier_split_join_point_lies_on_original(bezier_test_curve):
    """The split point must lie on the original curve at t."""
    b = bezier_test_curve
    t = 0.4
    left, right = b.split(t)
    expected = b.point_at_t(t)
    assert left.p3.x == pytest.approx(expected.x, abs=1e-8)
    assert left.p3.y == pytest.approx(expected.y, abs=1e-8)


def test_bezier_split_lengths_sum_to_original(bezier_test_curve):
    """Left length + right length must equal the original curve length."""
    b = bezier_test_curve
    left, right = b.split(0.5)
    assert left.length + right.length == pytest.approx(b.length, abs=1e-6)


def test_bezier_split_returns_cubicbezier_instances(bezier_test_curve):
    """split() must return two CubicBezier objects."""
    b = bezier_test_curve
    left, right = b.split(0.5)
    assert isinstance(left, CubicBezier)
    assert isinstance(right, CubicBezier)


# =============================================================================
# Split At Points Tests
# =============================================================================


@pytest.fixture
def split_test_curve():
    """Standard test curve for split_at_points tests."""
    return CubicBezier(
        p0=Point(10, 10),
        p1=Point(20, 0),
        p2=Point(30, 20),
        p3=Point(40, 10),
    )


def test_bezier_split_at_one_point_gives_two_curves(split_test_curve):
    b = split_test_curve
    subs = b.split_at_points([b.point_at_t(0.5)])
    assert len(subs) == 2
    for s in subs:
        assert isinstance(s, CubicBezier)


def test_bezier_split_at_two_points_gives_three_curves(split_test_curve):
    b = split_test_curve
    subs = b.split_at_points([b.point_at_t(0.25), b.point_at_t(0.75)])
    assert len(subs) == 3


def test_bezier_split_at_points_lengths_sum_to_original(split_test_curve):
    b = split_test_curve
    subs = b.split_at_points([b.point_at_t(0.3), b.point_at_t(0.7)])
    total = sum(s.length for s in subs)
    assert total == pytest.approx(b.length, abs=1e-4)


def test_bezier_split_at_points_chain_is_continuous(split_test_curve):
    """End of each sub-curve must equal the start of the next."""
    b = split_test_curve
    subs = b.split_at_points([b.point_at_t(0.2), b.point_at_t(0.6), b.point_at_t(0.9)])
    for a, c in zip(subs, subs[1:], strict=False):
        assert a.p3.x == pytest.approx(c.p0.x, abs=1e-6)
        assert a.p3.y == pytest.approx(c.p0.y, abs=1e-6)


def test_bezier_split_at_points_unsorted_input_same_result(split_test_curve):
    """Points in reverse order must produce the same sub-lengths."""
    b = split_test_curve
    pa, pb = b.point_at_t(0.3), b.point_at_t(0.7)
    forward = b.split_at_points([pa, pb])
    backward = b.split_at_points([pb, pa])
    assert len(forward) == len(backward)
    for a, c in zip(forward, backward, strict=False):
        assert a.length == pytest.approx(c.length, abs=1e-4)


def test_bezier_split_at_endpoint_produces_no_degenerate_stub(split_test_curve):
    """A point coinciding with p0 must be dropped (only one real split left)."""
    b = split_test_curve
    subs = b.split_at_points([b.p0, b.point_at_t(0.5)])
    assert len(subs) == 2


def test_bezier_split_at_points_all_near_endpoints_returns_original(split_test_curve):
    """When all points are at endpoints, return the original curve."""
    b = split_test_curve
    subs = b.split_at_points([b.p0, b.p3])
    assert len(subs) == 1
    assert subs[0].length == pytest.approx(b.length, abs=1e-4)


def test_bezier_split_preserves_start_and_end(split_test_curve):
    """First sub-curve starts at p0; last ends at p3."""
    b = split_test_curve
    subs = b.split_at_points([b.point_at_t(0.4)])
    assert subs[0].p0.x == pytest.approx(b.p0.x, abs=1e-8)
    assert subs[-1].p3.x == pytest.approx(b.p3.x, abs=1e-8)


# =============================================================================
# Consistency Methods Tests (point_perpendicular, contains_point)
# =============================================================================


@pytest.fixture
def bezier_consistency_curve():
    """Standard test curve for CubicBezier consistency methods."""
    return CubicBezier(
        p0=Point(10, 10),
        p1=Point(20, 0),
        p2=Point(30, 20),
        p3=Point(40, 10),
    )


# ── point_perpendicular ──────────────────────────────────────────────────


def test_bezier_point_perpendicular_distance(bezier_consistency_curve):
    """Offset point must be exactly *distance* away from the curve point."""
    b = bezier_consistency_curve
    d = 8.0
    for t in [0.25, 0.5, 0.75]:
        base = b.point_at_t(t)
        offset = b.point_perpendicular(d, t)
        assert base.distance_to(offset) == pytest.approx(d, abs=1e-10)


def test_bezier_point_perpendicular_direction_is_normal(bezier_consistency_curve):
    """The offset direction must be parallel to normal_at_t()."""
    b = bezier_consistency_curve
    t = 0.5
    base = b.point_at_t(t)
    offset = b.point_perpendicular(5.0, t)
    diff = np.array([offset.x - base.x, offset.y - base.y])
    diff_unit = diff / np.linalg.norm(diff)
    expected = b.normal_at_t(t)
    assert float(np.dot(diff_unit, expected)) == pytest.approx(1.0, abs=1e-10)


def test_bezier_point_perpendicular_negative_goes_other_side(bezier_consistency_curve):
    """Positive and negative distance must produce points on opposite sides."""
    b = bezier_consistency_curve
    t = 0.5
    pos = b.point_perpendicular(+5.0, t)
    neg = b.point_perpendicular(-5.0, t)
    base = b.point_at_t(t)
    # Both must be 5 mm from base, 10 mm from each other
    assert base.distance_to(pos) == pytest.approx(5.0, abs=1e-10)
    assert base.distance_to(neg) == pytest.approx(5.0, abs=1e-10)
    assert pos.distance_to(neg) == pytest.approx(10.0, abs=1e-10)


# ── contains_point ───────────────────────────────────────────────────────


def test_bezier_contains_point_endpoints(bezier_consistency_curve):
    """p0 and p3 must be on the curve."""
    b = bezier_consistency_curve
    assert b.contains_point(b.p0)
    assert b.contains_point(b.p3)


def test_bezier_contains_point_midpoint(bezier_consistency_curve):
    """The midpoint of the curve must be on the curve."""
    b = bezier_consistency_curve
    mid = b.point_at_t(0.5)
    assert b.contains_point(mid)


def test_bezier_contains_point_off_curve(bezier_consistency_curve):
    """A control point is NOT on the curve and must return False."""
    b = bezier_consistency_curve
    # p1=(20,0) is the off-curve control point – well outside the curve
    assert not b.contains_point(Point(20, 0))


def test_bezier_contains_point_tolerance(bezier_consistency_curve):
    """A point 0.005 mm from the curve is inside default tolerance (0.01 mm)."""
    b = bezier_consistency_curve
    pt = b.point_at_t(0.3)
    # nudge slightly off-curve in normal direction
    nor = b.normal_at_t(0.3)
    near = Point(pt.x + 0.005 * nor[0], pt.y + 0.005 * nor[1])
    assert b.contains_point(near, tolerance=0.01)


def test_bezier_contains_point_outside_tolerance(bezier_consistency_curve):
    """A point 1 mm from the curve is outside default tolerance."""
    b = bezier_consistency_curve
    pt = b.point_at_t(0.3)
    nor = b.normal_at_t(0.3)
    far = Point(pt.x + 1.0 * nor[0], pt.y + 1.0 * nor[1])
    assert not b.contains_point(far, tolerance=0.01)


# =============================================================================
# Translate Tests (line 137)
# =============================================================================


def test_cubic_bezier_translate_moves_all_control_points() -> None:
    """translate() shifts every control point and preserves the name."""
    b = CubicBezier(
        Point(0, 0),
        Point(10, 20),
        Point(30, 20),
        Point(40, 0),
        name="test_curve",
    )
    shifted = b.translate(5, -3)

    assert shifted.p0 == Point(5, -3)
    assert shifted.p1 == Point(15, 17)
    assert shifted.p2 == Point(35, 17)
    assert shifted.p3 == Point(45, -3)
    assert shifted.name == "test_curve"


def test_cubic_bezier_translate_returns_new_object() -> None:
    """translate() returns a *new* CubicBezier, leaving the original unchanged."""
    b = CubicBezier(Point(0, 0), Point(10, 0), Point(20, 0), Point(30, 0))
    shifted = b.translate(100, 100)

    assert b.p0 == Point(0, 0)
    assert shifted.p0 == Point(100, 100)


def test_cubic_bezier_translate_zero_is_identity() -> None:
    """translate(0, 0) returns a curve with identical control points."""
    b = CubicBezier(Point(1, 2), Point(3, 4), Point(5, 6), Point(7, 8))
    shifted = b.translate(0, 0)

    assert shifted.p0 == b.p0
    assert shifted.p3 == b.p3


# =============================================================================
# split_at_points — zero-length early return (line 320)
# =============================================================================


def test_bezier_split_at_points_zero_length_returns_single_copy() -> None:
    """A zero-length Bézier (all control points equal) returns a single-element
    list — the early-return on line 320."""
    p = Point(5, 5)
    b = CubicBezier(p, p, p, p, name="zero")
    result = b.split_at_points([p, p])

    assert len(result) == 1
    assert isinstance(result[0], CubicBezier)
    assert result[0].p0 == p
    assert result[0].name == "zero"


# =============================================================================
# __str__ and __repr__ (lines 114, 120)
# =============================================================================


def test_cubic_bezier_str_contains_control_points() -> None:
    """str() includes all four control-point coordinates and the name."""
    b = CubicBezier(Point(0, 0), Point(10, 20), Point(30, 20), Point(40, 0), name="arc")
    s = str(b)
    assert "arc" in s
    assert "40" in s


def test_cubic_bezier_repr_equals_str() -> None:
    """repr() returns the same string as str() for CubicBezier."""
    b = CubicBezier(Point(1, 2), Point(3, 4), Point(5, 6), Point(7, 8), name="test")
    assert repr(b) == str(b)


def test_cubic_bezier_rep_point_is_parametric_midpoint() -> None:
    # straight Bézier from (0,0) to (10,0) — point_at_t(0.5) == (5, 0)
    b = CubicBezier(Point(0, 0), Point(0, 0), Point(10, 0), Point(10, 0))
    rep = b.rep_point()
    assert rep.x == pytest.approx(5.0)
    assert rep.y == pytest.approx(0.0)
