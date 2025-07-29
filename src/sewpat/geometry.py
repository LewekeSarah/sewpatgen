"""
2D Geometry Module for CAD Operations.

This module provides classes for fundamental 2D geometric primitives such as
points, lines, segments, rays, and circles for use in CAD applications.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


def _solve_quadratic(a: float, b: float, c: float) -> List[float]:
    """Solve a quadratic equation ax^2 + bx + c = 0 in a numerically stable way.

    Uses a numerically stable algorithm to find solutions by avoiding
    subtractive cancellation.

    Args:
        a: Coefficient of the quadratic term.
        b: Coefficient of the linear term.
        c: Constant term.

    Returns:
        List[float]: A list containing 0, 1, or 2 solutions.
    """
    # TODO: https://cnrs.hal.science/hal-04116310v1/document
    # Check if this is actually a linear equation
    if abs(a) < 1e-14:
        # Linear equation: bx + c = 0
        if abs(b) < 1e-14:  # All coefficients are essentially zero
            return []
        return [-c / b]

    # Compute discriminant
    discriminant = b * b - 4 * a * c

    # No real solutions
    if discriminant < 0:
        return []

    # One real solution (repeated root)
    if abs(discriminant) < 1e-14:
        return [-b / (2*a)]

    # Two real solutions - use numerically stable algorithm
    # Instead of the standard formula x = (-b ± sqrt(discriminant)) / (2*a)
    # Use q = -0.5 * (b + sign(b) * sqrt(discriminant))
    # Then x1 = q/a and x2 = c/q
    sqrt_discriminant = math.sqrt(discriminant)

    if b >= 0:
        q = -0.5 * (b + sqrt_discriminant)
    else:
        q = -0.5 * (b - sqrt_discriminant)

    x1 = q / a
    x2 = c / q

    # Return solutions in ascending order
    if x1 <= x2:
        return [x1, x2]
    else:
        return [x2, x1]


def _intersect_lines(pt1: np.ndarray, n1: np.ndarray, pt2: np.ndarray, n2: np.ndarray) -> Optional[np.ndarray]:
    """Find intersection of two lines represented by a point on the line and the unit normal.

    Args:
        pt1: Point on first line.
        n1: Unit normal of first line.
        pt2: Point on second line.
        n2: Unit normal of second line.

    Returns:
        Optional[np.ndarray]: Intersection between the two lines if they are not parallel.
    """
    c1 = np.dot(pt1, n1)
    c2 = np.dot(pt2, n2)

    # System of equations for intersection (x, y):
    # a1 * x + b1 * y = c1
    # a2 * x + b2 * y = c2
    determinant = n1[0] * n2[1] - n2[0] * n1[1]

    if abs(determinant) < 1e-14:
        # Lines are parallel or coincident
        return None

    # Solve the system of equations using Cramer's rule
    x = (n2[1] * c1 - n1[1] * c2) / determinant
    y = (n1[0] * c2 - n2[0] * c1) / determinant

    return np.array([x, y])


@dataclass(frozen=True)
class Point:
    """A 2D point with x and y coordinates stored as a NumPy array.

    Attributes:
        coords: NumPy array containing [x, y] coordinates.
        name: Optional, name of the point.
    """
    coords: np.ndarray
    name: Optional[str] = None

    def __init__(self, x: float, y: float, name: Optional[str] = None):
        """Initialize a point with x and y coordinates.

        Args:
            x: The x-coordinate of the point.
            y: The y-coordinate of the point.
            name: Optional, name of the point.
        """
        # Use object.__setattr__ to set values in a frozen dataclass
        object.__setattr__(self, 'coords', np.array([x, y], dtype=float))
        object.__setattr__(self, 'name', name)

    @property
    def x(self) -> float:
        """Get the x coordinate.

        Returns:
            float: The x-coordinate of the point.
        """
        return self.coords[0]

    @property
    def y(self) -> float:
        """Get the y coordinate.

        Returns:
            float: The y-coordinate of the point.
        """
        return self.coords[1]

    def __str__(self) -> str:
        if self.name:
            return f"Point(name={self.name}, x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"
        else:
            return f"Point(x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"

    def distance_to(self, other: Union['Point', np.ndarray]) -> float:
        """Calculate the Euclidean distance between this point and another.

        Args:
            other: Another point to calculate distance to.

        Returns:
            float: The Euclidean distance between the two points.
        """
        if isinstance(other, Point):
            return np.linalg.norm(self.coords - other.coords)
        else:
            return np.linalg.norm(self.coords - other)

    def translate(self, dx: float, dy: float) -> 'Point':
        """Return a new point translated by the given vector.

        Args:
            dx: Translation distance along the x-axis.
            dy: Translation distance along the y-axis.

        Returns:
            Point: A new point translated by the specified vector.
        """
        translation = np.array([dx, dy])
        return Point(*(self.coords + translation))

    def rotate(self, center: 'Point', angle_rad: float) -> 'Point':
        """Rotate the point around a specified center.

        Args:
            center: The center point of rotation.
            angle_rad: Angle of rotation in radians (positive is counter-clockwise).

        Returns:
            Point: A new point representing the rotated position.
        """
        # Create rotation matrix
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        rotation_matrix = np.array([
            [cos_a, -sin_a],
            [sin_a, cos_a]
        ])

        # Translate to origin, rotate, and translate back
        translated = self.coords - center.coords
        rotated = rotation_matrix @ translated
        result = rotated + center.coords

        return Point(*result)


class Segment:
    """A line segment between two points (from p1 to p2).

    Attributes:
        p1: Start point of the line segment.
        p2: End point of the line segment.
        name: Optional, name of the line segment.
    """
    def __init__(self, p1: Point, p2: Point, name: Optional[str] = None):
        """Initialize a line with two points.

        Args:
            p1: First endpoint of the line segment.
            p2: Second endpoint of the line segment.
            name: Optional, name of the line segment.
        """
        self.p1 = p1
        self.p2 = p2
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return f"Segment(name={self.name}; p1={self.p1}, p2={self.p2})"
        else:
            return f"Segment(p1={self.p1}, p2={self.p2})"

    @property
    def length(self) -> float:
        """Calculate the length of the line segment.

        Returns:
            float: The Euclidean length of the line segment.
        """
        return self.p1.distance_to(self.p2)

    @property
    def direction_unnormalized(self) -> np.ndarray:
        """Return the direction vector of the line segment (not normalized).

        Returns:
            np.ndarray: The non-normalized direction of the line segment.
        """
        return self.p2.coords - self.p1.coords

    @property
    def unit_direction(self) -> np.ndarray:
        """Return the normalized direction vector of the line segment.

        Returns:
            np.ndarray: The normalized direction of the line segment.
        """
        dir_vec = self.p2.coords - self.p1.coords
        return dir_vec / np.linalg.norm(dir_vec)

    @property
    def unit_normal(self) -> np.ndarray:
        """Return the normalized direction vector perpendicular to the line segment.

        The perpendicular direction is to the left of the line direction.

        Returns:
            np.ndarray: The normalized direction perpendicular to the line segment.
        """
        dir_vec = self.p2.coords - self.p1.coords
        dir_vec = dir_vec / np.linalg.norm(dir_vec)
        return np.array([-dir_vec[1], dir_vec[0]])

    @property
    def midpoint(self) -> Point:
        """Calculate the midpoint of the line segment.

        Returns:
            Point: The midpoint of the line segment.
        """
        return Point(*(0.5 * (self.p1.coords + self.p2.coords)))

    def point_at_rel_dist(self, rel_pos: float) -> Point:
        """Calculate a point on the line segment given its relative position.

        Args:
            rel_pos: Relative position on the line segment in [0, 1]. A position
            of 0 corresponds to p1.

        Returns:
            Point: Position on the line segment.
        """
        assert (0 <= rel_pos) and (rel_pos <= 1), f"{rel_pos = } expected in [0, 1]"
        return Point(*( (1.0 - rel_pos) * self.p1.coords + rel_pos * self.p2.coords) )

    def point_perpendicular(self, distance_to_obj: float, distance_on_obj: Optional[float] = None, rel_pos_on_obj: Optional[float] = None) -> Point:
        """Calculates a point at a given perpendicular distance from the line segment.

        This method finds a point that is perpendicular to the line segment at a specified
        position along the line segment, with a given distance from the line segment.

        Args:
            distance_to_obj: Perpendicular distance from the line segment to the point.
                Positive values are to the left of the line direction, negative values to the right.
            distance_on_obj: Optional; absolute distance along the line segment from p1.
                If provided, rel_pos_on_obj must be None.
            rel_pos_on_obj: Optional; relative position along the line from 0.0 (at p1) to 1.0 (at p2).
                If provided, distance_on_obj must be None.

        Returns:
            Point: A new point at the specified perpendicular distance from the line segment.

        Raises:
            ValueError: If both or neither of distance_on_obj and rel_pos_on_obj are provided.
            AssertionError: If rel_pos_on_obj is provided, but not in range [0, 1].

        Examples:
            # Point 5 units perpendicular from the midpoint of the line
            >>> line = Line(Point(0, 0), Point(10, 0))
            >>> point = line.point_perpendicular(5, rel_pos_on_obj=0.5)
            >>> print(point)
            Point(5, 5)
        """
        if ((distance_on_obj is None) and (rel_pos_on_obj is None)) or ((distance_on_obj is not None) and (rel_pos_on_obj is not None)):
            raise ValueError("exactly one of distance_on_obj and rel_pos_on_obj has to be set")

        if distance_on_obj:
            dir = self.unit_direction
            base = self.p1.coords + distance_on_obj * dir
        else:
            assert ((0 <= rel_pos_on_obj) and (rel_pos_on_obj <= 1.0)), f"rel_pos_on_obj = {rel_pos_on_obj} required in [0, 1]"
            base = (1.0 - rel_pos_on_obj) * self.p1.coords + rel_pos_on_obj * self.p2.coords

        return Point(*(base + self.unit_normal * distance_to_obj))

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Check if a point lies on the line segment.

        Args:
            point: The point to check.
            tolerance: The maximum distance allowed for the point to be considered on the line.

        Returns:
            bool: True if the point lies on the line segment within tolerance, False otherwise.
        """
        # Check if dist(p1, p) + dist(p2, p) == length(line)
        delta1 = self.p1.coords - point.coords
        delta2 = self.p2.coords - point.coords
        delta = self.p2.coords - self.p1.coords
        d1 = math.sqrt(np.dot(delta1, delta1))
        d2 = math.sqrt(np.dot(delta2, delta2))
        line_length = math.sqrt(np.dot(delta, delta))

        # Check if point is collinear and within segment bounds
        return abs(d1 + d2 - line_length) < tolerance


