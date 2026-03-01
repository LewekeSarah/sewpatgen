#!/usr/bin/env python3
"""Geometry Module Example Script.

This script demonstrates the usage of the geometric primitives
in the sewpat library: Point, Segment, Ray, and Circle.
"""

import math

import numpy as np

from sewpat.geometry import Circle, Point, Ray, Segment, intersect


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def demonstrate_points():
    """Demonstrate Point operations.

    Shows creation of points, calculation of distances, translation,
    and rotation operations.
    """
    print_section("Points")

    p1 = Point(3, 4)
    p2 = Point(7, 8)

    print(f"Point p1: {p1}")
    print(f"Point p2: {p2}")
    print(f"p1 coordinates as NumPy array: {p1.coords}")
    print(f"p1.x: {p1.x}, p1.y: {p1.y}")

    distance = p1.distance_to(p2)
    print(f"Distance from p1 to p2: {distance:.2f}")

    p3 = p1.translate(2, 3)
    print(f"p1 translated by (2, 3): {p3}")

    translation = np.array([5, -2])
    p4 = Point(*(p1.coords + translation))
    print(f"p1 translated by NumPy array {translation}: {p4}")

    center = Point(0, 0)
    p5 = Point(5, 0)
    p5_rotated = p5.rotate(center, math.pi / 2)  # 90 degrees
    print(f"Point {p5} rotated 90° around origin: {p5_rotated}")


def demonstrate_lines():
    """Demonstrate Segment operations.

    Shows creation of segments, calculation of properties like length and midpoint,
    checking if points lie on segments, and finding intersections.
    """
    print_section("Segments")

    line1 = Segment(Point(0, 0), Point(10, 10))
    line2 = Segment(Point(0, 10), Point(10, 0))

    print(f"Segment 1: {line1}")
    print(f"Segment 2: {line2}")
    print(f"Length of segment 1: {line1.length:.2f}")
    print(f"Midpoint of segment 1: {line1.midpoint}")

    test_point = Point(5, 5)
    print(f"Is point {test_point} on segment 1? {line1.contains_point(test_point)}")
    print(f"Is point {test_point} on segment 2? {line2.contains_point(test_point)}")

    intersections = intersect(line1, line2)
    if intersections:
        print(f"Intersection of segment 1 and segment 2: {intersections[0]}")
    else:
        print("Segment 1 and segment 2 do not intersect")


def demonstrate_rays():
    """Demonstrate Ray operations.

    Shows creation of rays, calculation of points along rays,
    checking if points lie on rays, and finding intersections.
    """
    print_section("Rays")

    ray1 = Ray(Point(0, 0), (1, 1))  # 45° upward
    ray2 = Ray(Point(10, 0), (-1, 1))  # 45° upward and left
    ray3 = Ray(Point(5, 5), np.array([0, 1]))  # Straight up

    print(f"Ray 1: {ray1}")
    print(f"Ray 2: {ray2}")
    print(f"Ray 3 (with NumPy direction): {ray3}")

    # point_at_distance: directional distance on an infinite object
    point = ray1.point_at_distance(7.07)  # ~5√2
    print(f"Point on ray 1 at distance 7.07: {point}")
    print(f"Ray 1 direction (NumPy array): {ray1.direction}")

    test_point = Point(5, 5)
    print(f"Is point {test_point} on ray 1? {ray1.contains_point(test_point)}")

    intersections = intersect(ray1, ray2)
    if intersections:
        print(f"Intersection of ray 1 and ray 2: {intersections[0]}")
    else:
        print("Ray 1 and ray 2 do not intersect")

    line = Segment(Point(0, 10), Point(10, 0))
    intersections = intersect(ray1, line)
    if intersections:
        print(f"Intersection of ray 1 and segment: {intersections[0]}")
    else:
        print("Ray 1 and segment do not intersect")


