"""Tests for the geometry module.

This module contains unit tests for all the geometric primitives
defined in the geometry module: Point, Segment, Ray, and Circle.
"""

import math

import numpy as np
import pytest

from sewpat.geometry import (
    Circle,
    CubicBezier,
    Dart,
    InfoBox,
    Line,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
    intersect,
    miter_corner,
    point_in_sector,
    round_corner,
)

# =============================================================================
# Point Tests
# =============================================================================


def test_point_creation():
    """Test point creation and attributes.

    Verifies that a Point can be created with coordinates
    and that the coordinates are correctly stored.
    """
    p = Point(2.5, 3.7)
    assert p.x == pytest.approx(2.5)
    assert p.y == pytest.approx(3.7)


def test_point_distance_to():
    """Test distance calculation between points.

    Verifies that the distance_to method correctly calculates
    the Euclidean distance between two points.
    """
    p1 = Point(0, 0)
    p2 = Point(3, 4)
    assert p1.distance_to(p2) == pytest.approx(5.0)
    assert p2.distance_to(p1) == pytest.approx(5.0)


def test_point_translate():
    """Test point translation.

    Verifies that the translate method correctly creates a new point
    translated by the specified vector, while leaving the original unchanged.
    """
    p = Point(1, 2)
    translated = p.translate(2, 3)
    assert translated.x == pytest.approx(3)
    assert translated.y == pytest.approx(5)
    # Original point should not change (immutability)
    assert p.x == pytest.approx(1)
    assert p.y == pytest.approx(2)


def test_point_rotate():
    """Test point rotation around another point.

    Verifies that the rotate method correctly rotates a point
    around a specified center by the given angle.
    """
    center = Point(0, 0)
    p = Point(1, 0)

    # Rotate 90 degrees counterclockwise
    rotated = p.rotate(center, math.pi / 2)
    assert rotated.x == pytest.approx(0, abs=1e-10)
    assert rotated.y == pytest.approx(1, abs=1e-10)

    # Test with NumPy array operations
    np.testing.assert_almost_equal(rotated.coords, np.array([0, 1]), decimal=10)

    # Rotate 180 degrees
    rotated = p.rotate(center, math.pi)
    assert rotated.x == pytest.approx(-1, abs=1e-10)
    assert rotated.y == pytest.approx(0, abs=1e-10)

    # Rotation around non-origin center
    center = Point(1, 1)
    p = Point(2, 1)
    rotated = p.rotate(center, math.pi / 2)
    assert rotated.x == pytest.approx(1, abs=1e-10)
    assert rotated.y == pytest.approx(2, abs=1e-10)


def test_point_add():
    """Point + Point offsets by the second point as a displacement vector."""
    a = Point(1, 2)
    b = Point(3, 4)
    result = a + b
    assert result.x == pytest.approx(4)
    assert result.y == pytest.approx(6)
    # Original unchanged
    assert a.x == pytest.approx(1)


def test_point_sub():
    """Point - Point returns the displacement vector as a Point."""
    a = Point(5, 7)
    b = Point(2, 3)
    result = a - b
    assert result.x == pytest.approx(3)
    assert result.y == pytest.approx(4)


def test_point_mul_scalar():
    """Point * scalar scales the position vector."""
    p = Point(3, 4)
    assert (p * 2).x == pytest.approx(6)
    assert (p * 2).y == pytest.approx(8)
    assert (p * 0.5).x == pytest.approx(1.5)


def test_point_rmul_scalar():
    """scalar * Point is equivalent to Point * scalar."""
    p = Point(3, 4)
    result = 2.0 * p
    assert result.x == pytest.approx(6)
    assert result.y == pytest.approx(8)


def test_point_neg():
    """-Point negates both coordinates."""
    p = Point(3, -4)
    result = -p
    assert result.x == pytest.approx(-3)
    assert result.y == pytest.approx(4)


def test_point_midpoint_via_arithmetic():
    """(a + b) * 0.5 gives the midpoint."""
    a = Point(0, 0)
    b = Point(4, 6)
    mid = (a + b) * 0.5
    assert mid.x == pytest.approx(2)
    assert mid.y == pytest.approx(3)


def test_point_add_non_point_returns_not_implemented():
    """Adding a non-Point returns NotImplemented
    (no TypeError from Point itself)."""
    p = Point(1, 2)
    result = p.__add__(42)
    assert result is NotImplemented


def test_point_sub_non_point_returns_not_implemented():
    p = Point(1, 2)
    assert p.__sub__("x") is NotImplemented


def test_point_mul_non_scalar_returns_not_implemented():
    p = Point(1, 2)
    assert p.__mul__(Point(1, 1)) is NotImplemented


def test_point_immutability_preserved():
    """Arithmetic operators always return new Points; originals are unchanged."""
    p = Point(1, 2)
    _ = p + Point(10, 10)
    _ = p * 5
    assert p.x == pytest.approx(1)
    assert p.y == pytest.approx(2)


# =============================================================================
# Point Along From Tests (curve.point_along_from())
# =============================================================================

# ------------------------------------------------------------------
# Segment
# ------------------------------------------------------------------


def test_segment_point_along_from_forward():
    """Moving forward along a horizontal segment gives the correct x position."""
    seg = Segment(Point(0, 0), Point(100, 0))
    p = Point(30, 0)
    result = seg.point_along_from(p, 20)
    assert result.x == pytest.approx(50.0, abs=1e-6)
    assert result.y == pytest.approx(0.0, abs=1e-6)


def test_segment_point_along_from_backward():
    """A negative arc_length moves backward along the segment."""
    seg = Segment(Point(0, 0), Point(100, 0))
    p = Point(50, 0)
    result = seg.point_along_from(p, -10)
    assert result.x == pytest.approx(40.0, abs=1e-6)


def test_segment_point_along_from_diagonal():
    """Works correctly on a diagonal segment."""
    seg = Segment(Point(0, 0), Point(30, 40))  # length = 50
    p = seg.point_at_t(0.5)  # at arc-length 25
    result = seg.point_along_from(p, 10)
    assert result.distance_to(p) == pytest.approx(10.0, abs=1e-5)