class Ray:
    """A ray starting from a point and going in a specific direction.

    Attributes:
        origin: The starting point of the ray.
        direction: Normalized direction vector of the ray.
        name: Optional, name of the ray.
    """
    def __init__(self, origin: Point, direction: Union[Tuple[float, float], List[float], np.ndarray], name: Optional[str] = None):
        """Initialize a ray with an origin point and direction vector.

        Args:
            origin: The starting point of the ray.
            direction: Direction vector as tuple, list or numpy array.
            name: Optional, name of the ray.

        Raises:
            ValueError: If the direction vector is zero (has no magnitude).
        """
        self.origin = origin

        # Convert direction to numpy array if it's not already
        if not isinstance(direction, np.ndarray):
            direction = np.array(direction, dtype=float)

        # Normalize direction vector
        magnitude = np.linalg.norm(direction)
        if magnitude < 1e-14:
            raise ValueError("Direction vector cannot be zero")

        self.direction = direction / magnitude
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return f"Ray(name={self.name}, origin={self.origin}, direction={self.direction})"
        else:
            return f"Ray(origin={self.origin}, direction={self.direction})"

    @property
    def unit_direction(self) -> np.ndarray:
        """Return the normalized direction vector of the line.

        Returns:
            np.ndarray: The normalized direction of the line.
        """
        return self.direction

    @property
    def unit_normal(self) -> np.ndarray:
        """Return the normalized direction vector perpendicular to the ray.

        The perpendicular direction is to the left of the ray direction.

        Returns:
            np.ndarray: The normalized direction perpendicular to the ray.
        """
        dir_vec = self.direction
        return np.array([-dir_vec[1], dir_vec[0]])

    def point_at_distance(self, distance: float) -> Point:
        """Return a point on the ray at the given distance from the origin.

        Args:
            distance: The distance from the origin.

        Returns:
            Point: A point on the ray at the specified distance from the origin.
        """
        point_coords = self.origin.coords + self.direction * distance
        return Point(*point_coords)

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Check if a point lies on the ray.

        Args:
            point: The point to check.
            tolerance: The maximum angular deviation allowed.

        Returns:
            bool: True if the point lies on the ray within tolerance, False otherwise.
        """
        # Vector from origin to point
        v = point.coords - self.origin.coords

        # Magnitude of this vector
        mag_v = np.linalg.norm(v)

        if mag_v < tolerance:
            return True  # Point is at the origin

        # Normalize the vector
        v_normalized = v / mag_v

        # Dot product with direction
        dot_product = np.dot(v_normalized, self.direction)

        # Check if vectors are parallel (dot product near 1)
        # and point is in the right direction
        return abs(dot_product - 1.0) < tolerance

    def point_perpendicular(self, distance_to_obj: float, distance_on_obj: float) -> Point:
        """Calculates a point at a given perpendicular distance from the ray.

        This method finds a point that is perpendicular to the ray at a specified position
        along the ray, with a given distance from the ray.

        Args:
            distance_to_obj: Perpendicular distance from the line to the point.
                Positive values are to the left of the line direction, negative values to the right.
            distance_on_obj: Absolute distance along the ray from origin.

        Returns:
            Point: A new point at the specified perpendicular distance from the ray.
        """
        dir = self.direction
        base = self.origin.coords + distance_on_obj * dir
        return Point(*(base + self.unit_normal * distance_to_obj))


class Line:
    """An infinite line going in a specific direction.

    Attributes:
        point: A point on the line.
        direction: Normalized direction vector of the line.
        name: Optional, name of the line.
    """
    def __init__(self, point: Point, direction: Union[Tuple[float, float], List[float], np.ndarray], name: Optional[str] = None):
        """Initialize a line with a point and direction vector.

        Args:
            point: A point on the line.
            direction: Direction vector as tuple, list or numpy array.
            name: Optional, name of the line.

        Raises:
            ValueError: If the direction vector is zero (has no magnitude).
        """
        self.point = point

        # Convert direction to numpy array if it's not already
        if not isinstance(direction, np.ndarray):
            direction = np.array(direction, dtype=float)

        # Normalize direction vector
        magnitude = np.linalg.norm(direction)
        if magnitude < 1e-14:
            raise ValueError("Direction vector cannot be zero")

        self.direction = direction / magnitude
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return f"Line(name={self.name}, point={self.point}, direction={self.direction})"
        else:
            return f"Line(point={self.point}, direction={self.direction})"

    @property
    def unit_direction(self) -> np.ndarray:
        """Return the normalized direction vector of the line.

        Returns:
            np.ndarray: The normalized direction of the line.
        """
        return self.direction

    @property
    def unit_normal(self) -> np.ndarray:
        """Return the normalized direction vector perpendicular to the line.

        The perpendicular direction is to the left of the line direction.

        Returns:
            np.ndarray: The normalized direction perpendicular to the line.
        """
        dir_vec = self.direction
        return np.array([-dir_vec[1], dir_vec[0]])

    def point_at_distance(self, distance: float) -> Point:
        """Return a point on the line at the given distance from the base point.

        Args:
            distance: The distance from the base point.

        Returns:
            Point: A point on the line at the specified distance from the base point.
        """
        point_coords = self.point.coords + self.direction * distance
        return Point(*point_coords)

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Check if a point lies on the ray.

        Args:
            point: The point to check.
            tolerance: The maximum angular deviation allowed.

        Returns:
            bool: True if the point lies on the ray within tolerance, False otherwise.
        """
        # Vector from origin to point
        v = point.coords - self.point.coords

        # Magnitude of this vector
        mag_v = np.linalg.norm(v)

        if mag_v < tolerance:
            return True  # Point is at the origin

        # Normalize the vector
        v_normalized = v / mag_v

        dot_product = np.dot(v_normalized, self.direction)

        # Check if vectors are parallel (dot product near 1)
        return abs(abs(dot_product) - 1.0) < tolerance

    def point_perpendicular(self, distance_to_obj: float, distance_on_obj: float) -> Point:
        """Calculates a point at a given perpendicular distance from the line.

        This method finds a point that is perpendicular to the line at a specified position
        along the line, with a given distance from the line.

        Args:
            distance_to_obj: Perpendicular distance from the line to the point.
                Positive values are to the left of the line direction, negative values to the right.
            distance_on_obj: Absolute distance along the line from base point.

        Returns:
            Point: A new point at the specified perpendicular distance from the line.
        """
        dir = self.direction
        base = self.point.coords + distance_on_obj * dir
        return Point(*(base + self.unit_normal * distance_to_obj))


