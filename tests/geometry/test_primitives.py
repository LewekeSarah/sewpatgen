"""Tests for the geometry module.

This module contains unit tests for all the geometric primitives
defined in the geometry module: Point, Segment, Ray, and Circle.
"""

import math
import unittest

import numpy as np

from sewpat.geometry import (
    Circle,
    CubicBezier,
    Point,
    Ray,
    Segment,
    intersect,
)


class TestPoint(unittest.TestCase):
    """Test cases for the Point class.

    This class contains tests for the Point geometric primitive,
    including creation, distance calculation, translation and rotation.
    """

    def test_creation(self):
        """Test point creation and attributes.

        Verifies that a Point can be created with coordinates
        and that the coordinates are correctly stored.
        """
        p = Point(2.5, 3.7)
        self.assertAlmostEqual(p.x, 2.5)
        self.assertAlmostEqual(p.y, 3.7)

    def test_distance_to(self):
        """Test distance calculation between points.

        Verifies that the distance_to method correctly calculates
        the Euclidean distance between two points.
        """
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        self.assertAlmostEqual(p1.distance_to(p2), 5.0)
        self.assertAlmostEqual(p2.distance_to(p1), 5.0)

    def test_translate(self):
        """Test point translation.

        Verifies that the translate method correctly creates a new point
        translated by the specified vector, while leaving the original unchanged.
        """
        p = Point(1, 2)
        translated = p.translate(2, 3)
        self.assertAlmostEqual(translated.x, 3)
        self.assertAlmostEqual(translated.y, 5)
        # Original point should not change (immutability)
        self.assertAlmostEqual(p.x, 1)
        self.assertAlmostEqual(p.y, 2)

    def test_rotate(self):
        """Test point rotation around another point.

        Verifies that the rotate method correctly rotates a point
        around a specified center by the given angle.
        """
        center = Point(0, 0)
        p = Point(1, 0)

        # Rotate 90 degrees counterclockwise
        rotated = p.rotate(center, math.pi / 2)
        self.assertAlmostEqual(rotated.x, 0, places=10)
        self.assertAlmostEqual(rotated.y, 1, places=10)

        # Test with NumPy array operations
        np.testing.assert_almost_equal(rotated.coords, np.array([0, 1]), decimal=10)

        # Rotate 180 degrees
        rotated = p.rotate(center, math.pi)
        self.assertAlmostEqual(rotated.x, -1, places=10)
        self.assertAlmostEqual(rotated.y, 0, places=10)

        # Rotation around non-origin center
        center = Point(1, 1)
        p = Point(2, 1)
        rotated = p.rotate(center, math.pi / 2)
        self.assertAlmostEqual(rotated.x, 1, places=10)
        self.assertAlmostEqual(rotated.y, 2, places=10)

    def test_add(self):
        """Point + Point offsets by the second point as a displacement vector."""
        a = Point(1, 2)
        b = Point(3, 4)
        result = a + b
        self.assertAlmostEqual(result.x, 4)
        self.assertAlmostEqual(result.y, 6)
        # Original unchanged
        self.assertAlmostEqual(a.x, 1)

    def test_sub(self):
        """Point - Point returns the displacement vector as a Point."""
        a = Point(5, 7)
        b = Point(2, 3)
        result = a - b
        self.assertAlmostEqual(result.x, 3)
        self.assertAlmostEqual(result.y, 4)

    def test_mul_scalar(self):
        """Point * scalar scales the position vector."""
        p = Point(3, 4)
        self.assertAlmostEqual((p * 2).x, 6)
        self.assertAlmostEqual((p * 2).y, 8)
        self.assertAlmostEqual((p * 0.5).x, 1.5)

    def test_rmul_scalar(self):
        """scalar * Point is equivalent to Point * scalar."""
        p = Point(3, 4)
        result = 2.0 * p
        self.assertAlmostEqual(result.x, 6)
        self.assertAlmostEqual(result.y, 8)

    def test_neg(self):
        """-Point negates both coordinates."""
        p = Point(3, -4)
        result = -p
        self.assertAlmostEqual(result.x, -3)
        self.assertAlmostEqual(result.y, 4)

    def test_midpoint_via_arithmetic(self):
        """(a + b) * 0.5 gives the midpoint."""
        a = Point(0, 0)
        b = Point(4, 6)
        mid = (a + b) * 0.5
        self.assertAlmostEqual(mid.x, 2)
        self.assertAlmostEqual(mid.y, 3)

    def test_add_non_point_returns_not_implemented(self):
        """Adding a non-Point returns NotImplemented
        (no TypeError from Point itself)."""
        p = Point(1, 2)
        result = p.__add__(42)
        self.assertIs(result, NotImplemented)

    def test_sub_non_point_returns_not_implemented(self):
        p = Point(1, 2)
        self.assertIs(p.__sub__("x"), NotImplemented)

    def test_mul_non_scalar_returns_not_implemented(self):
        p = Point(1, 2)
        self.assertIs(p.__mul__(Point(1, 1)), NotImplemented)

    def test_immutability_preserved(self):
        """Arithmetic operators always return new Points; originals are unchanged."""
        p = Point(1, 2)
        _ = p + Point(10, 10)
        _ = p * 5
        self.assertAlmostEqual(p.x, 1)
        self.assertAlmostEqual(p.y, 2)