def demonstrate_circles():
    """Demonstrate Circle operations.

    Shows creation of circles, properties like area and circumference,
    points on circles at specified angles, containment checks,
    and intersections with other geometric objects.
    """
    print_section("Circles")

    circle1 = Circle(Point(0, 0), 5)
    circle2 = Circle(Point(8, 0), 5)

    print(f"Circle 1: {circle1}")
    print(f"Circle 2: {circle2}")
    print(f"Area of circle 1: {circle1.area:.2f}")
    print(f"Circumference of circle 1: {circle1.circumference:.2f}")
    print(f"Circle 1 center as NumPy array: {circle1.center.coords}")

    point0 = circle1.point_at_angle(0)  # 3 o'clock
    point90 = circle1.point_at_angle(math.pi / 2)  # 12 o'clock
    print(f"Point on circle 1 at   0°: {point0}")
    print(f"Point on circle 1 at  90°: {point90}")

    test_point = Point(3, 4)  # 3-4-5 triangle – lies on circle 1
    print(f"Is point {test_point} on circle 1? {circle1.contains_point(test_point)}")
    print(
        f"Is point {test_point} inside circle 1? {circle1.contains_point_inside(test_point)}"
    )

    # Circle–circle intersection
    intersections = intersect(circle1, circle2)
    if len(intersections) == 2:
        print(
            f"Circle 1 and circle 2 intersect at: {intersections[0]} and {intersections[1]}"
        )
    elif len(intersections) == 1:
        print(f"Circle 1 and circle 2 touch at: {intersections[0]}")
    else:
        print("Circle 1 and circle 2 do not intersect")

    # Circle–segment intersection
    line = Segment(Point(-10, 0), Point(10, 0))  # Horizontal line through origin
    intersections = intersect(circle1, line)
    if len(intersections) == 2:
        print(
            f"Circle 1 and horizontal segment intersect at: {intersections[0]} and {intersections[1]}"
        )
    elif len(intersections) == 1:
        print(f"Circle 1 and horizontal segment touch at: {intersections[0]}")
    else:
        print("Circle 1 and horizontal segment do not intersect")


def demonstrate_cad_example():
    """Demonstrate a simple CAD-like example.

    Creates a rectangle with rounded corners and calculates the total perimeter.
    """
    print_section("Simple CAD Example: Rectangle with Rounded Corners")

    rect_width = 100
    rect_height = 60
    corner_radius = 10

    # Straight edges (between the arc endpoints)
    top_line = Segment(
        Point(corner_radius, rect_height),
        Point(rect_width - corner_radius, rect_height),
    )
    right_line = Segment(
        Point(rect_width, corner_radius), Point(rect_width, rect_height - corner_radius)
    )
    bottom_line = Segment(Point(corner_radius, 0), Point(rect_width - corner_radius, 0))
    left_line = Segment(Point(0, corner_radius), Point(0, rect_height - corner_radius))

    # Corner circles
    c1 = Circle(
        Point(corner_radius, rect_height - corner_radius), corner_radius
    )  # top-left
    c2 = Circle(
        Point(rect_width - corner_radius, rect_height - corner_radius), corner_radius
    )  # top-right
    c3 = Circle(Point(corner_radius, corner_radius), corner_radius)  # bottom-left
    c4 = Circle(
        Point(rect_width - corner_radius, corner_radius), corner_radius
    )  # bottom-right

    print(
        f"  Width: {rect_width}, Height: {rect_height}, Corner radius: {corner_radius}"
    )
    print(f"  Top edge:    {top_line}")
    print(f"  Right edge:  {right_line}")
    print(f"  Bottom edge: {bottom_line}")
    print(f"  Left edge:   {left_line}")
    print(f"  Corner circles: {c1}, {c2}, {c3}, {c4}")

    perimeter = (
        top_line.length
        + right_line.length
        + bottom_line.length
        + left_line.length
        + 2 * math.pi * corner_radius  # four quarter-circles = one full circle
    )
    print(f"  Total perimeter: {perimeter:.2f}")


def main():
    """Run all demonstrations."""
    print("Geometry Module Examples")

    demonstrate_points()
    demonstrate_lines()
    demonstrate_rays()
    demonstrate_circles()
    demonstrate_cad_example()

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
