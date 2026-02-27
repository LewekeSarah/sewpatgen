"""Tests for the geometry module.

This module contains unit tests for all the geometric primitives
defined in the geometry module: Point, Segment, Ray, and Circle.
"""

import math
import unittest
import numpy as np
from sewpat.geometry import Point, Segment, Ray, Circle, CubicBezier, intersect


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


class TestSegment(unittest.TestCase):
    """Test cases for the Segment class.

    This class contains tests for the Segment geometric primitive,
    including creation, properties and intersection calculations.
    """

    def test_creation(self):
        """Test line creation and attributes.

        Verifies that a Line can be created with two points
        and that the points are correctly stored.
        """
        p1 = Point(1, 1)
        p2 = Point(4, 5)
        line = Segment(p1, p2)
        self.assertEqual(line.p1, p1)
        self.assertEqual(line.p2, p2)

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
        """Test if a point lies on the line segment.

        Verifies that the contains_point method correctly determines
        whether a given point lies on the line segment within tolerance.
        """
        line = Segment(Point(0, 0), Point(10, 10))

        # Points on the line
        self.assertTrue(line.contains_point(Point(0, 0)))
        self.assertTrue(line.contains_point(Point(5, 5)))
        self.assertTrue(line.contains_point(Point(10, 10)))

        # Points not on the line
        self.assertFalse(line.contains_point(Point(2, 3)))
        self.assertFalse(line.contains_point(Point(-1, -1)))  # Outside segment
        self.assertFalse(line.contains_point(Point(11, 11)))  # Outside segment

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

        Verifies that the point_at_distance method correctly calculates
        a point along the ray at the specified distance from the origin.
        """
        ray = Ray(Point(0, 0), (1, 0))  # Ray along x-axis
        point = ray.point_at_distance(5)
        self.assertAlmostEqual(point.x, 5.0)
        self.assertAlmostEqual(point.y, 0.0)

        # Ray along y-axis
        ray = Ray(Point(0, 0), (0, 1))  # Ray along y-axis
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
        self.assertTrue(
            circle.contains_point_inside(Point(5, 0), include_boundary=True)
        )
        self.assertFalse(
            circle.contains_point_inside(Point(5, 0), include_boundary=False)
        )

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

    def _make_curve(self):
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
        self.assertGreater(
            mn.y, 0.0, "y_min must be above the off-curve control point y=0"
        )
        self.assertLess(
            mx.y, 20.0, "y_max must be below the off-curve control point y=20"
        )

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
            min_d_a = min(
                pt.distance_to(self._A.point_at_t(k / 1000)) for k in range(1001)
            )
            min_d_b = min(
                pt.distance_to(self._B.point_at_t(k / 1000)) for k in range(1001)
            )
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


if __name__ == "__main__":
    unittest.main()
