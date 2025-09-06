#!/usr/bin/env python3
"""Geometry Module Example Script.

This script demonstrates the usage of the geometric primitives
in the sewpat library: Point, Segment, Ray, and Circle.
"""

import math
import numpy as np

from sewpat.geometry import Point, Segment, Ray, Circle


def print_section(title):
    """Print a section header.

    Args:
        title: The title text to display in the section header.
    """
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def demonstrate_points():
    """Demonstrate Point operations.

    Shows creation of points, calculation of distances, translation,
    and rotation operations.
    """
    print_section("Points")

    # Create points
    p1 = Point(3, 4)
    p2 = Point(7, 8)

    print(f"Point p1: {p1}")
    print(f"Point p2: {p2}")

    # Access underlying NumPy array
    print(f"p1 coordinates as NumPy array: {p1.coords}")
    print(f"p1.x: {p1.x}, p1.y: {p1.y}")

    # Distance between points
    distance = p1.distance_to(p2)
    print(f"Distance from p1 to p2: {distance:.2f}")

    # Translate a point
    p3 = p1.translate(2, 3)
    print(f"p1 translated by (2, 3): {p3}")

    # Translate using NumPy array
    translation = np.array([5, -2])
    p4 = Point(*(p1.coords + translation))
    print(f"p1 translated by NumPy array {translation}: {p4}")

    # Rotate a point
    center = Point(0, 0)
    p4 = Point(5, 0)
    p4_rotated = p4.rotate(center, math.pi/2)  # 90 degrees
    print(f"Point {p4} rotated 90° around origin: {p4_rotated}")


def demonstrate_lines():
    """Demonstrate Line operations.

    Shows creation of lines, calculation of properties like length and midpoint,
    checking if points lie on lines, and finding intersections between lines.
    """
    print_section("Lines")

    # Create lines
    line1 = Segment(Point(0, 0), Point(10, 10))
    line2 = Segment(Point(0, 10), Point(10, 0))

    print(f"Line 1: {line1}")
    print(f"Line 2: {line2}")

    # Line properties
    print(f"Length of line 1: {line1.length:.2f}")
    print(f"Midpoint of line 1: {line1.midpoint}")

    # Check if a point is on a line
    test_point = Point(5, 5)
    print(f"Is point {test_point} on line 1? {line1.contains_point(test_point)}")
    print(f"Is point {test_point} on line 2? {line2.contains_point(test_point)}")

    # Find intersection between lines
    intersections = line1.intersect_with(line2)
    if intersections:
        print(f"Intersection of line 1 and line 2: {intersections[0]}")
    else:
        print("Line 1 and line 2 do not intersect")


def demonstrate_rays():
    """Demonstrate Ray operations.

    Shows creation of rays, calculation of points along rays,
    checking if points lie on rays, and finding intersections
    between rays and other geometric objects.
    """
    print_section("Rays")

    # Create rays
    ray1 = Ray(Point(0, 0), (1, 1))  # 45° upward
    ray2 = Ray(Point(10, 0), (-1, 1))  # 45° upward and left

    # Create ray with NumPy array direction
    ray3 = Ray(Point(5, 5), np.array([0, 1]))  # Straight up
    print(f"Ray 3 (with NumPy direction): {ray3}")

    print(f"Ray 1: {ray1}")
    print(f"Ray 2: {ray2}")

    # Get point at distance
    point = ray1.point_at_distance(7.07)  # ~5√2
    print(f"Point on ray 1 at distance 7.07: {point}")

    # Show direction as NumPy array
    print(f"Ray 1 direction (NumPy array): {ray1.direction}")

    # Check if point is on ray
    test_point = Point(5, 5)
    print(f"Is point {test_point} on ray 1? {ray1.contains_point(test_point)}")

    # Find intersection between rays
    intersections = ray1.intersect_with(ray2)
    if intersections:
        print(f"Intersection of ray 1 and ray 2: {intersections[0]}")
    else:
        print("Ray 1 and ray 2 do not intersect")

    # Ray and line intersection
    line = Segment(Point(0, 10), Point(10, 0))
    intersections = ray1.intersect_with(line)
    if intersections:
        print(f"Intersection of ray 1 and line: {intersections[0]}")
    else:
        print("Ray 1 and line do not intersect")