def test_segment_point_along_from_out_of_range_raises():
    """Moving beyond the segment end raises ValueError."""
    seg = Segment(Point(0, 0), Point(10, 0))
    p = Point(8, 0)
    with pytest.raises(ValueError):
        seg.point_along_from(p, 5)  # would land at 13, beyond length 10


# ------------------------------------------------------------------
# Ray
# ------------------------------------------------------------------


def test_ray_point_along_from_forward():
    """Moving along a ray advances by the exact distance."""
    ray = Ray(Point(0, 0), (1, 0))
    p = Point(30, 0)
    result = ray.point_along_from(p, 15)
    assert result.x == pytest.approx(45.0, abs=1e-6)
    assert result.y == pytest.approx(0.0, abs=1e-6)


def test_ray_point_along_from_backward():
    """Negative arc_length moves backward along the ray."""
    ray = Ray(Point(0, 0), (0, 1))
    p = Point(0, 50)
    result = ray.point_along_from(p, -20)
    assert result.y == pytest.approx(30.0, abs=1e-6)


# ------------------------------------------------------------------
# Line
# ------------------------------------------------------------------


def test_line_point_along_from_forward():
    """Moving along an infinite line works in both directions."""
    from sewpat.geometry import Line

    line = Line(Point(0, 0), (1, 0))
    p = Point(10, 0)
    result = line.point_along_from(p, 25)
    assert result.x == pytest.approx(35.0, abs=1e-6)


def test_line_point_along_from_backward():
    """Negative arc_length on a Line moves in the opposite direction."""
    from sewpat.geometry import Line

    line = Line(Point(0, 0), (1, 0))
    p = Point(10, 0)
    result = line.point_along_from(p, -10)
    assert result.x == pytest.approx(0.0, abs=1e-6)


# ------------------------------------------------------------------
# Circle
# ------------------------------------------------------------------


def test_circle_point_along_from_ccw():
    """Moving CCW along a circle by π*r (half circumference)
    reaches the antipode."""
    c = Circle(Point(0, 0), 10)
    p = c.point_at_angle(0)  # (10, 0)
    half_circ = math.pi * 10
    result = c.point_along_from(p, half_circ)
    assert result.x == pytest.approx(-10.0, abs=1e-5)
    assert result.y == pytest.approx(0.0, abs=1e-5)


def test_circle_point_along_from_full_revolution():
    """Moving a full circumference returns to the starting point."""
    c = Circle(Point(0, 0), 10)
    p = c.point_at_angle(math.pi / 4)
    full = 2 * math.pi * 10
    result = c.point_along_from(p, full)
    assert result.x == pytest.approx(p.x, abs=1e-5)
    assert result.y == pytest.approx(p.y, abs=1e-5)


def test_circle_point_along_from_cw_negative():
    """Negative arc_length moves clockwise."""
    c = Circle(Point(0, 0), 10)
    p = c.point_at_angle(math.pi / 2)  # (0, 10)
    quarter = math.pi / 2 * 10
    result = c.point_along_from(p, -quarter)
    assert result.x == pytest.approx(10.0, abs=1e-5)
    assert result.y == pytest.approx(0.0, abs=1e-5)


# =============================================================================
# Segment Tests
# =============================================================================


def test_segment_creation():
    """Test segment creation and attributes.

    Verifies that a Segment can be created with two points
    and that the points are correctly stored, including via start/end aliases.
    """
    p1 = Point(1, 1)
    p2 = Point(4, 5)
    line = Segment(p1, p2)
    assert line.p1 == p1
    assert line.p2 == p2
    assert line.start == p1
    assert line.end == p2


def test_segment_length():
    """Test line length calculation.

    Verifies that the length property correctly calculates
    the Euclidean distance between the line's endpoints.
    """
    line = Segment(Point(0, 0), Point(3, 4))
    assert line.length == pytest.approx(5.0)


def test_segment_direction_unnormalized():
    """Test direction vector calculation."""
    line = Segment(Point(1, 1), Point(4, 5))
    direction = line.direction_unnormalized
    np.testing.assert_almost_equal(direction, np.array([3, 4]))


def test_segment_midpoint():
    """Test midpoint calculation.

    Verifies that the midpoint property correctly calculates
    the point exactly halfway between the line's endpoints.
    """
    line = Segment(Point(1, 2), Point(5, 6))
    mid = line.midpoint
    assert mid.x == pytest.approx(3.0)
    assert mid.y == pytest.approx(4.0)


def test_segment_contains_point():
    """Test if a point lies on the line segment."""
    line = Segment(Point(0, 0), Point(10, 10))
    assert line.contains_point(Point(0, 0))
    assert line.contains_point(Point(5, 5))
    assert line.contains_point(Point(10, 10))
    assert not line.contains_point(Point(2, 3))
    assert not line.contains_point(Point(-1, -1))
    assert not line.contains_point(Point(11, 11))


def test_segment_point_at_t():
    """Test point_at_t()."""
    seg = Segment(Point(0, 0), Point(10, 0))
    assert seg.point_at_t(0.0).x == pytest.approx(0.0)
    assert seg.point_at_t(0.5).x == pytest.approx(5.0)
    assert seg.point_at_t(1.0).x == pytest.approx(10.0)


def test_segment_point_perpendicular_t():
    """point_perpendicular with t= places the point at the correct position."""
    seg = Segment(Point(0, 0), Point(10, 0))  # horizontal, normal points up (+y)
    pt = seg.point_perpendicular(5.0, t=0.5)
    assert pt.x == pytest.approx(5.0)
    assert pt.y == pytest.approx(5.0)


def test_segment_point_perpendicular_arc_length():
    """point_perpendicular with arc_length= gives the same result as t=."""
    seg = Segment(Point(0, 0), Point(10, 0))
    pt_t = seg.point_perpendicular(5.0, t=0.5)
    pt_l = seg.point_perpendicular(5.0, arc_length=5.0)
    assert pt_t.x == pytest.approx(pt_l.x)
    assert pt_t.y == pytest.approx(pt_l.y)