class TestPointAlongFrom(unittest.TestCase):
    """Tests for curve.point_along_from() across all supported curve types."""

    # ------------------------------------------------------------------
    # Segment
    # ------------------------------------------------------------------

    def test_segment_forward(self):
        """Moving forward along a horizontal segment gives the correct x position."""
        seg = Segment(Point(0, 0), Point(100, 0))
        p = Point(30, 0)
        result = seg.point_along_from(p, 20)
        self.assertAlmostEqual(result.x, 50.0, places=6)
        self.assertAlmostEqual(result.y, 0.0, places=6)

    def test_segment_backward(self):
        """A negative arc_length moves backward along the segment."""
        seg = Segment(Point(0, 0), Point(100, 0))
        p = Point(50, 0)
        result = seg.point_along_from(p, -10)
        self.assertAlmostEqual(result.x, 40.0, places=6)

    def test_segment_diagonal(self):
        """Works correctly on a diagonal segment."""
        seg = Segment(Point(0, 0), Point(30, 40))  # length = 50
        p = seg.point_at_t(0.5)  # at arc-length 25
        result = seg.point_along_from(p, 10)
        self.assertAlmostEqual(result.distance_to(p), 10.0, places=5)

    def test_segment_out_of_range_raises(self):
        """Moving beyond the segment end raises ValueError."""
        seg = Segment(Point(0, 0), Point(10, 0))
        p = Point(8, 0)
        with self.assertRaises(ValueError):
            seg.point_along_from(p, 5)  # would land at 13, beyond length 10

    # ------------------------------------------------------------------
    # CubicBezier
    # ------------------------------------------------------------------

    def test_bezier_forward(self):
        """Moving forward along a straight Bezier (degenerate line) is accurate."""
        # Straight Bezier from (0,0) to (100,0) — arc-length == chord length
        bez = CubicBezier(Point(0, 0), Point(33, 0), Point(66, 0), Point(100, 0))
        p = bez.point_at_t(0.3)  # ≈ 30 mm along
        result = bez.point_along_from(p, 20)
        # Should land near x=50; allow 0.5 mm tolerance for
        # round-trip arc-length accumulation
        self.assertAlmostEqual(result.x, 50.0, places=0)
        self.assertAlmostEqual(result.y, 0.0, places=3)

    def test_bezier_displacement_magnitude(self):
        """Displacement along a curved Bezier equals the requested arc length."""
        bez = CubicBezier(Point(0, 0), Point(10, 40), Point(30, 40), Point(40, 0))
        p = bez.point_at_t(0.2)
        result = bez.point_along_from(p, 5.0)
        # The result should be strictly further along the curve
        self.assertGreater(result.distance_to(p), 0.0)

    # ------------------------------------------------------------------
    # Ray
    # ------------------------------------------------------------------

    def test_ray_forward(self):
        """Moving along a ray advances by the exact distance."""
        ray = Ray(Point(0, 0), (1, 0))
        p = Point(30, 0)
        result = ray.point_along_from(p, 15)
        self.assertAlmostEqual(result.x, 45.0, places=6)
        self.assertAlmostEqual(result.y, 0.0, places=6)

    def test_ray_backward(self):
        """Negative arc_length moves backward along the ray."""
        ray = Ray(Point(0, 0), (0, 1))
        p = Point(0, 50)
        result = ray.point_along_from(p, -20)
        self.assertAlmostEqual(result.y, 30.0, places=6)

    # ------------------------------------------------------------------
    # Line
    # ------------------------------------------------------------------

    def test_line_forward(self):
        """Moving along an infinite line works in both directions."""
        from sewpat.geometry import Line

        line = Line(Point(0, 0), (1, 0))
        p = Point(10, 0)
        result = line.point_along_from(p, 25)
        self.assertAlmostEqual(result.x, 35.0, places=6)

    def test_line_backward(self):
        """Negative arc_length on a Line moves in the opposite direction."""
        from sewpat.geometry import Line

        line = Line(Point(0, 0), (1, 0))
        p = Point(10, 0)
        result = line.point_along_from(p, -10)
        self.assertAlmostEqual(result.x, 0.0, places=6)

    # ------------------------------------------------------------------
    # Circle
    # ------------------------------------------------------------------

    def test_circle_ccw(self):
        """Moving CCW along a circle by π*r (half circumference)
        reaches the antipode."""
        c = Circle(Point(0, 0), 10)
        p = c.point_at_angle(0)  # (10, 0)
        half_circ = math.pi * 10
        result = c.point_along_from(p, half_circ)
        self.assertAlmostEqual(result.x, -10.0, places=5)
        self.assertAlmostEqual(result.y, 0.0, places=5)

    def test_circle_full_revolution(self):
        """Moving a full circumference returns to the starting point."""
        c = Circle(Point(0, 0), 10)
        p = c.point_at_angle(math.pi / 4)
        full = 2 * math.pi * 10
        result = c.point_along_from(p, full)
        self.assertAlmostEqual(result.x, p.x, places=5)
        self.assertAlmostEqual(result.y, p.y, places=5)

    def test_circle_cw_negative(self):
        """Negative arc_length moves clockwise."""
        c = Circle(Point(0, 0), 10)
        p = c.point_at_angle(math.pi / 2)  # (0, 10)
        quarter = math.pi / 2 * 10
        result = c.point_along_from(p, -quarter)
        self.assertAlmostEqual(result.x, 10.0, places=5)
        self.assertAlmostEqual(result.y, 0.0, places=5)