def demonstrate_circles():
    """Demonstrate Circle operations.

    Shows creation of circles, calculation of circle properties like area and circumference,
    finding points on circles at specified angles, checking if points lie on/inside circles,
    and calculating intersections with other geometric objects.
    """
    print_section("Circles")

    # Create circles
    circle1 = Circle(Point(0, 0), 5)
    circle2 = Circle(Point(8, 0), 5)

    print(f"Circle 1: {circle1}")
    print(f"Circle 2: {circle2}")

    # Circle properties
    print(f"Area of circle 1: {circle1.area:.2f}")
    print(f"Circumference of circle 1: {circle1.circumference:.2f}")

    # Access center as NumPy array
    print(f"Circle 1 center as NumPy array: {circle1.center.coords}")

    # Points on circle
    point0 = circle1.point_at_angle(0)  # Point on the right (3 o'clock)
    point90 = circle1.point_at_angle(math.pi/2)  # Point at the top (12 o'clock)

    print(f"Point on circle 1 at 0°: {point0}")
    print(f"Point on circle 1 at 90°: {point90}")

    # Check if point is on circle
    test_point = Point(3, 4)  # 3-4-5 triangle, should be on circle 1
    print(f"Is point {test_point} on circle 1? {circle1.contains_point(test_point)}")
    print(f"Is point {test_point} inside circle 1? {circle1.contains_point_inside(test_point)}")

    # Circle-circle intersection
    intersections = circle1.intersect_with(circle2)
    if len(intersections) == 2:
        print(f"Circle 1 and Circle 2 intersect at two points: {intersections[0]} and {intersections[1]}")
    elif len(intersections) == 1:
        print(f"Circle 1 and Circle 2 intersect at one point: {intersections[0]}")
    else:
        print("Circle 1 and Circle 2 do not intersect")

    # Circle-line intersection
    line = Segment(Point(-10, 0), Point(10, 0))  # Horizontal line through origin
    intersections = circle1.intersect_with(line)
    if len(intersections) == 2:
        print(f"Circle 1 and horizontal line intersect at two points: {intersections[0]} and {intersections[1]}")
    elif len(intersections) == 1:
        print(f"Circle 1 and horizontal line intersect at one point: {intersections[0]}")
    else:
        print("Circle 1 and horizontal line do not intersect")


def demonstrate_cad_example():
    """Demonstrate a simple CAD-like example.

    Creates a rectangle with rounded corners to demonstrate how the
    geometric primitives can be combined to represent more complex shapes.
    Calculates the total perimeter of the shape.
    """
    print_section("Simple CAD Example")
    print("Creating a simple geometric construction:")

    # Create a rectangle with rounded corners
    rect_width = 10
    rect_height = 6
    corner_radius = 1

    # Define the rectangle corners (before rounding) using NumPy arrays
    corners = np.array([
        [0, rect_height],             # top_left
        [rect_width, rect_height],    # top_right
        [0, 0],                       # bottom_left
        [rect_width, 0]               # bottom_right
    ])

    top_left = Point(*corners[0])
    top_right = Point(*corners[1])
    bottom_left = Point(*corners[2])
    bottom_right = Point(*corners[3])

    # Create circles for the rounded corners
    c1 = Circle(Point(corner_radius, rect_height - corner_radius), corner_radius)  # Top-left
    c2 = Circle(Point(rect_width - corner_radius, rect_height - corner_radius), corner_radius)  # Top-right
    c3 = Circle(Point(corner_radius, corner_radius), corner_radius)  # Bottom-left
    c4 = Circle(Point(rect_width - corner_radius, corner_radius), corner_radius)  # Bottom-right

    # Create connecting lines
    top_line = Segment(Point(corner_radius, rect_height), Point(rect_width - corner_radius, rect_height))
    right_line = Segment(Point(rect_width, corner_radius), Point(rect_width, rect_height - corner_radius))
    bottom_line = Segment(Point(corner_radius, 0), Point(rect_width - corner_radius, 0))
    left_line = Segment(Point(0, corner_radius), Point(0, rect_height - corner_radius))

    # Print out the object definition
    print("Rectangle with rounded corners:")
    print(f"  Width: {rect_width}, Height: {rect_height}, Corner Radius: {corner_radius}")
    print(f"  Top line: {top_line}")
    print(f"  Right line: {right_line}")
    print(f"  Bottom line: {bottom_line}")
    print(f"  Left line: {left_line}")
    print(f"  Top-left corner: {c1}")
    print(f"  Top-right corner: {c2}")
    print(f"  Bottom-left corner: {c3}")
    print(f"  Bottom-right corner: {c4}")

    # Calculate total perimeter
    perimeter = (
        top_line.length + right_line.length + bottom_line.length + left_line.length +
        2 * math.pi * corner_radius  # Four quarter circles = one full circle
    )

    print(f"  Total perimeter: {perimeter:.2f}")


def main():
    """Run all demonstrations.

    Serves as the entry point to execute all example demonstrations
    showing various aspects of the geometry module.
    """
    print("Geometry Module Examples")

    demonstrate_points()
    demonstrate_lines()
    demonstrate_rays()
    demonstrate_circles()
    demonstrate_cad_example()

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