def test_segment_point_perpendicular_default_is_midpoint():
    """point_perpendicular with no position arg uses the midpoint."""
    seg = Segment(Point(0, 0), Point(10, 0))
    pt = seg.point_perpendicular(3.0)
    assert pt.x == pytest.approx(5.0)
    assert pt.y == pytest.approx(3.0)


def test_segment_point_perpendicular_negative_distance():
    """Negative distance goes to the right (opposite side) of the segment."""
    seg = Segment(Point(0, 0), Point(10, 0))
    pos = seg.point_perpendicular(+5.0, t=0.5)
    neg = seg.point_perpendicular(-5.0, t=0.5)
    assert pos.x == pytest.approx(neg.x)
    assert pos.y == pytest.approx(-neg.y)


def test_segment_point_perpendicular_both_position_args_raises():
    """Providing both arc_length and t must raise ValueError."""
    seg = Segment(Point(0, 0), Point(10, 0))
    with pytest.raises(ValueError):
        seg.point_perpendicular(5.0, arc_length=3.0, t=0.3)


def test_segment_line_line_intersection():
    """Test intersection between two lines.

    Verifies that the intersect_with method correctly finds
    the intersection point between two lines and handles
    special cases like parallel lines and non-intersecting segments.
    """
    line1 = Segment(Point(0, 0), Point(10, 10))
    line2 = Segment(Point(0, 10), Point(10, 0))

    # These lines should intersect at (5, 5)
    intersections = intersect(line1, line2)
    assert len(intersections) == 1
    assert intersections[0].x == pytest.approx(5.0)
    assert intersections[0].y == pytest.approx(5.0)

    # Parallel lines
    line3 = Segment(Point(0, 0), Point(10, 10))
    line4 = Segment(Point(0, 1), Point(10, 11))
    assert intersect(line3, line4) == []

    # Lines that don't intersect within their segments
    line5 = Segment(Point(0, 0), Point(5, 5))
    line6 = Segment(Point(6, 6), Point(10, 10))
    assert intersect(line5, line6) == []


# =============================================================================
# Segment Additional Methods Tests
# =============================================================================


@pytest.fixture
def test_segment():
    """Standard test segment for additional method tests."""
    return Segment(Point(0, 0), Point(30, 40))  # length = 50


# ── point_at_length ──────────────────────────────────────────────────────


def test_segment_point_at_length_zero_is_p1(test_segment):
    s = test_segment
    pt = s.point_at_length(0)
    assert pt.x == pytest.approx(0.0)
    assert pt.y == pytest.approx(0.0)


def test_segment_point_at_length_full_is_p2(test_segment):
    s = test_segment
    pt = s.point_at_length(50)
    assert pt.x == pytest.approx(30.0)
    assert pt.y == pytest.approx(40.0)


def test_segment_point_at_length_midpoint(test_segment):
    s = test_segment
    pt = s.point_at_length(25)
    assert pt.x == pytest.approx(15.0)
    assert pt.y == pytest.approx(20.0)


def test_segment_point_at_length_raises_negative(test_segment):
    with pytest.raises(ValueError):
        test_segment.point_at_length(-1)


def test_segment_point_at_length_raises_overflow(test_segment):
    with pytest.raises(ValueError):
        test_segment.point_at_length(51)


# ── bounding_box ─────────────────────────────────────────────────────────


def test_segment_bounding_box_axis_aligned():
    s = Segment(Point(5, 3), Point(20, 15))
    mn, mx = s.bounding_box()
    assert mn.x == pytest.approx(5)
    assert mn.y == pytest.approx(3)
    assert mx.x == pytest.approx(20)
    assert mx.y == pytest.approx(15)


def test_segment_bounding_box_reversed_coords():
    """Works correctly when p2 has smaller coordinates than p1."""
    s = Segment(Point(20, 15), Point(5, 3))
    mn, mx = s.bounding_box()
    assert mn.x == pytest.approx(5)
    assert mn.y == pytest.approx(3)
    assert mx.x == pytest.approx(20)
    assert mx.y == pytest.approx(15)


def test_segment_bounding_box_horizontal():
    s = Segment(Point(0, 5), Point(10, 5))
    mn, mx = s.bounding_box()
    assert mn.y == pytest.approx(mx.y)  # zero height


# ── split ────────────────────────────────────────────────────────────────


def test_segment_split_returns_two_segments(test_segment):
    left, right = test_segment.split(0.5)
    assert isinstance(left, Segment)
    assert isinstance(right, Segment)


def test_segment_split_midpoint_at_half(test_segment):
    left, right = test_segment.split(0.5)
    # left ends / right starts at midpoint (15, 20)
    assert left.p2.x == pytest.approx(15.0)
    assert left.p2.y == pytest.approx(20.0)
    assert right.p1.x == pytest.approx(15.0)
    assert right.p1.y == pytest.approx(20.0)


def test_segment_split_lengths_sum_to_original(test_segment):
    s = test_segment
    left, right = s.split(0.4)
    assert left.length + right.length == pytest.approx(s.length, abs=1e-6)


def test_segment_split_preserves_endpoints(test_segment):
    s = test_segment
    left, right = s.split(0.3)
    assert left.p1.x == pytest.approx(s.p1.x)
    assert right.p2.x == pytest.approx(s.p2.x)
    assert right.p2.y == pytest.approx(s.p2.y)


def test_segment_split_invalid_t_zero_raises(test_segment):
    with pytest.raises(ValueError):
        test_segment.split(0.0)


def test_segment_split_invalid_t_one_raises(test_segment):
    with pytest.raises(ValueError):
        test_segment.split(1.0)


# ── split_at_points ──────────────────────────────────────────────────────


def test_segment_split_at_one_point_gives_two_segments(test_segment):
    s = test_segment
    mid = s.point_at_t(0.5)
    subs = s.split_at_points([mid])
    assert len(subs) == 2


def test_segment_split_at_two_points_gives_three_segments(test_segment):
    s = test_segment
    pa = s.point_at_t(0.25)
    pb = s.point_at_t(0.75)
    subs = s.split_at_points([pa, pb])
    assert len(subs) == 3