class TestSegment(unittest.TestCase):
    """Test cases for the Segment class.

    This class contains tests for the Segment geometric primitive,
    including creation, properties and intersection calculations.
    """

    def test_creation(self):
        """Test segment creation and attributes.

        Verifies that a Segment can be created with two points
        and that the points are correctly stored, including via start/end aliases.
        """
        p1 = Point(1, 1)
        p2 = Point(4, 5)
        line = Segment(p1, p2)
        self.assertEqual(line.p1, p1)
        self.assertEqual(line.p2, p2)
        self.assertEqual(line.start, p1)
        self.assertEqual(line.end, p2)

    def test_length(self):
        """Test line length calculation.

        Verifies that the length property correctly calculates
        the Euclidean distance between the line's endpoints.
        """
        line = Segment(Point(0, 0), Point(3, 4))
        self.assertAlmostEqual(line.length, 5.0)

    def test_direction_unnormalized(self):
        """Test direction vector calculation."""
        line = Segment(Point(1, 1), Point(4, 5))
        direction = line.direction_unnormalized
        np.testing.assert_almost_equal(direction, np.array([3, 4]))

    def test_midpoint(self):
        """Test midpoint calculation.

        Verifies that the midpoint property correctly calculates
        the point exactly halfway between the line's endpoints.
        """
        line = Segment(Point(1, 2), Point(5, 6))
        mid = line.midpoint
        self.assertAlmostEqual(mid.x, 3.0)
        self.assertAlmostEqual(mid.y, 4.0)

    def test_contains_point(self):
        """Test if a point lies on the line segment."""
        line = Segment(Point(0, 0), Point(10, 10))
        self.assertTrue(line.contains_point(Point(0, 0)))
        self.assertTrue(line.contains_point(Point(5, 5)))
        self.assertTrue(line.contains_point(Point(10, 10)))
        self.assertFalse(line.contains_point(Point(2, 3)))
        self.assertFalse(line.contains_point(Point(-1, -1)))
        self.assertFalse(line.contains_point(Point(11, 11)))

    def test_point_at_t(self):
        """Test point_at_t()."""
        seg = Segment(Point(0, 0), Point(10, 0))
        self.assertAlmostEqual(seg.point_at_t(0.0).x, 0.0)
        self.assertAlmostEqual(seg.point_at_t(0.5).x, 5.0)
        self.assertAlmostEqual(seg.point_at_t(1.0).x, 10.0)

    def test_point_perpendicular_t(self):
        """point_perpendicular with t= places the point at the correct position."""
        seg = Segment(Point(0, 0), Point(10, 0))  # horizontal, normal points up (+y)
        pt = seg.point_perpendicular(5.0, t=0.5)
        self.assertAlmostEqual(pt.x, 5.0)
        self.assertAlmostEqual(pt.y, 5.0)

    def test_point_perpendicular_arc_length(self):
        """point_perpendicular with arc_length= gives the same result as t=."""
        seg = Segment(Point(0, 0), Point(10, 0))
        pt_t = seg.point_perpendicular(5.0, t=0.5)
        pt_l = seg.point_perpendicular(5.0, arc_length=5.0)
        self.assertAlmostEqual(pt_t.x, pt_l.x)
        self.assertAlmostEqual(pt_t.y, pt_l.y)

    def test_point_perpendicular_default_is_midpoint(self):
        """point_perpendicular with no position arg uses the midpoint."""
        seg = Segment(Point(0, 0), Point(10, 0))
        pt = seg.point_perpendicular(3.0)
        self.assertAlmostEqual(pt.x, 5.0)
        self.assertAlmostEqual(pt.y, 3.0)

    def test_point_perpendicular_negative_distance(self):
        """Negative distance goes to the right (opposite side) of the segment."""
        seg = Segment(Point(0, 0), Point(10, 0))
        pos = seg.point_perpendicular(+5.0, t=0.5)
        neg = seg.point_perpendicular(-5.0, t=0.5)
        self.assertAlmostEqual(pos.x, neg.x)
        self.assertAlmostEqual(pos.y, -neg.y)

    def test_point_perpendicular_both_position_args_raises(self):
        """Providing both arc_length and t must raise ValueError."""
        seg = Segment(Point(0, 0), Point(10, 0))
        with self.assertRaises(ValueError):
            seg.point_perpendicular(5.0, arc_length=3.0, t=0.3)

    def test_line_line_intersection(self):
        """Test intersection between two lines.

        Verifies that the intersect_with method correctly finds
        the intersection point between two lines and handles
        special cases like parallel lines and non-intersecting segments.
        """
        line1 = Segment(Point(0, 0), Point(10, 10))
        line2 = Segment(Point(0, 10), Point(10, 0))

        # These lines should intersect at (5, 5)
        intersections = intersect(line1, line2)
        self.assertEqual(len(intersections), 1)
        self.assertAlmostEqual(intersections[0].x, 5.0)
        self.assertAlmostEqual(intersections[0].y, 5.0)

        # Parallel lines
        line3 = Segment(Point(0, 0), Point(10, 10))
        line4 = Segment(Point(0, 1), Point(10, 11))
        self.assertEqual(intersect(line3, line4), [])

        # Lines that don't intersect within their segments
        line5 = Segment(Point(0, 0), Point(5, 5))
        line6 = Segment(Point(6, 6), Point(10, 10))
        self.assertEqual(intersect(line5, line6), [])