class Circle:
    """A circle defined by a center point and radius.

    Attributes:
        center: The center point of the circle.
        radius: The radius of the circle.
        name: Optional, name of the circle.
    """
    def __init__(self, center: Point, radius: float, name: Optional[str] = None):
        """Initialize a circle with center point and radius.

        Args:
            center: The center point of the circle.
            radius: The radius of the circle (must be positive).
            name: Optional, name of the circle.

        Raises:
            ValueError: If the radius is not positive.
        """
        if radius <= 0:
            raise ValueError("Radius must be positive")

        self.center = center
        self.radius = radius
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return f"Circle(name={self.name}, center={self.center}, radius={self.radius:.6g})"
        else:
            return f"Circle(center={self.center}, radius={self.radius:.6g})"

    @property
    def area(self) -> float:
        """Calculate the area of the circle.

        Returns:
            float: The area of the circle.
        """
        return math.pi * self.radius * self.radius

    @property
    def diameter(self) -> float:
        """Calculate the diameter of the circle.

        Returns:
            float: The diameter of the circle.
        """
        return 2 * self.radius

    @property
    def circumference(self) -> float:
        """Calculate the circumference of the circle.

        Returns:
            float: The circumference of the circle.
        """
        return 2 * math.pi * self.radius

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Check if a point lies on the circle boundary.

        Args:
            point: The point to check.
            tolerance: Maximum distance from the circle boundary allowed.

        Returns:
            bool: True if the point is on the circle boundary within tolerance, False otherwise.
        """
        distance = self.center.distance_to(point)
        return abs(distance - self.radius) < tolerance

    def contains_point_inside(self, point: Point, include_boundary: bool = True) -> bool:
        """Check if a point is inside the circle.

        Args:
            point: The point to check.
            include_boundary: If True, points on the boundary are considered inside.

        Returns:
            bool: True if the point is inside the circle (and on boundary if include_boundary),
                 False otherwise.
        """
        distance = self.center.distance_to(point)
        if include_boundary:
            return distance <= self.radius
        return distance < self.radius

    def point_at_angle(self, angle_rad: float) -> Point:
        """Get a point on the circle at the given angle.

        Args:
            angle_rad: Angle in radians. 0 is along the positive x-axis,
                      increasing counterclockwise.

        Returns:
            Point: A point on the circle at the specified angle.
        """
        point_coords = self.center.coords + self.radius * np.array([
            math.cos(angle_rad),
            math.sin(angle_rad)
        ])
        return Point(*point_coords)

    def _intersect_with_circle(self, other: 'Circle') -> List[Point]:
        """Find intersection points with another circle.

        Args:
            other: Another circle to check for intersections.

        Returns:
            List[Point]: List of intersection points (empty if no intersections).
        """
        # Calculate distance between centers using NumPy for efficiency
        center_vector = other.center.coords - self.center.coords
        d = np.linalg.norm(center_vector)

        # Check for no intersection or one circle inside the other
        if d > self.radius + other.radius:
            return []  # Circles are too far apart

        if d < abs(self.radius - other.radius):
            return []  # One circle is inside the other

        if (abs(d) < 1e-14) and (abs(self.radius - other.radius) < 1e-14):
            return []  # Circles are coincident

        # Handle the case of circles touching at exactly one point
        if abs(d - (self.radius + other.radius)) < 1e-14:  # External touch
            # Calculate the point of tangency
            t = self.radius / (self.radius + other.radius)
            point_coords = self.center.coords + t * (other.center.coords - self.center.coords)
            return [Point(*point_coords)]

        if abs(d - abs(self.radius - other.radius)) < 1e-14:  # Internal touch
            # Calculate the point of tangency
            if self.radius > other.radius:
                t = self.radius / (self.radius - other.radius)
            else:
                t = -self.radius / (other.radius - self.radius)

            point_coords = self.center.coords + t * (other.center.coords - self.center.coords)
            return [Point(*point_coords)]

        # Calculate intersection points
        # Law of cosines to find the angle
        a = (self.radius * self.radius - other.radius * other.radius + d * d) / (2 * d)
        h = math.sqrt(self.radius * self.radius - a * a)

        # Direction vector from self.center to other.center
        direction = (other.center.coords - self.center.coords) / d

        # Find the point P2 which is 'a' away from self.center on the line to other.center
        p2 = self.center.coords + a * direction

        # Compute the perpendicular vector
        perp = np.array([-direction[1], direction[0]])

        # Calculate the intersection points
        p3 = p2 + h * perp
        p4 = p2 - h * perp

        return [Point(*p3), Point(*p4)]


def _intersect_linear_linear(p1: np.ndarray, p2: np.ndarray, a: Union[Segment, Ray, Line], b: Union[Segment, Ray, Line], check1: bool, check2: bool) -> List[Point]:
    """Find the intersection point between two linear objects (i.e., segments, lines, rays).

    Args:
        p1: Point on object 1.
        p2: Point on object 2.
        a: Object 1.
        b: Object 2.
        check1: Determines whether contains_point() is checked on object 1.
        check2: Determines whether contains_point() is checked on object 2.

    Returns:
        List[Point]: List containing the intersection point, or empty list if no intersection.
    """
    pt = _intersect_lines(p1, a.unit_normal, p2, b.unit_normal)

    if pt is None:
        return []

    intersection = Point(*pt)
    if ((check1 and not a.contains_point(intersection)) or
            (check2 and not b.contains_point(intersection))):
        return []

    return [intersection]

def _intersect_linear_circle(lin_pt: np.ndarray, dir: np.ndarray, circle: Circle) -> List[float]:
    """Find the intersection point between a linear object (i.e., segments, lines, rays) and a circle.

    Args:
        lin_pt: Point on linear object.
        dir: Direction vector of linear object.
        circle: Circle.

    Returns:
        List[float]: List containing (relative) position of intersections along the linear object.
    """
    dc = lin_pt - circle.center.coords

    A = np.dot(dir, dir)
    B = np.dot(dc, dir)
    C = np.dot(dc, dc)

    return _solve_quadratic(A, 2 * B, C - circle.radius**2)


def _intersect_circle_circle(c1: Circle, c2: Circle) -> List[Point]:
    """Find intersection points between two circles.

    Args:
        c1: First circle.
        c2: Second circle.

    Returns:
        List[Point]: List of intersection points (empty if no intersections).
    """
    # Calculate distance between centers using NumPy for efficiency
    center_vector = c2.center.coords - c1.center.coords
    d = np.linalg.norm(center_vector)

    # Check for no intersection or one circle inside the other
    if d > c1.radius + c2.radius:
        return []  # Circles are too far apart

    if d < abs(c1.radius - c2.radius):
        return []  # One circle is inside the other

    if (abs(d) < 1e-14) and (abs(c1.radius - c2.radius) < 1e-14):
        return []  # Circles are coincident

    # Handle the case of circles touching at exactly one point
    if abs(d - (c1.radius + c2.radius)) < 1e-14:  # External touch
        # Calculate the point of tangency
        t = c1.radius / (c1.radius + c2.radius)
        point_coords = c1.center.coords + t * (c2.center.coords - c1.center.coords)
        return [Point(*point_coords)]

    if abs(d - abs(c1.radius - c2.radius)) < 1e-14:  # Internal touch
        # Calculate the point of tangency
        if c1.radius > c2.radius:
            t = c1.radius / (c1.radius - c2.radius)
        else:
            t = -c1.radius / (c2.radius - c1.radius)

        point_coords = c1.center.coords + t * (c2.center.coords - c1.center.coords)
        return [Point(*point_coords)]

    # Calculate intersection points
    # Law of cosines to find the angle
    a = (c1.radius * c1.radius - c2.radius * c2.radius + d * d) / (2 * d)
    h = math.sqrt(c1.radius * c1.radius - a * a)

    # Direction vector from c1.center to c2.center
    direction = (c2.center.coords - c1.center.coords) / d

    # Find the point P2 which is 'a' away from c1.center on the line to c2.center
    p2 = c1.center.coords + a * direction

    # Compute the perpendicular vector
    perp = np.array([-direction[1], direction[0]])

    # Calculate the intersection points
    p3 = p2 + h * perp
    p4 = p2 - h * perp

    return [Point(*p3), Point(*p4)]


GEOMETRIC_TYPE = Union[Point, Line, Ray, Circle, Segment]


def intersect(a: GEOMETRIC_TYPE, b: GEOMETRIC_TYPE) -> List[Point]:
    """Find intersections between two geometrical objects.

    Args:
        a: First object.
        b: Second object.

    Returns:
        List[Point]: List containing intersections or empty list if there are no intersections.
    """
    if isinstance(a, Segment):
        if isinstance(b, Segment):
            return _intersect_linear_linear(a.p1.coords, b.p1.coords, a, b, True, True)
        elif isinstance(b, Ray):
            return _intersect_linear_linear(a.p1.coords, b.origin.coords, a, b, True, True)
        elif isinstance(b, Line):
            return _intersect_linear_linear(a.p1.coords, b.point.coords, a, b, True, False)
        elif isinstance(b, Circle):
            t = _intersect_linear_circle(a.p1.coords, a.p2.coords - a.p1.coords, b)
            return [a.point_at_rel_dist(ct) for ct in t if (0 <= ct) and (ct <= 1)]
    elif isinstance(a, Ray):
        if isinstance(b, Segment):
            return _intersect_linear_linear(b.p1.coords, a.origin.coords, b, a, True, True)
        elif isinstance(b, Ray):
            return _intersect_linear_linear(a.origin.coords, b.origin.coords, a, b, True, True)
        elif isinstance(b, Line):
            return _intersect_linear_linear(a.origin.coords, b.point.coords, a, b, True, False)
        elif isinstance(b, Circle):
            t = _intersect_linear_circle(a.origin.coords, a.unit_direction, b)
            return [Point(*(a.origin.coords + ct * a.unit_direction)) for ct in t if (0 <= ct)]
    elif isinstance(a, Line):
        if isinstance(b, Segment):
            return _intersect_linear_linear(b.p1.coords, a.point.coords, b, a, True, False)
        elif isinstance(b, Ray):
            return _intersect_linear_linear(b.origin.coords, a.point.coords, b, a, True, False)
        elif isinstance(b, Line):
            return _intersect_linear_linear(a.point.coords, b.point.coords, a, b, False, False)
        elif isinstance(b, Circle):
            t = _intersect_linear_circle(a.point.coords, a.unit_direction, b)
            return [Point(*(a.point.coords + ct * a.unit_direction)) for ct in t]
    elif isinstance(a, Circle):
        if isinstance(b, Segment):
            t = _intersect_linear_circle(b.p1.coords, b.p2.coords - b.p1.coords, a)
            return [b.point_at_rel_dist(ct) for ct in t if (0 <= ct) and (ct <= 1)]
        elif isinstance(b, Ray):
            t = _intersect_linear_circle(b.origin.coords, b.unit_direction, a)
            return [Point(*(b.origin.coords + ct * b.unit_direction)) for ct in t if (0 <= ct)]
        elif isinstance(b, Line):
            t = _intersect_linear_circle(b.point.coords, b.unit_direction, a)
            return [Point(*(b.point.coords + ct * b.unit_direction)) for ct in t if (0 <= ct)]
        elif isinstance(b, Circle):
            return _intersect_circle_circle(a, b)

    raise TypeError(f"Intersection not implemented for {type(a)} and {type(b)}")