def test_segment_split_at_points_lengths_sum_to_original(test_segment):
    s = test_segment
    pa = s.point_at_t(0.3)
    pb = s.point_at_t(0.7)
    subs = s.split_at_points([pa, pb])
    total = sum(seg.length for seg in subs)
    assert total == pytest.approx(s.length, abs=1e-6)


def test_segment_split_at_points_chain_is_continuous(test_segment):
    """End of each sub-segment must equal start of the next."""
    s = test_segment
    subs = s.split_at_points([s.point_at_t(0.2), s.point_at_t(0.6), s.point_at_t(0.9)])
    for a, b in zip(subs, subs[1:], strict=False):
        assert a.p2.x == pytest.approx(b.p1.x, abs=1e-6)
        assert a.p2.y == pytest.approx(b.p1.y, abs=1e-6)


def test_segment_split_at_points_unsorted_input_same_result(test_segment):
    """Points given in reverse order must produce the same splits."""
    s = test_segment
    pa, pb = s.point_at_t(0.3), s.point_at_t(0.7)
    forward = s.split_at_points([pa, pb])
    backward = s.split_at_points([pb, pa])
    assert len(forward) == len(backward)
    for a, b in zip(forward, backward, strict=False):
        assert a.length == pytest.approx(b.length, abs=1e-6)


def test_segment_split_at_endpoint_produces_no_degenerate_stub(test_segment):
    """A point coinciding with p1 or p2 must be silently dropped."""
    s = test_segment
    subs = s.split_at_points([s.p1, s.point_at_t(0.5)])
    # p1 is within tolerance of endpoint → only one split point remains
    assert len(subs) == 2


def test_segment_split_at_points_all_near_endpoints_returns_original(test_segment):
    """When all points collapse onto endpoints, return the original segment."""
    s = test_segment
    subs = s.split_at_points([s.p1, s.p2])
    assert len(subs) == 1
    assert subs[0].length == pytest.approx(s.length, abs=1e-6)


# =============================================================================
# Ray Tests
# =============================================================================


def test_ray_creation():
    """Test ray creation and attributes.

    Verifies that a Ray can be created with an origin point and direction,
    and that the direction vector is normalized properly.
    """
    origin = Point(1, 2)
    direction = (3, 4)
    ray = Ray(origin, direction)
    assert ray.origin == origin

    # Direction should be normalized
    magnitude = math.sqrt(3 * 3 + 4 * 4)
    expected = np.array([3 / magnitude, 4 / magnitude])
    np.testing.assert_almost_equal(ray.direction, expected)

    # Test with zero vector
    with pytest.raises(ValueError):
        Ray(origin, (0, 0))

    # Test with numpy array
    ray_np = Ray(origin, np.array([3, 4]))
    np.testing.assert_almost_equal(ray_np.direction, expected)

    # Test access to coords directly
    np.testing.assert_almost_equal(origin.coords, np.array([1, 2]))


def test_ray_point_at_distance():
    """Test getting a point at a specified distance on the ray.

    Ray and Line use point_at_distance() (directional distance along an
    infinite object). Segment and CubicBezier use point_at_length()
    (arc length on a bounded path). The two are semantically distinct.
    """
    ray = Ray(Point(0, 0), (1, 0))  # Ray along x-axis
    point = ray.point_at_distance(5)
    assert point.x == pytest.approx(5.0)
    assert point.y == pytest.approx(0.0)

    # Ray along y-axis
    ray = Ray(Point(0, 0), (0, 1))
    point = ray.point_at_distance(3)
    assert point.x == pytest.approx(0.0)
    assert point.y == pytest.approx(3.0)
    np.testing.assert_almost_equal(point.coords, np.array([0.0, 3.0]))

    ray = Ray(Point(1, 1), (1, 1))  # 45-degree ray
    point = ray.point_at_distance(math.sqrt(2))
    assert point.x == pytest.approx(2.0)
    assert point.y == pytest.approx(2.0)


def test_ray_contains_point():
    """Test if a point lies on the ray.

    Verifies that the contains_point method correctly determines
    whether a given point lies on the ray within tolerance.
    """
    ray = Ray(Point(0, 0), (3, 4))

    # Points on the ray
    assert ray.contains_point(Point(0, 0))  # Origin
    assert ray.contains_point(Point(0.6, 0.8))  # At distance 1
    assert ray.contains_point(Point(3, 4))  # At distance 5
    assert ray.contains_point(Point(6, 8))  # At distance 10

    # Points not on the ray
    assert not ray.contains_point(Point(1, 0))
    assert not ray.contains_point(Point(-0.6, -0.8))  # Wrong direction


def test_ray_line_intersection():
    """Test intersection between ray and line.

    Verifies that the intersect_with method correctly finds the
    intersection point between a ray and a line segment.
    """
    ray = Ray(Point(0, 0), (1, 1))
    line = Segment(Point(0, 10), Point(10, 0))

    # Ray and line should intersect at (5, 5)
    intersections = intersect(ray, line)
    assert len(intersections) == 1
    assert intersections[0].x == pytest.approx(5.0)
    assert intersections[0].y == pytest.approx(5.0)
    np.testing.assert_almost_equal(intersections[0].coords, np.array([5.0, 5.0]))

    # Ray pointing away from line
    ray = Ray(Point(0, 0), (-1, -1))
    assert intersect(ray, line) == []


def test_ray_ray_intersection():
    """Test intersection between two rays.

    Verifies that the intersect_with method correctly finds the
    intersection point between two rays and handles special cases
    like parallel rays and rays pointing away from each other.
    """
    ray1 = Ray(Point(0, 0), (1, 1))
    ray2 = Ray(Point(0, 10), (1, -1))

    # Rays should intersect at (5, 5)
    intersections = intersect(ray1, ray2)
    assert len(intersections) == 1
    assert intersections[0].x == pytest.approx(5.0)
    assert intersections[0].y == pytest.approx(5.0)

    # Parallel rays
    ray3 = Ray(Point(0, 0), (1, 1))
    ray4 = Ray(Point(1, 0), (1, 1))
    assert intersect(ray3, ray4) == []

    # Rays pointing away from each other
    ray5 = Ray(Point(0, 0), (1, 0))
    ray6 = Ray(Point(10, 0), (-1, 0))
    assert intersect(ray5, ray6) == []