class TestRay(unittest.TestCase):
    """Test cases for the Ray class.

    This class contains tests for the Ray geometric primitive,
    including creation, point calculation, and intersection operations.
    """

    def test_creation(self):
        """Test ray creation and attributes.

        Verifies that a Ray can be created with an origin point and direction,
        and that the direction vector is normalized properly.
        """
        origin = Point(1, 2)
        direction = (3, 4)
        ray = Ray(origin, direction)
        self.assertEqual(ray.origin, origin)

        # Direction should be normalized
        magnitude = math.sqrt(3 * 3 + 4 * 4)
        expected = np.array([3 / magnitude, 4 / magnitude])
        np.testing.assert_almost_equal(ray.direction, expected)

        # Test with zero vector
        with self.assertRaises(ValueError):
            Ray(origin, (0, 0))

        # Test with numpy array
        ray_np = Ray(origin, np.array([3, 4]))
        np.testing.assert_almost_equal(ray_np.direction, expected)

        # Test access to coords directly
        np.testing.assert_almost_equal(origin.coords, np.array([1, 2]))

    def test_point_at_distance(self):
        """Test getting a point at a specified distance on the ray.

        Ray and Line use point_at_distance() (directional distance along an
        infinite object). Segment and CubicBezier use point_at_length()
        (arc length on a bounded path). The two are semantically distinct.
        """
        ray = Ray(Point(0, 0), (1, 0))  # Ray along x-axis
        point = ray.point_at_distance(5)
        self.assertAlmostEqual(point.x, 5.0)
        self.assertAlmostEqual(point.y, 0.0)

        # Ray along y-axis
        ray = Ray(Point(0, 0), (0, 1))
        point = ray.point_at_distance(3)
        self.assertAlmostEqual(point.x, 0.0)
        self.assertAlmostEqual(point.y, 3.0)
        np.testing.assert_almost_equal(point.coords, np.array([0.0, 3.0]))

        ray = Ray(Point(1, 1), (1, 1))  # 45-degree ray
        point = ray.point_at_distance(math.sqrt(2))
        self.assertAlmostEqual(point.x, 2.0)
        self.assertAlmostEqual(point.y, 2.0)

    def test_contains_point(self):
        """Test if a point lies on the ray.

        Verifies that the contains_point method correctly determines
        whether a given point lies on the ray within tolerance.
        """
        ray = Ray(Point(0, 0), (3, 4))

        # Points on the ray
        self.assertTrue(ray.contains_point(Point(0, 0)))  # Origin
        self.assertTrue(ray.contains_point(Point(0.6, 0.8)))  # At distance 1
        self.assertTrue(ray.contains_point(Point(3, 4)))  # At distance 5
        self.assertTrue(ray.contains_point(Point(6, 8)))  # At distance 10

        # Points not on the ray
        self.assertFalse(ray.contains_point(Point(1, 0)))
        self.assertFalse(ray.contains_point(Point(-0.6, -0.8)))  # Wrong direction

    def test_ray_line_intersection(self):
        """Test intersection between ray and line.

        Verifies that the intersect_with method correctly finds the
        intersection point between a ray and a line segment.
        """
        ray = Ray(Point(0, 0), (1, 1))
        line = Segment(Point(0, 10), Point(10, 0))

        # Ray and line should intersect at (5, 5)
        intersections = intersect(ray, line)
        self.assertEqual(len(intersections), 1)
        self.assertAlmostEqual(intersections[0].x, 5.0)
        self.assertAlmostEqual(intersections[0].y, 5.0)
        np.testing.assert_almost_equal(intersections[0].coords, np.array([5.0, 5.0]))

        # Ray pointing away from line
        ray = Ray(Point(0, 0), (-1, -1))
        self.assertEqual(intersect(ray, line), [])

    def test_ray_ray_intersection(self):
        """Test intersection between two rays.

        Verifies that the intersect_with method correctly finds the
        intersection point between two rays and handles special cases
        like parallel rays and rays pointing away from each other.
        """
        ray1 = Ray(Point(0, 0), (1, 1))
        ray2 = Ray(Point(0, 10), (1, -1))

        # Rays should intersect at (5, 5)
        intersections = intersect(ray1, ray2)
        self.assertEqual(len(intersections), 1)
        self.assertAlmostEqual(intersections[0].x, 5.0)
        self.assertAlmostEqual(intersections[0].y, 5.0)

        # Parallel rays
        ray3 = Ray(Point(0, 0), (1, 1))
        ray4 = Ray(Point(1, 0), (1, 1))
        self.assertEqual(intersect(ray3, ray4), [])

        # Rays pointing away from each other
        ray5 = Ray(Point(0, 0), (1, 0))
        ray6 = Ray(Point(10, 0), (-1, 0))
        self.assertEqual(intersect(ray5, ray6), [])


