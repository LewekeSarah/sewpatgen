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
    Point,
    Ray,
    Segment,
    intersect,
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
# CubicBezier
# ------------------------------------------------------------------


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
# CubicBezier Bounding Box Tests
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
# CubicBezier Intersection Tests
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
# CubicBezier New Methods Tests
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
# CubicBezier Split At Points Tests
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