# =============================================================================
# Circle Tests
# =============================================================================


def test_circle_creation():
    """Test circle creation and attributes.

    Verifies that a Circle can be created with a center point and radius,
    and that invalid radii are properly rejected.
    """
    center = Point(2, 3)
    radius = 5
    circle = Circle(center, radius)
    assert circle.center == center
    assert circle.radius == radius

    # Test invalid radius
    with pytest.raises(ValueError):
        Circle(center, 0)
    with pytest.raises(ValueError):
        Circle(center, -1)


def test_circle_area_and_circumference():
    """Test area and circumference calculations.

    Verifies that the area and circumference properties
    correctly calculate these values for the circle.
    """
    circle = Circle(Point(0, 0), 2)
    assert circle.area == pytest.approx(math.pi * 4)
    assert circle.circumference == pytest.approx(math.pi * 4)


def test_circle_contains_point():
    """Test if a point lies on the circle.

    Verifies that the contains_point method correctly determines
    whether a given point lies on the circle boundary within tolerance.
    """
    circle = Circle(Point(0, 0), 5)

    # Points on the circle
    assert circle.contains_point(Point(5, 0))
    assert circle.contains_point(Point(0, 5))
    assert circle.contains_point(Point(3, 4))  # 3-4-5 triangle

    # Points not on the circle
    assert not circle.contains_point(Point(0, 0))  # Center
    assert not circle.contains_point(Point(3, 3))  # Inside
    assert not circle.contains_point(Point(10, 0))  # Outside


def test_circle_contains_point_inside():
    """Test if a point is inside the circle.

    Verifies that the contains_point_inside method correctly determines
    whether a given point is inside the circle, with options to include
    or exclude the boundary.
    """
    circle = Circle(Point(0, 0), 5)

    # Inside points
    assert circle.contains_point_inside(Point(0, 0))  # Center
    assert circle.contains_point_inside(Point(3, 0))  # Inside

    # Boundary
    assert circle.contains_point_inside(Point(5, 0), include_boundary=True)
    assert not circle.contains_point_inside(Point(5, 0), include_boundary=False)

    # Outside
    assert not circle.contains_point_inside(Point(10, 0))


def test_circle_point_at_angle():
    """Test getting a point on the circle at a specified angle.

    Verifies that the point_at_angle method correctly calculates
    points on the circle boundary at specified angles.
    """
    circle = Circle(Point(0, 0), 1)

    # Points at cardinal directions
    point = circle.point_at_angle(0)  # Right
    assert point.x == pytest.approx(1.0)
    assert point.y == pytest.approx(0.0)

    point = circle.point_at_angle(math.pi / 2)  # Top
    assert point.x == pytest.approx(0.0)
    assert point.y == pytest.approx(1.0)

    point = circle.point_at_angle(math.pi)  # Left
    assert point.x == pytest.approx(-1.0)
    assert point.y == pytest.approx(0.0)

    point = circle.point_at_angle(3 * math.pi / 2)  # Bottom
    assert point.x == pytest.approx(0.0)
    assert point.y == pytest.approx(-1.0)


def test_circle_line_intersection():
    """Test intersection between circle and line.

    Verifies that the intersect_with method correctly finds intersection
    points between a circle and a line, including special cases like
    tangent lines and non-intersecting lines.
    """
    circle = Circle(Point(0, 0), 5)

    # Line through the center
    line = Segment(Point(-10, 0), Point(10, 0))
    intersections = intersect(circle, line)
    assert len(intersections) == 2  # Two intersection points
    points = sorted([p.x for p in intersections])
    assert points[0] == pytest.approx(-5.0)
    assert points[1] == pytest.approx(5.0)

    # Tangent line
    line = Segment(Point(0, 5), Point(10, 5))
    intersections = intersect(circle, line)
    assert len(intersections) == 1  # One point only
    assert intersections[0].x == pytest.approx(0.0)
    assert intersections[0].y == pytest.approx(5.0)

    # Line that doesn't intersect
    line = Segment(Point(0, 10), Point(10, 10))
    assert intersect(circle, line) == []


def test_circle_ray_intersection():
    """Test intersection between circle and ray.

    Verifies that the intersect_with method correctly finds intersection
    points between a circle and a ray, including special cases like rays
    intersecting at one or two points, and rays pointing away from the circle.
    """
    circle = Circle(Point(0, 0), 5)

    # Ray that intersects twice
    ray = Ray(Point(-10, 0), (1, 0))
    intersections = intersect(circle, ray)
    assert len(intersections) == 2  # Two intersection points
    points = sorted([p.x for p in intersections])
    assert points[0] == pytest.approx(-5.0)
    assert points[1] == pytest.approx(5.0)

    # Ray that intersects once
    ray = Ray(Point(0, 5), (1, 0))
    intersections = intersect(circle, ray)
    assert len(intersections) == 1  # One point only
    assert intersections[0].x == pytest.approx(0.0)
    assert intersections[0].y == pytest.approx(5.0)

    # Ray pointing away from circle
    ray = Ray(Point(-10, 0), (-1, 0))
    assert intersect(circle, ray) == []


def test_circle_circle_intersection():
    """Test intersection between two circles.

    Verifies that the intersect_with method correctly finds intersection
    points between two circles, including special cases like externally
    touching circles, non-intersecting circles, and one circle inside another.
    """
    circle1 = Circle(Point(0, 0), 5)

    # Circles that intersect at two points
    circle2 = Circle(Point(8, 0), 5)
    intersections = intersect(circle1, circle2)
    assert len(intersections) == 2  # Two intersection points
    points = sorted([(p.x, p.y) for p in intersections])
    assert points[0][0] == pytest.approx(4.0)
    assert points[0][1] == pytest.approx(-3.0)
    assert points[1][0] == pytest.approx(4.0)
    assert points[1][1] == pytest.approx(3.0)

    # Circles that touch at one point (externally)
    circle3 = Circle(Point(10, 0), 5)
    intersections = intersect(circle1, circle3)
    assert len(intersections) == 1  # One point only
    assert intersections[0].x == pytest.approx(5.0)
    assert intersections[0].y == pytest.approx(0.0)

    # Circles that don't intersect
    circle4 = Circle(Point(20, 0), 5)
    assert intersect(circle1, circle4) == []

    # One circle inside the other (no intersection)
    circle5 = Circle(Point(0, 0), 2)
    assert intersect(circle1, circle5) == []