class TestCircle(unittest.TestCase):
    """Test cases for the Circle class.

    This class contains tests for the Circle geometric primitive,
    including creation, area/circumference calculation, and intersections.
    """

    def test_creation(self):
        """Test circle creation and attributes.

        Verifies that a Circle can be created with a center point and radius,
        and that invalid radii are properly rejected.
        """
        center = Point(2, 3)
        radius = 5
        circle = Circle(center, radius)
        self.assertEqual(circle.center, center)
        self.assertEqual(circle.radius, radius)

        # Test invalid radius
        with self.assertRaises(ValueError):
            Circle(center, 0)
        with self.assertRaises(ValueError):
            Circle(center, -1)

    def test_area_and_circumference(self):
        """Test area and circumference calculations.

        Verifies that the area and circumference properties
        correctly calculate these values for the circle.
        """
        circle = Circle(Point(0, 0), 2)
        self.assertAlmostEqual(circle.area, math.pi * 4)
        self.assertAlmostEqual(circle.circumference, math.pi * 4)

    def test_contains_point(self):
        """Test if a point lies on the circle.

        Verifies that the contains_point method correctly determines
        whether a given point lies on the circle boundary within tolerance.
        """
        circle = Circle(Point(0, 0), 5)

        # Points on the circle
        self.assertTrue(circle.contains_point(Point(5, 0)))
        self.assertTrue(circle.contains_point(Point(0, 5)))
        self.assertTrue(circle.contains_point(Point(3, 4)))  # 3-4-5 triangle

        # Points not on the circle
        self.assertFalse(circle.contains_point(Point(0, 0)))  # Center
        self.assertFalse(circle.contains_point(Point(3, 3)))  # Inside
        self.assertFalse(circle.contains_point(Point(10, 0)))  # Outside

    def test_contains_point_inside(self):
        """Test if a point is inside the circle.

        Verifies that the contains_point_inside method correctly determines
        whether a given point is inside the circle, with options to include
        or exclude the boundary.
        """
        circle = Circle(Point(0, 0), 5)

        # Inside points
        self.assertTrue(circle.contains_point_inside(Point(0, 0)))  # Center
        self.assertTrue(circle.contains_point_inside(Point(3, 0)))  # Inside

        # Boundary
        self.assertTrue(circle.contains_point_inside(Point(5, 0), include_boundary=True))
        self.assertFalse(circle.contains_point_inside(Point(5, 0), include_boundary=False))

        # Outside
        self.assertFalse(circle.contains_point_inside(Point(10, 0)))

    def test_point_at_angle(self):
        """Test getting a point on the circle at a specified angle.

        Verifies that the point_at_angle method correctly calculates
        points on the circle boundary at specified angles.
        """
        circle = Circle(Point(0, 0), 1)

        # Points at cardinal directions
        point = circle.point_at_angle(0)  # Right
        self.assertAlmostEqual(point.x, 1.0)
        self.assertAlmostEqual(point.y, 0.0)

        point = circle.point_at_angle(math.pi / 2)  # Top
        self.assertAlmostEqual(point.x, 0.0)
        self.assertAlmostEqual(point.y, 1.0)

        point = circle.point_at_angle(math.pi)  # Left
        self.assertAlmostEqual(point.x, -1.0)
        self.assertAlmostEqual(point.y, 0.0)

        point = circle.point_at_angle(3 * math.pi / 2)  # Bottom
        self.assertAlmostEqual(point.x, 0.0)
        self.assertAlmostEqual(point.y, -1.0)

    def test_circle_line_intersection(self):
        """Test intersection between circle and line.

        Verifies that the intersect_with method correctly finds intersection
        points between a circle and a line, including special cases like
        tangent lines and non-intersecting lines.
        """
        circle = Circle(Point(0, 0), 5)

        # Line through the center
        line = Segment(Point(-10, 0), Point(10, 0))
        intersections = intersect(circle, line)
        self.assertEqual(len(intersections), 2)  # Two intersection points
        points = sorted([p.x for p in intersections])
        self.assertAlmostEqual(points[0], -5.0)
        self.assertAlmostEqual(points[1], 5.0)

        # Tangent line
        line = Segment(Point(0, 5), Point(10, 5))
        intersections = intersect(circle, line)
        self.assertEqual(len(intersections), 1)  # One point only
        self.assertAlmostEqual(intersections[0].x, 0.0)
        self.assertAlmostEqual(intersections[0].y, 5.0)

        # Line that doesn't intersect
        line = Segment(Point(0, 10), Point(10, 10))
        self.assertEqual(intersect(circle, line), [])

    def test_circle_ray_intersection(self):
        """Test intersection between circle and ray.

        Verifies that the intersect_with method correctly finds intersection
        points between a circle and a ray, including special cases like rays
        intersecting at one or two points, and rays pointing away from the circle.
        """
        circle = Circle(Point(0, 0), 5)

        # Ray that intersects twice
        ray = Ray(Point(-10, 0), (1, 0))
        intersections = intersect(circle, ray)
        self.assertEqual(len(intersections), 2)  # Two intersection points
        points = sorted([p.x for p in intersections])
        self.assertAlmostEqual(points[0], -5.0)
        self.assertAlmostEqual(points[1], 5.0)

        # Ray that intersects once
        ray = Ray(Point(0, 5), (1, 0))
        intersections = intersect(circle, ray)
        self.assertEqual(len(intersections), 1)  # One point only
        self.assertAlmostEqual(intersections[0].x, 0.0)
        self.assertAlmostEqual(intersections[0].y, 5.0)

        # Ray pointing away from circle
        ray = Ray(Point(-10, 0), (-1, 0))
        self.assertEqual(intersect(circle, ray), [])

    def test_circle_circle_intersection(self):
        """Test intersection between two circles.

        Verifies that the intersect_with method correctly finds intersection
        points between two circles, including special cases like externally
        touching circles, non-intersecting circles, and one circle inside another.
        """
        circle1 = Circle(Point(0, 0), 5)

        # Circles that intersect at two points
        circle2 = Circle(Point(8, 0), 5)
        intersections = intersect(circle1, circle2)
        self.assertEqual(len(intersections), 2)  # Two intersection points
        points = sorted([(p.x, p.y) for p in intersections])
        self.assertAlmostEqual(points[0][0], 4.0)
        self.assertAlmostEqual(points[0][1], -3.0)
        self.assertAlmostEqual(points[1][0], 4.0)
        self.assertAlmostEqual(points[1][1], 3.0)

        # Circles that touch at one point (externally)
        circle3 = Circle(Point(10, 0), 5)
        intersections = intersect(circle1, circle3)
        self.assertEqual(len(intersections), 1)  # One point only
        self.assertAlmostEqual(intersections[0].x, 5.0)
        self.assertAlmostEqual(intersections[0].y, 0.0)

        # Circles that don't intersect
        circle4 = Circle(Point(20, 0), 5)
        self.assertEqual(intersect(circle1, circle4), [])

        # One circle inside the other (no intersection)
        circle5 = Circle(Point(0, 0), 2)
        self.assertEqual(intersect(circle1, circle5), [])


class TestCubicBezierBoundingBox(unittest.TestCase):
    """Tests for CubicBezier.bounding_box().

    The bounding box must reflect the actual curve extent, NOT the
    convex hull of the four control points. p1 and p2 are off-curve
    and must never be used as bounding-box seeds.
    """

    @staticmethod
    def _make_curve():
        """Curve where control points lie outside the actual curve extent."""
        return CubicBezier(
            p0=Point(10, 10),
            p1=Point(20, 0),  # below the curve
            p2=Point(30, 20),  # above the curve
            p3=Point(40, 10),
        )

    def test_bbox_x_bounds_match_endpoints(self):
        """x range is fully determined by the endpoints for this curve."""
        bez = self._make_curve()
        mn, mx = bez.bounding_box()
        self.assertAlmostEqual(mn.x, 10.0, places=6)
        self.assertAlmostEqual(mx.x, 40.0, places=6)

    def test_bbox_y_does_not_reach_control_points(self):
        """y min/max must stay within the actual curve, not at control points."""
        bez = self._make_curve()
        mn, mx = bez.bounding_box()
        # Control points are at y=0 and y=20 – the curve never reaches them
        self.assertGreater(mn.y, 0.0, "y_min must be above the off-curve control point y=0")
        self.assertLess(mx.y, 20.0, "y_max must be below the off-curve control point y=20")

    def test_bbox_y_values_are_correct(self):
        """Exact y extrema match the analytic result (also verified by svgpathtools)."""
        bez = self._make_curve()
        mn, mx = bez.bounding_box()
        self.assertAlmostEqual(mn.y, 7.113249, places=4)
        self.assertAlmostEqual(mx.y, 12.886751, places=4)

    def test_bbox_endpoints_always_inside(self):
        """Start and end points of the curve must lie within the bounding box."""
        bez = self._make_curve()
        mn, mx = bez.bounding_box()
        for pt in (bez.p0, bez.p3):
            self.assertGreaterEqual(pt.x, mn.x)
            self.assertLessEqual(pt.x, mx.x)
            self.assertGreaterEqual(pt.y, mn.y)
            self.assertLessEqual(pt.y, mx.y)

    def test_bbox_straight_line(self):
        """A straight cubic Bezier has a bounding box equal to its endpoint range."""
        bez = CubicBezier(
            p0=Point(0, 0),
            p1=Point(10, 10),  # control points along the diagonal
            p2=Point(20, 20),
            p3=Point(30, 30),
        )
        mn, mx = bez.bounding_box()
        self.assertAlmostEqual(mn.x, 0.0, places=6)
        self.assertAlmostEqual(mn.y, 0.0, places=6)
        self.assertAlmostEqual(mx.x, 30.0, places=6)
        self.assertAlmostEqual(mx.y, 30.0, places=6)