# =============================================================================
# Miter Corner Tests (reflex-corner detection)
# =============================================================================


def test_miter_corner_convex_extends_outward():
    """A convex 90° corner must produce a miter point outside the original seams."""
    # Corner between top (→) and right (↓): expected miter at (110, -10)
    ga = Segment(Point(0, -10), Point(100, -10))  # horizontal, going right
    gb = Segment(Point(110, 0), Point(110, 100))  # vertical, going down
    corner = miter_corner(ga, gb, 10.0)
    # Miter should extend to (110, -10) — forward along ta
    assert corner.x == pytest.approx(110.0, abs=1e-3)
    assert corner.y == pytest.approx(-10.0, abs=1e-3)


def test_miter_corner_reflex_returns_bevel_midpoint():
    """A reflex (concave) corner must return the bevel midpoint, not a spike.

    Simulate a U-shaped notch: two offset segments whose junction is concave.
    """
    # ga ends at (10,0) going right, gb starts at (10, 20) going right — not aligned
    ga2 = Segment(Point(0, 0), Point(10, 0))  # → end=(10,0)
    gb2 = Segment(Point(10, 20), Point(20, 20))  # → start=(10,20) — not aligned
    # The intersection is behind end_a (dot < 0), so bevel midpoint expected
    corner2 = miter_corner(ga2, gb2, 5.0)
    bevel_x = 0.5 * (10.0 + 10.0)
    bevel_y = 0.5 * (0.0 + 20.0)
    assert corner2.x == pytest.approx(bevel_x, abs=1e-3)
    assert corner2.y == pytest.approx(bevel_y, abs=1e-3)


def test_miter_corner_reflex_180_degree_returns_bevel():
    """Two anti-parallel segments (U-turn) produce bevel midpoint, not infinity."""
    # ga: (0,0)→(10,0) ta=(+1,0)
    # gb: (10,0)→(0,0)  tb=(-1,0)  — exact anti-parallel (180° turn)
    ga = Segment(Point(0, 0), Point(10, 0))
    gb = Segment(Point(10, 0), Point(0, 0))
    corner = miter_corner(ga, gb, 5.0)
    # Lines are parallel so _intersect_lines returns None → bevel midpoint
    assert corner.x == pytest.approx(10.0, abs=1e-3)
    assert corner.y == pytest.approx(0.0, abs=1e-3)


def test_miter_corner_convex_not_clamped_to_bevel():
    """A normal outward 90° corner must NOT be treated as reflex."""
    # ga going right (+x), gb going down (+y) — standard outward CW corner
    ga = Segment(Point(0, -10), Point(90, -10))  # → ta=(+1,0)
    gb = Segment(Point(110, 0), Point(110, 90))  # ↓ tb=(0,+1)
    corner = miter_corner(ga, gb, 10.0)
    # Must NOT return bevel midpoint (50, 45) — must return miter (110,-10)
    assert corner.x == pytest.approx(110.0, abs=1e-2)
    assert corner.y == pytest.approx(-10.0, abs=1e-2)


# =============================================================================
# Round Corner Tests (cubic Bézier arc approximation)
# =============================================================================


def test_round_corner_convex_90deg_returns_cubic_bezier():
    """A convex 90° corner returns a CubicBezier, not a Point."""
    ga = Segment(Point(0, -10), Point(100, -10))  # → ta=(+1,0)
    gb = Segment(Point(110, 0), Point(110, 100))  # ↓ tb=(0,+1)
    result = round_corner(ga, gb)
    assert isinstance(result, CubicBezier)


def test_round_corner_arc_starts_at_end_of_ga():
    """The arc must start exactly at geom_end(ga)."""
    ga = Segment(Point(0, -10), Point(100, -10))
    gb = Segment(Point(110, 0), Point(110, 100))
    arc = round_corner(ga, gb)
    assert isinstance(arc, CubicBezier)
    assert arc.p0.x == pytest.approx(100.0, abs=1e-6)
    assert arc.p0.y == pytest.approx(-10.0, abs=1e-6)


def test_round_corner_arc_ends_at_start_of_gb():
    """The arc must end exactly at geom_start(gb)."""
    ga = Segment(Point(0, -10), Point(100, -10))
    gb = Segment(Point(110, 0), Point(110, 100))
    arc = round_corner(ga, gb)
    assert isinstance(arc, CubicBezier)
    assert arc.p3.x == pytest.approx(110.0, abs=1e-6)
    assert arc.p3.y == pytest.approx(0.0, abs=1e-6)


def test_round_corner_arc_stays_close_to_true_circle():
    """All points on the Bézier arc must lie within 0.03 % of the true radius.

    Setup: ga ends at (100, -10), gb starts at (110, 0).  Tangents (+1,0)
    and (0,+1).  The arc centre is at (100, 0): the perpendicular to
    ta=(+1,0) through end_a=(100,-10) gives x=100; the perpendicular to
    tb=(0,+1) through start_b=(110,0) gives y=0.  r = 10 mm.
    Max theoretical error for k=4/3·tan(θ/4) at 90° is 0.027 % of r.
    """
    import math as _m

    ga = Segment(Point(0, -10), Point(100, -10))
    gb = Segment(Point(110, 0), Point(110, 100))
    arc = round_corner(ga, gb)
    assert isinstance(arc, CubicBezier)
    cx, cy, r = 100.0, 0.0, 10.0  # correct arc centre
    tolerance = r * 0.0003  # 0.03 % of radius = 0.003 mm
    for k in range(21):
        pt = arc.point_at_t(k / 20)
        radial_err = abs(_m.hypot(pt.x - cx, pt.y - cy) - r)
        assert radial_err < tolerance, (
            f"t={k / 20:.2f}: radial error {radial_err:.5f} mm > {tolerance:.5f} mm"
        )