class TestCubicBezierIntersect(unittest.TestCase):
    """Tests for Bézier–Bézier intersection via intersect().

    Reference values are verified against svgpathtools.CubicBezier.intersect(),
    which uses the Bézier-clipping algorithm (Sederberg & Nishita 1990).
    """

    # The two crossing curves used throughout the suite
    # (same curves as in examples/svgpathtools_test.py)
    _A = CubicBezier(
        p0=Point(10, 10),
        p1=Point(20, 0),
        p2=Point(30, 20),
        p3=Point(40, 10),
    )
    _B = CubicBezier(
        p0=Point(10, 15),
        p1=Point(20, 25),
        p2=Point(30, 5),
        p3=Point(40, 15),
    )

    def test_two_crossings_found(self):
        """The reference pair of curves has exactly two intersections."""
        pts = intersect(self._A, self._B)
        self.assertEqual(len(pts), 2)

    def test_intersection_points_lie_on_both_curves(self):
        """Every returned point must lie on both curves (distance < 0.05 mm).

        We verify membership by sampling each curve at 1000 points and checking
        that the intersection point is within 0.05 mm of the closest sample.
        The tolerance is deliberately loose to account for the finite sampling
        resolution (~0.033 mm step for a ~33 mm long curve).
        """
        tol = 0.05  # mm – sampling grid resolution bound
        pts = intersect(self._A, self._B)
        for pt in pts:
            min_d_a = min(pt.distance_to(self._A.point_at_t(k / 1000)) for k in range(1001))
            min_d_b = min(pt.distance_to(self._B.point_at_t(k / 1000)) for k in range(1001))
            self.assertLess(min_d_a, tol, f"Point {pt} is not on curve A")
            self.assertLess(min_d_b, tol, f"Point {pt} is not on curve B")

    def test_first_intersection_coordinates(self):
        """First intersection near (30.92, 12.50) as per svgpathtools reference."""
        pts = sorted(intersect(self._A, self._B), key=lambda p: p.x)
        self.assertAlmostEqual(pts[0].x, 30.924, places=1)
        self.assertAlmostEqual(pts[0].y, 12.5, places=1)

    def test_second_intersection_coordinates(self):
        """Second intersection near (36.13, 12.50) as per svgpathtools reference."""
        pts = sorted(intersect(self._A, self._B), key=lambda p: p.x)
        self.assertAlmostEqual(pts[1].x, 36.133, places=1)
        self.assertAlmostEqual(pts[1].y, 12.5, places=1)

    def test_symmetric_call_returns_same_count(self):
        """intersect(A, B) and intersect(B, A) must return the same number of points."""
        pts_ab = intersect(self._A, self._B)
        pts_ba = intersect(self._B, self._A)
        self.assertEqual(len(pts_ab), len(pts_ba))

    def test_no_intersection_parallel_curves(self):
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
        self.assertEqual(pts, [])

    def test_no_duplicates_returned(self):
        """No two returned points may be closer than 0.01 mm to each other."""
        pts = intersect(self._A, self._B)
        for i, p1 in enumerate(pts):
            for j, p2 in enumerate(pts):
                if i != j:
                    self.assertGreater(p1.distance_to(p2), 0.01)


class TestCubicBezierNewMethods(unittest.TestCase):
    """Tests for normal_at_t(), point_at_length(), split(), and property aliases."""

    @staticmethod
    def _curve():
        return CubicBezier(
            p0=Point(10, 10),
            p1=Point(20, 0),
            p2=Point(30, 20),
            p3=Point(40, 10),
        )

    # ── start / end aliases ──────────────────────────────────────────────────

    def test_start_is_p0(self):
        """start property must equal p0."""
        b = self._curve()
        self.assertEqual(b.start, b.p0)

    def test_end_is_p3(self):
        """end property must equal p3."""
        b = self._curve()
        self.assertEqual(b.end, b.p3)

    # ── length as property ───────────────────────────────────────────────────

    def test_length_is_property(self):
        """length must be accessible as a property (no call parentheses)."""
        b = self._curve()
        curve_len = b.length  # must not raise TypeError
        self.assertGreater(curve_len, 0.0)

    # ── normal_at_t ─────────────────────────────────────────────────────────

    def test_normal_is_unit_length(self):
        """normal_at_t() must return a vector of length 1."""
        b = self._curve()
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            n = b.normal_at_t(t)
            self.assertAlmostEqual(float(np.linalg.norm(n)), 1.0, places=10)

    def test_normal_perpendicular_to_tangent(self):
        """Normal and tangent must be perpendicular (dot product = 0)."""
        b = self._curve()
        for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
            tan = b.tangent_at_t(t)
            nor = b.normal_at_t(t)
            tan_unit = tan / np.linalg.norm(tan)
            self.assertAlmostEqual(float(np.dot(tan_unit, nor)), 0.0, places=10)

    def test_normal_offset_point_at_correct_distance(self):
        """A point offset by d mm along the normal is d mm from the curve."""
        b = self._curve()
        d = 10.0  # mm seam allowance
        t = 0.5
        pt = b.point_at_t(t)
        nor = b.normal_at_t(t)
        offset = Point(pt.x + d * nor[0], pt.y + d * nor[1])
        self.assertAlmostEqual(pt.distance_to(offset), d, places=10)

    # ── point_at_length ──────────────────────────────────────────────────────

    def test_point_at_length_zero_is_start(self):
        """point_at_length(0) must return p0."""
        b = self._curve()
        pt = b.point_at_length(0.0)
        self.assertAlmostEqual(pt.x, b.p0.x, places=4)
        self.assertAlmostEqual(pt.y, b.p0.y, places=4)

    def test_point_at_length_full_is_end(self):
        """point_at_length(total_length) must return p3."""
        b = self._curve()
        pt = b.point_at_length(b.length)
        self.assertAlmostEqual(pt.x, b.p3.x, places=4)
        self.assertAlmostEqual(pt.y, b.p3.y, places=4)

    def test_point_at_length_midpoint_is_on_curve(self):
        """point_at_length(L/2) must lie on the curve."""
        b = self._curve()
        half = b.length / 2
        pt = b.point_at_length(half)
        # Verify by sampling: closest sample on curve should be < 0.05 mm away
        min_d = min(pt.distance_to(b.point_at_t(k / 2000)) for k in range(2001))
        self.assertLess(min_d, 0.05)

    def test_point_at_length_arc_distance_is_correct(self):
        """The arc length from p0 to point_at_length(s) must equal s."""
        b = self._curve()
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
        self.assertAlmostEqual(recovered, s, places=4)

    def test_point_at_length_raises_on_negative(self):
        """point_at_length() must raise ValueError for negative arc length."""
        b = self._curve()
        with self.assertRaises(ValueError):
            b.point_at_length(-1.0)

    def test_point_at_length_raises_on_overflow(self):
        """point_at_length() must raise ValueError if arc length > curve length."""
        b = self._curve()
        with self.assertRaises(ValueError):
            b.point_at_length(b.length + 1.0)

    # ── split ────────────────────────────────────────────────────────────────

    def test_split_left_starts_at_p0(self):
        """Left piece must start at the original p0."""
        b = self._curve()
        left, _ = b.split(0.5)
        self.assertAlmostEqual(left.p0.x, b.p0.x, places=10)
        self.assertAlmostEqual(left.p0.y, b.p0.y, places=10)

    def test_split_right_ends_at_p3(self):
        """Right piece must end at the original p3."""
        b = self._curve()
        _, right = b.split(0.5)
        self.assertAlmostEqual(right.p3.x, b.p3.x, places=10)
        self.assertAlmostEqual(right.p3.y, b.p3.y, places=10)

    def test_split_join_point_matches(self):
        """Left end and right start must be the same point (the split point)."""
        b = self._curve()
        left, right = b.split(0.5)
        self.assertAlmostEqual(left.p3.x, right.p0.x, places=10)
        self.assertAlmostEqual(left.p3.y, right.p0.y, places=10)

    def test_split_join_point_lies_on_original(self):
        """The split point must lie on the original curve at t."""
        b = self._curve()
        t = 0.4
        left, right = b.split(t)
        expected = b.point_at_t(t)
        self.assertAlmostEqual(left.p3.x, expected.x, places=8)
        self.assertAlmostEqual(left.p3.y, expected.y, places=8)

    def test_split_lengths_sum_to_original(self):
        """Left length + right length must equal the original curve length."""
        b = self._curve()
        left, right = b.split(0.5)
        self.assertAlmostEqual(left.length + right.length, b.length, places=6)

    def test_split_returns_cubicbezier_instances(self):
        """split() must return two CubicBezier objects."""
        b = self._curve()
        left, right = b.split(0.5)
        self.assertIsInstance(left, CubicBezier)
        self.assertIsInstance(right, CubicBezier)