def test_round_corner_reflex_returns_point():
    """A reflex corner returns a Point (bevel midpoint), not a CubicBezier."""
    # ga going right, end at (10,0); gb going left, start at (10,0) — hairpin
    ga = Segment(Point(0, 0), Point(10, 0))
    gb = Segment(Point(10, 0), Point(0, 0))
    result = round_corner(ga, gb)
    assert isinstance(result, Point)


def test_round_corner_parallel_tangents_returns_point():
    """Parallel tangents (straight continuation) return a Point."""
    ga = Segment(Point(0, 0), Point(10, 0))
    gb = Segment(Point(10, 0), Point(20, 0))
    result = round_corner(ga, gb)
    # Angle ≈ 0 → falls back to bevel midpoint (a Point)
    assert isinstance(result, Point)


def test_round_corner_180_degree_returns_point():
    """Anti-parallel segments (U-turn) return a Point fallback."""
    ga = Segment(Point(0, 5), Point(10, 5))  # →
    gb = Segment(Point(10, 5), Point(0, 5))  # ← (anti-parallel)
    result = round_corner(ga, gb)
    assert isinstance(result, Point)


def test_round_corner_control_points_on_tangent_lines():
    """Both control points must lie on the respective tangent lines of the arc."""
    ga = Segment(Point(0, -10), Point(100, -10))  # → ta=(+1,0)
    gb = Segment(Point(110, 0), Point(110, 100))  # ↓ tb=(0,+1)
    arc = round_corner(ga, gb)
    assert isinstance(arc, CubicBezier)
    # cp1 must be east of p0 (same y), cp2 must be north of p3 (same x)
    assert arc.p1.y == pytest.approx(arc.p0.y, abs=1e-6)  # tangent along +x
    assert arc.p2.x == pytest.approx(arc.p3.x, abs=1e-6)  # tangent along -y


# =============================================================================
# Dart Roof Tests (Abnäherdach)
# =============================================================================


@pytest.fixture
def symmetric_dart():
    """Helper: symmetric dart centered at origin on the x-axis."""
    width, depth = 40.0, 80.0
    center = Point(0.0, 0.0)
    leg_a = Point(-width / 2, 0.0)
    leg_b = Point(+width / 2, 0.0)
    tip = Point(0.0, -depth)  # tip below the seam line
    return Dart(leg_a=leg_a, leg_b=leg_b, center=center, tip=tip)


def test_dart_roof_returns_point_instance(symmetric_dart):
    dart = symmetric_dart
    roof = dart.roof
    assert isinstance(roof, Point)


def test_dart_roof_points_above_original_legs(symmetric_dart):
    """Roof points must protrude *away* from the tip (outward past the seam).

    For a dart where the tip is below the seam (y < 0), the Abnäherdach
    crown protrudes above the seam (y > 0) so that after sewing the edge
    lies flush.
    """
    dart = symmetric_dart
    roof = dart.roof
    # tip is at y=-80; seam is at y=0; roof points should be at y > 0
    assert roof.y > dart.center.y


def test_dart_roof_height_formula(symmetric_dart):
    """Verify the right-triangle formula: h = half_width * cos(α) / sin(α)."""
    import math

    dart = symmetric_dart
    roof_height = np.linalg.norm(dart.roof.coords - dart.center.coords)

    assert float(math.tan(dart.intake_angle) * (dart.width / 2)) == pytest.approx(
        roof_height, abs=1e-5
    )


def test_dart_roof_zero_width_no_displacement():
    """A dart with zero-length seam has no roof displacement."""
    tip = Point(0.0, -50.0)
    center = Point(0.0, 0.0)
    dart = Dart(leg_a=center, leg_b=center, center=center, tip=tip)
    roof = dart.roof
    assert roof.x == pytest.approx(dart.center.x, abs=1e-6)
    assert roof.y == pytest.approx(dart.center.y, abs=1e-6)


def test_dart_roof_rise_increases_with_wider_dart():
    """A wider dart (larger intake angle) should produce a larger roof rise."""
    # Narrow dart
    width_narrow, depth = 20.0, 80.0
    center = Point(0.0, 0.0)
    leg_a_narrow = Point(-width_narrow / 2, 0.0)
    leg_b_narrow = Point(+width_narrow / 2, 0.0)
    tip = Point(0.0, -depth)
    dart_narrow = Dart(leg_a=leg_a_narrow, leg_b=leg_b_narrow, center=center, tip=tip)

    # Wide dart
    width_wide = 60.0
    leg_a_wide = Point(-width_wide / 2, 0.0)
    leg_b_wide = Point(+width_wide / 2, 0.0)
    dart_wide = Dart(leg_a=leg_a_wide, leg_b=leg_b_wide, center=center, tip=tip)

    # For this setup tip is at y=-80, seam at y=0; roof is at y > 0
    rise_narrow = np.linalg.norm(dart_narrow.roof.coords - dart_narrow.center.coords)
    rise_wide = np.linalg.norm(dart_wide.roof.coords - dart_wide.center.coords)
    assert rise_wide > rise_narrow


# =============================================================================
# Additional coverage: Point, Segment, _LinearGeom gaps
# =============================================================================


def test_point_str_with_name_contains_name():
    """Point.__str__ with a name set includes that name (Point is a frozen dataclass)."""
    p = Point(1.0, 2.0)
    object.__setattr__(p, "name", "side_seam")
    assert "side_seam" in str(p)


def test_point_eq_non_point_returns_not_implemented():
    """Point.__eq__ with a non-Point returns NotImplemented."""
    result = Point(0, 0).__eq__("not a point")
    assert result is NotImplemented


def test_point_hash_equal_points_match():
    """Two identical Points have the same hash."""
    p1 = Point(3.0, 7.0)
    p2 = Point(3.0, 7.0)
    assert hash(p1) == hash(p2)


def test_point_distance_to_numpy_array():
    """Point.distance_to also accepts a numpy array (non-Point branch)."""
    p = Point(3.0, 4.0)
    assert p.distance_to(p.coords) == pytest.approx(0.0)