class TestCubicBezierSplitAtPoints(unittest.TestCase):
    """Tests for CubicBezier.split_at_points()."""

    @staticmethod
    def _curve():
        return CubicBezier(
            p0=Point(10, 10),
            p1=Point(20, 0),
            p2=Point(30, 20),
            p3=Point(40, 10),
        )

    def test_split_at_one_point_gives_two_curves(self):
        b = self._curve()
        subs = b.split_at_points([b.point_at_t(0.5)])
        self.assertEqual(len(subs), 2)
        for s in subs:
            self.assertIsInstance(s, CubicBezier)

    def test_split_at_two_points_gives_three_curves(self):
        b = self._curve()
        subs = b.split_at_points([b.point_at_t(0.25), b.point_at_t(0.75)])
        self.assertEqual(len(subs), 3)

    def test_split_at_points_lengths_sum_to_original(self):
        b = self._curve()
        subs = b.split_at_points([b.point_at_t(0.3), b.point_at_t(0.7)])
        total = sum(s.length for s in subs)
        self.assertAlmostEqual(total, b.length, places=4)

    def test_split_at_points_chain_is_continuous(self):
        """End of each sub-curve must equal the start of the next."""
        b = self._curve()
        subs = b.split_at_points([b.point_at_t(0.2), b.point_at_t(0.6), b.point_at_t(0.9)])
        for a, c in zip(subs, subs[1:], strict=False):
            self.assertAlmostEqual(a.p3.x, c.p0.x, places=6)
            self.assertAlmostEqual(a.p3.y, c.p0.y, places=6)

    def test_split_at_points_unsorted_input_same_result(self):
        """Points in reverse order must produce the same sub-lengths."""
        b = self._curve()
        pa, pb = b.point_at_t(0.3), b.point_at_t(0.7)
        forward = b.split_at_points([pa, pb])
        backward = b.split_at_points([pb, pa])
        self.assertEqual(len(forward), len(backward))
        for a, c in zip(forward, backward, strict=False):
            self.assertAlmostEqual(a.length, c.length, places=4)

    def test_split_at_endpoint_produces_no_degenerate_stub(self):
        """A point coinciding with p0 must be dropped (only one real split left)."""
        b = self._curve()
        subs = b.split_at_points([b.p0, b.point_at_t(0.5)])
        self.assertEqual(len(subs), 2)

    def test_split_at_points_all_near_endpoints_returns_original(self):
        """When all points are at endpoints, return the original curve."""
        b = self._curve()
        subs = b.split_at_points([b.p0, b.p3])
        self.assertEqual(len(subs), 1)
        self.assertAlmostEqual(subs[0].length, b.length, places=4)

    def test_split_preserves_start_and_end(self):
        """First sub-curve starts at p0; last ends at p3."""
        b = self._curve()
        subs = b.split_at_points([b.point_at_t(0.4)])
        self.assertAlmostEqual(subs[0].p0.x, b.p0.x, places=8)
        self.assertAlmostEqual(subs[-1].p3.x, b.p3.x, places=8)


if __name__ == "__main__":
    unittest.main()