def test_segment_from_direction_zero_vector_raises():
    """Segment.from_direction raises ValueError when start == through."""
    p = Point(0, 0)
    with pytest.raises(ValueError):
        from sewpat.geometry import Segment as S

        S.from_direction(p, p, 10.0)


def test_segment_split_at_points_boundary_point_returns_one():
    """split_at_points with a point at the endpoint returns a single segment."""
    seg = Segment(Point(0, 0), Point(100, 0))
    # Point exactly at p1 is filtered out by the eps guard
    result = seg.split_at_points([Point(0, 0)])
    assert len(result) == 1


def test_linear_geom_point_perpendicular_via_segment():
    """_LinearGeom.point_perpendicular returns correctly offset point."""
    from sewpat.geometry._primitives import Segment as Seg

    seg = Seg(Point(0, 0), Point(100, 0))
    pt = seg.point_perpendicular(distance=20, arc_length=50)
    assert pt.x == pytest.approx(50)
    assert pt.y == pytest.approx(20)


# =============================================================================
# rep_point — one test per geometry type
# =============================================================================


def test_point_rep_point_is_self():
    p = Point(3.0, 7.0)
    assert p.rep_point() is p


def test_segment_rep_point_is_midpoint():
    seg = Segment(Point(0, 0), Point(10, 0))
    rep = seg.rep_point()
    assert rep.x == pytest.approx(5.0)
    assert rep.y == pytest.approx(0.0)


def test_rect_rep_point_is_centre():
    r = Rect(origin=Point(0, 0), width=10.0, height=4.0)
    rep = r.rep_point()
    assert rep.x == pytest.approx(5.0)
    assert rep.y == pytest.approx(2.0)


def test_triangle_rep_point_is_centroid():
    tri = Triangle(Point(0, 0), Point(6, 0), Point(0, 6))
    rep = tri.rep_point()
    assert rep.x == pytest.approx(2.0)
    assert rep.y == pytest.approx(2.0)


def test_infobox_rep_point_is_position():
    box = InfoBox(position=Point(5.0, 8.0), header="Label")
    rep = box.rep_point()
    assert rep.x == pytest.approx(5.0)
    assert rep.y == pytest.approx(8.0)


def test_circle_rep_point_is_centre():
    c = Circle(center=Point(3.0, -1.0), radius=2.0)
    rep = c.rep_point()
    assert rep.x == pytest.approx(3.0)
    assert rep.y == pytest.approx(-1.0)


def test_ray_has_no_rep_point():
    r = Ray(Point(0, 0), np.array([1.0, 0.0]))
    assert not hasattr(r, "rep_point")


def test_line_has_no_rep_point():
    ln = Line(Point(0, 0), np.array([1.0, 0.0]))
    assert not hasattr(ln, "rep_point")


# =============================================================================
# point_in_sector Tests
# =============================================================================

# Fixed sector: CCW 90° sweeping from right (0°) to up (90°), i.e. first quadrant.
_PIVOT = Point(0.0, 0.0)
_LEG: tuple[float, float] = (1.0, 0.0)  # → 0°
_CUT: tuple[float, float] = (0.0, 1.0)  # ↑ 90°


def test_point_in_sector_interior():
    assert point_in_sector(_PIVOT, _LEG, _CUT, Point(3.0, 3.0)) is True


def test_point_in_sector_on_leg_boundary():
    assert point_in_sector(_PIVOT, _LEG, _CUT, Point(5.0, 0.0)) is True


def test_point_in_sector_on_cut_boundary():
    assert point_in_sector(_PIVOT, _LEG, _CUT, Point(0.0, 5.0)) is True


def test_point_in_sector_below_leg():
    # (1, -1) is at -45°, outside [0°, 90°]
    assert point_in_sector(_PIVOT, _LEG, _CUT, Point(5.0, -5.0)) is False


def test_point_in_sector_behind_pivot():
    # (-1, 0) is at 180°, outside [0°, 90°]
    assert point_in_sector(_PIVOT, _LEG, _CUT, Point(-5.0, 0.0)) is False


def test_point_in_sector_third_quadrant():
    assert point_in_sector(_PIVOT, _LEG, _CUT, Point(-5.0, -5.0)) is False


def test_point_in_sector_at_pivot_returns_false():
    # Distance = 0 → angular position indeterminate
    assert point_in_sector(_PIVOT, _LEG, _CUT, _PIVOT) is False


def test_point_in_sector_parallel_directions_returns_false():
    # Degenerate sector: leg == cut
    assert point_in_sector(_PIVOT, _LEG, _LEG, Point(3.0, 3.0)) is False


def test_point_in_sector_antiparallel_directions_returns_false():
    # Degenerate sector: angle = π
    anti: tuple[float, float] = (-1.0, 0.0)
    assert point_in_sector(_PIVOT, _LEG, anti, Point(0.0, 5.0)) is False


def test_point_in_sector_cw_sector_interior():
    # CW 90°: from up (90°) to right (0°) — sector angle = -π/2
    leg: tuple[float, float] = (0.0, 1.0)
    cut: tuple[float, float] = (1.0, 0.0)
    # (1, 1) at 45° is inside the CW first-quadrant sweep
    assert point_in_sector(_PIVOT, leg, cut, Point(5.0, 5.0)) is True


def test_point_in_sector_cw_sector_outside():
    leg: tuple[float, float] = (0.0, 1.0)
    cut: tuple[float, float] = (1.0, 0.0)
    # (-1, 1) at 135° is outside the CW sweep from 90° to 0°
    assert point_in_sector(_PIVOT, leg, cut, Point(-5.0, 5.0)) is False


def test_point_in_sector_offset_pivot():
    # Shift pivot to (10, 10) — same angular geometry
    pivot = Point(10.0, 10.0)
    # (15, 15) is 45° from pivot → inside
    assert point_in_sector(pivot, _LEG, _CUT, Point(15.0, 15.0)) is True
    # (5, 15) is 135° from pivot → outside
    assert point_in_sector(pivot, _LEG, _CUT, Point(5.0, 15.0)) is False
