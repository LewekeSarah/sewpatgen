"""
2D Geometry Module for CAD Operations.

This module provides classes for fundamental 2D geometric primitives such as
points, lines, segments, rays, and circles for use in CAD applications.
"""

import math
import numpy as np
from dataclasses import dataclass
from sewpat.units import MM, CM

# svgpathtools is used as a backend for Bezier–Bezier intersection.
# It implements the numerically robust Bézier-clipping algorithm (Sederberg &
# Nishita 1990) which converges quadratically and avoids the O(n²) sampling
# artefacts of a brute-force grid scan.
from svgpathtools import CubicBezier as _SvgCubicBezier


def _solve_quadratic(a: float, b: float, c: float) -> list[float]:
    """Solve a quadratic equation ax^2 + bx + c = 0 in a numerically stable way.

    Uses a numerically stable algorithm to find solutions by avoiding
    subtractive cancellation.

    Args:
        a: Coefficient of the quadratic term.
        b: Coefficient of the linear term.
        c: Constant term.

    Returns:
        list[float]: A list containing 0, 1, or 2 solutions.
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
        return [-b / (2 * a)]

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


def _intersect_lines(
    pt1: np.ndarray, n1: np.ndarray, pt2: np.ndarray, n2: np.ndarray
) -> np.ndarray | None:
    """Find intersection of two lines represented by a point on the line and the unit normal.

    Args:
        pt1: Point on first line.
        n1: Unit normal of first line.
        pt2: Point on second line.
        n2: Unit normal of second line.

    Returns:
        np.ndarray | None: Intersection between the two lines if they are not parallel.
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
    name: str | None = None

    def __init__(self, x: float, y: float, name: str | None = None):
        """Initialize a point with x and y coordinates.

        Args:
            x: The x-coordinate of the point.
            y: The y-coordinate of the point.
            name: Optional, name of the point.
        """
        # Use object.__setattr__ to set values in a frozen dataclass
        object.__setattr__(self, "coords", np.array([x, y], dtype=float))
        object.__setattr__(self, "name", name)

    @property
    def x(self) -> float:
        """Get the x coordinate."""
        return float(self.coords[0])

    @property
    def y(self) -> float:
        """Get the y coordinate."""
        return float(self.coords[1])

    def __str__(self) -> str:
        if self.name:
            return f"Point(name={self.name}, x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"
        else:
            return f"Point(x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"

    def distance_to(self, other: Point | np.ndarray) -> float:
        """Calculate the Euclidean distance between this point and another."""
        if isinstance(other, Point):
            return float(np.linalg.norm(self.coords - other.coords))
        else:
            return float(np.linalg.norm(self.coords - other))

    def translate(self, dx: float, dy: float) -> "Point":
        """Return a new point translated by the given vector.

        Args:
            dx: Translation distance along the x-axis.
            dy: Translation distance along the y-axis.

        Returns:
            Point: A new point translated by the specified vector.
        """
        translation = np.array([dx, dy])
        return Point(*(self.coords + translation))

    def rotate(self, center: "Point", angle_rad: float) -> "Point":
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
        rotation_matrix = np.array([[cos_a, -sin_a], [sin_a, cos_a]])

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

    def __init__(self, p1: Point, p2: Point, name: str | None = None):
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

    def point_at_t(self, t: float) -> Point:
        """Calculate a point on the line segment at relative parameter t.

        Args:
            t: Parameter value in [0, 1]. t=0 corresponds to p1, t=1 to p2.

        Returns:
            Point: Position on the line segment at parameter t.
        """
        assert (0 <= t) and (t <= 1), f"{t = } expected in [0, 1]"
        return Point(*((1.0 - t) * self.p1.coords + t * self.p2.coords))

    def point_at_rel_dist(self, rel_pos: float) -> Point:
        """Deprecated alias for ``point_at_t()``. Use ``point_at_t()`` instead."""
        return self.point_at_t(rel_pos)

    def point_perpendicular(
        self,
        distance_to_obj: float,
        distance_on_obj: float | None = None,
        rel_pos_on_obj: float | None = None,
    ) -> Point:
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
            >>> line = Line(Point(0, 0), [10, 0])
            >>> point = line.point_perpendicular(5, rel_pos_on_obj=0.5)
            >>> print(point)
            Point(5, 5)
        """
        if ((distance_on_obj is None) and (rel_pos_on_obj is None)) or (
            (distance_on_obj is not None) and (rel_pos_on_obj is not None)
        ):
            raise ValueError(
                "exactly one of distance_on_obj and rel_pos_on_obj has to be set"
            )

        if distance_on_obj:
            dir = self.unit_direction
            base = self.p1.coords + distance_on_obj * dir
        else:
            assert (0 <= rel_pos_on_obj) and (
                rel_pos_on_obj <= 1.0
            ), f"rel_pos_on_obj = {rel_pos_on_obj} required in [0, 1]"
            base = (
                1.0 - rel_pos_on_obj
            ) * self.p1.coords + rel_pos_on_obj * self.p2.coords

        return Point(*(base + self.unit_normal * distance_to_obj))

    def project_point(self, point: "Point") -> "Point":
        """Return the orthogonal projection of *point* onto this segment's line.

        The result is the closest point on the infinite line through p1 and p2.
        It is not clamped to the segment endpoints.

        Args:
            point: The point to project.

        Returns:
            Point: The foot of the perpendicular from *point* to the segment line.
        """
        p1 = self.p1.coords
        d = self.p2.coords - p1
        t = float(np.dot(point.coords - p1, d) / np.dot(d, d))
        return Point(*(p1 + t * d))

    def contains_point(self, point: Point, tolerance: float = 1e-12) -> bool:
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

    def point_at_length(self, arc_length: float) -> "Point":
        """Return the point at a given arc length from p1 along the segment.

        Mirrors ``CubicBezier.point_at_length()`` for API consistency.

        Args:
            arc_length: Distance from p1 along the segment (mm).

        Returns:
            Point on the segment at the given distance from p1.

        Raises:
            ValueError: If arc_length is negative or exceeds the segment length.
        """
        total = self.length
        if arc_length < 0 or arc_length > total + 1e-9:
            raise ValueError(f"arc_length {arc_length:.4f} is outside [0, {total:.4f}]")
        return self.point_at_rel_dist(arc_length / total)

    def bounding_box(self) -> tuple["Point", "Point"]:
        """Return the axis-aligned bounding box of the segment.

        Mirrors ``CubicBezier.bounding_box()`` for API consistency.

        Returns:
            Tuple of (min_point, max_point).
        """
        min_x = min(self.p1.x, self.p2.x)
        min_y = min(self.p1.y, self.p2.y)
        max_x = max(self.p1.x, self.p2.x)
        max_y = max(self.p1.y, self.p2.y)
        return Point(min_x, min_y), Point(max_x, max_y)


class Ray:
    """A ray starting from a point and going in a specific direction.

    Attributes:
        origin: The starting point of the ray.
        direction: Normalized direction vector of the ray.
        name: Optional, name of the ray.
    """

    def __init__(
        self,
        origin: Point,
        direction: tuple[float, float] | list[float] | np.ndarray,
        name: str | None = None,
    ):
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
            distance: The distance from the origin along the ray direction.

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

    def point_perpendicular(
        self, distance_to_obj: float, distance_on_obj: float
    ) -> Point:
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

    def __init__(
        self,
        point: Point,
        direction: tuple[float, float] | list[float] | np.ndarray,
        name: str | None = None,
    ):
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
            distance: The distance from the base point along the line direction.

        Returns:
            Point: A point on the line at the specified distance from the base point.
        """
        point_coords = self.point.coords + self.direction * distance
        return Point(*point_coords)

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Check if a point lies on the line.

        Args:
            point: The point to check.
            tolerance: The maximum angular deviation allowed.

        Returns:
            bool: True if the point lies on the line within tolerance, False otherwise.
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

    def point_perpendicular(
        self, distance_to_obj: float, distance_on_obj: float
    ) -> Point:
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


class Rect:
    """An axis-aligned rectangle defined by its top-left corner, width and height.

    Attributes:
        origin: The top-left corner of the rectangle.
        width: The width of the rectangle.
        height: The height of the rectangle.
        name: Optional label displayed in the centre of the rectangle.
    """

    def __init__(
        self,
        origin: Point,
        width: float,
        height: float,
        name: str | None = None,
    ):
        self.origin = origin
        self.width = width
        self.height = height
        self.name = name


class Triangle:
    """A triangle defined by three points.

    Used for notch symbols on sewing patterns: a small filled triangle
    standing on the seam edge and pointing inward.

    Attributes:
        p1: First vertex (base left).
        p2: Second vertex (base right).
        p3: Third vertex (tip, pointing inward).
        name: Optional label.
    """

    def __init__(self, p1: Point, p2: Point, p3: Point, name: str | None = None):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.name = name


class InfoBox:
    """A text info box displayed at a given position.

    Typically placed at the centroid of a pattern part, showing the part
    name as a header and optional notes (e.g. seam allowance information).

    Attributes:
        position: Centre point of the info box.
        header: Bold header text (usually the part name).
        notes: Optional list of additional lines shown below the header.
    """

    def __init__(
        self,
        position: Point,
        header: str,
        notes: "list[str] | None" = None,
    ):
        self.position = position
        self.header = header
        self.notes: list[str] = notes if notes is not None else []
        self.name: str | None = None


class Circle:
    """A circle defined by a center point and radius.

    Attributes:
        center: The center point of the circle.
        radius: The radius of the circle.
        name: Optional, name of the circle.
    """

    def __init__(self, center: Point, radius: float, name: str | None = None):
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

    def contains_point_inside(
        self, point: Point, include_boundary: bool = True
    ) -> bool:
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
        point_coords = self.center.coords + self.radius * np.array(
            [math.cos(angle_rad), math.sin(angle_rad)]
        )
        return Point(*point_coords)

    def _intersect_with_circle(self, other: "Circle") -> List[Point]:
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
            point_coords = self.center.coords + t * (
                other.center.coords - self.center.coords
            )
            return [Point(*point_coords)]

        if abs(d - abs(self.radius - other.radius)) < 1e-14:  # Internal touch
            # Calculate the point of tangency
            if self.radius > other.radius:
                t = self.radius / (self.radius - other.radius)
            else:
                t = -self.radius / (other.radius - self.radius)

            point_coords = self.center.coords + t * (
                other.center.coords - self.center.coords
            )
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


def _intersect_linear_linear(
    p1: np.ndarray,
    p2: np.ndarray,
    a: Segment | Ray | Line,
    b: Segment | Ray | Line,
    check1: bool,
    check2: bool,
) -> list[Point]:
    """Find the intersection point between two linear objects (i.e., segments, lines, rays).

    Args:
        p1: Point on object 1.
        p2: Point on object 2.
        a: Object 1.
        b: Object 2.
        check1: Determines whether contains_point() is checked on object 1.
        check2: Determines whether contains_point() is checked on object 2.

    Returns:
        list[Point]: List containing the intersection point, or empty list if no intersection.
    """
    pt = _intersect_lines(p1, a.unit_normal, p2, b.unit_normal)

    if pt is None:
        return []

    intersection = Point(*pt)
    if (check1 and not a.contains_point(intersection)) or (
        check2 and not b.contains_point(intersection)
    ):
        return []

    return [intersection]


def _solve_cubic(a: float, b: float, c: float, d: float) -> list[float]:
    """Solve a cubic equation ax³ + bx² + cx + d = 0.

    Args:
        a, b, c, d: Coefficients of the cubic equation.

    Returns:
        List of real roots.
    """
    eps = 1e-10

    if abs(a) < eps:
        # Degenerate to quadratic
        return _solve_quadratic(b, c, d)

    # Normalize coefficients
    b /= a
    c /= a
    d /= a

    # Substitute x = t - b/3 to eliminate quadratic term
    # Results in t³ + pt + q = 0
    p = c - b * b / 3
    q = d - b * c / 3 + 2 * b * b * b / 27

    # Use Cardano's formula
    discriminant = (q / 2) ** 2 + (p / 3) ** 3

    roots = []

    if discriminant > eps:
        # One real root
        sqrt_disc = math.sqrt(discriminant)
        u = (
            (-q / 2 + sqrt_disc) ** (1 / 3)
            if (-q / 2 + sqrt_disc) >= 0
            else -(abs(-q / 2 + sqrt_disc) ** (1 / 3))
        )
        v = (
            (-q / 2 - sqrt_disc) ** (1 / 3)
            if (-q / 2 - sqrt_disc) >= 0
            else -(abs(-q / 2 - sqrt_disc) ** (1 / 3))
        )
        roots.append(u + v - b / 3)
    elif abs(discriminant) < eps:
        # Two or three real roots
        if abs(q) < eps:
            # Triple root
            roots.append(-b / 3)
        else:
            # One single and one double root
            u = (-q / 2) ** (1 / 3) if (-q / 2) >= 0 else -(abs(-q / 2) ** (1 / 3))
            roots.extend([2 * u - b / 3, -u - b / 3])
    else:
        # Three distinct real roots
        rho = math.sqrt(-((p / 3) ** 3))
        theta = math.acos(-q / 2 / rho)

        for k in range(3):
            root = (
                2 * (rho ** (1 / 3)) * math.cos((theta + 2 * math.pi * k) / 3) - b / 3
            )
            roots.append(root)

    return roots


def _intersect_bezier_line(
    bezier: CubicBezier, line_point: np.ndarray, line_dir: np.ndarray
) -> list[float]:
    """Find intersection parameters t where a cubic Bezier intersects a line.

    Args:
        bezier: The cubic Bezier curve.
        line_point: A point on the line.
        line_dir: Direction vector of the line (should be normalized).

    Returns:
        List of t parameters where intersections occur.
    """
    # Line equation: P = line_point + s * line_dir
    # Bezier equation: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
    #
    # For intersection: B(t) lies on the line
    # We can use the implicit line equation: (P - line_point) × line_dir = 0
    # where × is the 2D cross product (determinant)

    # Get perpendicular to line direction for implicit form
    line_perp = np.array([-line_dir[1], line_dir[0]])

    # Coefficients for the cubic equation in t
    # B(t) = a₃t³ + a₂t² + a₁t + a₀ where:
    a0 = bezier.p0.coords
    a1 = 3 * (bezier.p1.coords - bezier.p0.coords)
    a2 = 3 * (bezier.p2.coords - 2 * bezier.p1.coords + bezier.p0.coords)
    a3 = (
        bezier.p3.coords
        - 3 * bezier.p2.coords
        + 3 * bezier.p1.coords
        - bezier.p0.coords
    )

    # Distance from line_point to each coefficient projected onto line_perp
    d0 = np.dot(a0 - line_point, line_perp)
    d1 = np.dot(a1, line_perp)
    d2 = np.dot(a2, line_perp)
    d3 = np.dot(a3, line_perp)

    # Solve cubic equation: d₃t³ + d₂t² + d₁t + d₀ = 0
    return _solve_cubic(d3, d2, d1, d0)


class CubicBezier:
    """A 2D cubic Bezier curve defined by four control points.

    The curve starts at p0, is influenced by control points p1 and p2,
    and ends at p3. The parameter t varies from 0 to 1.

    Attributes:
        p0: Start point of the curve.
        p1: First control point.
        p2: Second control point.
        p3: End point of the curve.
    """

    def __init__(
        self, p0: Point, p1: Point, p2: Point, p3: Point, name: str | None = None
    ):
        """Initialize a cubic Bezier curve with four control points.

        Args:
            p0: Start point of the curve.
            p1: First control point.
            p2: Second control point.
            p3: End point of the curve.
            name: The name of the curve.
        """
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.name = name

    def __str__(self) -> str:
        return f"CubicBezier(name={self.name}, p0={self.p0}, p1={self.p1}, p2={self.p2}, p3={self.p3})"

    def point_at_t(self, t: float) -> Point:
        """Evaluate the Bezier curve at parameter t.

        Args:
            t: Parameter value, typically between 0 and 1.

        Returns:
            Point on the curve at parameter t.
        """
        # Cubic Bezier formula: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
        t2 = t * t
        t3 = t2 * t
        mt = 1.0 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        x = (
            mt3 * self.p0.x
            + 3 * mt2 * t * self.p1.x
            + 3 * mt * t2 * self.p2.x
            + t3 * self.p3.x
        )

        y = (
            mt3 * self.p0.y
            + 3 * mt2 * t * self.p1.y
            + 3 * mt * t2 * self.p2.y
            + t3 * self.p3.y
        )

        return Point(x, y)

    def _svg(self) -> _SvgCubicBezier:
        """Return an equivalent svgpathtools CubicBezier for delegated calculations."""
        return _SvgCubicBezier(
            complex(self.p0.x, self.p0.y),
            complex(self.p1.x, self.p1.y),
            complex(self.p2.x, self.p2.y),
            complex(self.p3.x, self.p3.y),
        )

    def length(self) -> float:
        """Compute the exact arc length of the Bézier curve.

        Delegates to ``svgpathtools``, which uses Gauss-Legendre quadrature
        for a numerically exact result – unlike a polyline approximation.

        Returns:
            Arc length of the curve in the same units as the control points.
        """
        return self._svg().length()

    def tangent_at_t(self, t: float) -> np.ndarray:
        """Compute the tangent vector at parameter t.

        Delegates to ``svgpathtools.derivative()``, which evaluates B'(t)
        analytically.

        Args:
            t: Parameter value, typically between 0 and 1.

        Returns:
            Tangent vector as a numpy array (not normalised).
        """
        d = self._svg().derivative(t)
        return np.array([d.real, d.imag])

    def normal_at_t(self, t: float) -> np.ndarray:
        """Compute the unit normal vector at parameter t.

        The normal points 90° counter-clockwise from the tangent direction
        (i.e. to the *left* of the travel direction), consistent with the
        convention used by ``Segment.unit_normal``.

        This is the correct direction vector for offsetting a point on the
        curve by a seam allowance.

        Args:
            t: Parameter value, typically between 0 and 1.

        Returns:
            Unit normal vector as a numpy array.
        """
        n = self._svg().normal(t)
        return np.array([n.real, n.imag])

    def point_at_length(self, arc_length: float) -> "Point":
        """Return the point on the curve at a given arc length from the start.

        Uses ``svgpathtools.ilength()`` (inverse arc-length) which solves for
        the parameter *t* corresponding to the requested arc length via
        Gauss-Legendre quadrature – the same method used by ``length()``.

        Typical use: place a notch exactly 3 cm from the start of a curved
        seam edge.

        Args:
            arc_length: Distance along the curve from p0, in the same units
                as the control points (mm).

        Returns:
            Point on the curve at the given arc length.

        Raises:
            ValueError: If arc_length is negative or exceeds the curve length.
        """
        total = self.length()
        if arc_length < 0 or arc_length > total + 1e-9:
            raise ValueError(f"arc_length {arc_length:.4f} is outside [0, {total:.4f}]")
        t = self._svg().ilength(arc_length)
        return self.point_at_t(t)

    def split(self, t: float) -> tuple["CubicBezier", "CubicBezier"]:
        """Split the curve at parameter t into two cubic Bézier curves.

        Delegates to ``svgpathtools.split()``, which uses the de Casteljau
        algorithm for numerically stable subdivision.

        Args:
            t: Parameter value at which to split (0 < t < 1).

        Returns:
            Tuple of (left, right) CubicBezier curves, where *left* covers
            the original curve from 0 to t and *right* from t to 1.
        """
        left, right = self._svg().split(t)
        return (
            CubicBezier(
                Point(left.start.real, left.start.imag),
                Point(left.control1.real, left.control1.imag),
                Point(left.control2.real, left.control2.imag),
                Point(left.end.real, left.end.imag),
            ),
            CubicBezier(
                Point(right.start.real, right.start.imag),
                Point(right.control1.real, right.control1.imag),
                Point(right.control2.real, right.control2.imag),
                Point(right.end.real, right.end.imag),
            ),
        )

    def bounding_box(self) -> tuple[Point, Point]:
        """Compute the axis-aligned bounding box of the Bezier curve.

        Only the start and end points (p0, p3) lie on the curve itself.
        The control points p1 and p2 act as "magnets" and may lie well
        outside the actual curve, so they must NOT be used as bounding-box
        seeds. Instead the true extrema are found analytically by solving
        B'(t) = 0 and evaluating the curve at the resulting t values.

        Returns:
            Tuple of (min_point, max_point) defining the bounding box.
        """
        # Seed with the two curve endpoints only (they are always on the curve)
        x_coords = [self.p0.x, self.p3.x]
        y_coords = [self.p0.y, self.p3.y]

        # Find extrema by solving derivative = 0
        # For x: 3(1-t)²(P₁-P₀) + 6(1-t)t(P₂-P₁) + 3t²(P₃-P₂) = 0
        # This simplifies to: at² + bt + c = 0 where:
        a_x = 3 * (self.p3.x - 3 * self.p2.x + 3 * self.p1.x - self.p0.x)
        b_x = 6 * (self.p2.x - 2 * self.p1.x + self.p0.x)
        c_x = 3 * (self.p1.x - self.p0.x)

        a_y = 3 * (self.p3.y - 3 * self.p2.y + 3 * self.p1.y - self.p0.y)
        b_y = 6 * (self.p2.y - 2 * self.p1.y + self.p0.y)
        c_y = 3 * (self.p1.y - self.p0.y)

        # Solve for critical points
        for a, b, c in [(a_x, b_x, c_x), (a_y, b_y, c_y)]:
            if abs(a) > 1e-10:  # Quadratic case
                roots = _solve_quadratic(a, b, c)
                for t in roots:
                    if 0 <= t <= 1:
                        point = self.point_at_t(t)
                        x_coords.append(point.x)
                        y_coords.append(point.y)
            elif abs(b) > 1e-10:  # Linear case
                t = -c / b
                if 0 <= t <= 1:
                    point = self.point_at_t(t)
                    x_coords.append(point.x)
                    y_coords.append(point.y)

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        return Point(min_x, min_y), Point(max_x, max_y)

    def point_perpendicular(self, distance_to_obj: float, t: float) -> "Point":
        """Return a point offset perpendicularly from the curve at parameter t.

        Mirrors ``Segment.point_perpendicular()`` / ``Ray.point_perpendicular()``
        / ``Line.point_perpendicular()`` for API consistency, adapted to the
        curve case where the normal direction varies along the curve.

        Positive *distance_to_obj* is to the left of the travel direction (same
        sign convention as ``unit_normal`` on linear objects).

        Typical use: offset a point on a seam line by the seam allowance.

        Args:
            distance_to_obj: Perpendicular offset in mm. Positive = left of
                direction, negative = right of direction.
            t: Parameter value on the curve (0 = p0, 1 = p3).

        Returns:
            Point offset by *distance_to_obj* in the normal direction at *t*.
        """
        pt = self.point_at_t(t)
        nor = self.normal_at_t(t)
        return Point(pt.x + distance_to_obj * nor[0], pt.y + distance_to_obj * nor[1])

    def contains_point(self, point: "Point", tolerance: float = 0.01) -> bool:
        """Check whether a point lies on the curve within a given tolerance.

        Mirrors ``Segment.contains_point()`` / ``Ray.contains_point()`` /
        ``Line.contains_point()`` for API consistency.

        Because there is no closed-form inverse for a cubic Bézier, the check
        is performed by finding the closest point on the curve via
        ``point_at_length`` + binary search on the arc-length parameter and
        comparing the distance.

        Args:
            point: The point to test.
            tolerance: Maximum Euclidean distance (mm) allowed for the point
                to be considered on the curve. Defaults to 0.01 mm.

        Returns:
            True if the closest point on the curve is within *tolerance* of
            *point*, False otherwise.
        """
        # Coarse search: sample 200 points, keep the best t
        best_t = 0.0
        best_d = point.distance_to(self.p0)
        for i in range(1, 201):
            t = i / 200
            d = point.distance_to(self.point_at_t(t))
            if d < best_d:
                best_d, best_t = d, t

        # Early exit if already within tolerance
        if best_d <= tolerance:
            return True

        # Refine with binary search around best_t (±1/200 bracket)
        lo = max(0.0, best_t - 1 / 200)
        hi = min(1.0, best_t + 1 / 200)
        for _ in range(30):
            m1 = lo + (hi - lo) / 3
            m2 = hi - (hi - lo) / 3
            if point.distance_to(self.point_at_t(m1)) < point.distance_to(
                self.point_at_t(m2)
            ):
                hi = m2
            else:
                lo = m1
        best_d = point.distance_to(self.point_at_t((lo + hi) / 2))
        return best_d <= tolerance


def _intersect_linear_circle(
    lin_pt: np.ndarray, dir: np.ndarray, circle: Circle
) -> list[float]:
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


def _intersect_circle_circle(c1: Circle, c2: Circle) -> list[Point]:
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


def _intersect_bezier_bezier(
    a: "CubicBezier", b: "CubicBezier", tol: float = 1e-12
) -> list["Point"]:
    """Find intersections between two cubic Bézier curves.

    Uses ``svgpathtools`` as a backend, which implements the numerically robust
    Bézier-clipping algorithm (Sederberg & Nishita 1990). The algorithm
    converges quadratically and reliably finds all transversal intersections
    without O(n²) sampling artefacts.

    Args:
        a: First cubic Bézier curve.
        b: Second cubic Bézier curve.
        tol: Distance tolerance for duplicate-intersection filtering (mm).
             Defaults to 1e-12 (effectively exact).

    Returns:
        List of intersection points on curve *a*.
    """
    svg_a = _SvgCubicBezier(
        complex(a.p0.x, a.p0.y),
        complex(a.p1.x, a.p1.y),
        complex(a.p2.x, a.p2.y),
        complex(a.p3.x, a.p3.y),
    )
    svg_b = _SvgCubicBezier(
        complex(b.p0.x, b.p0.y),
        complex(b.p1.x, b.p1.y),
        complex(b.p2.x, b.p2.y),
        complex(b.p3.x, b.p3.y),
    )
    intersections: list[Point] = []
    for t1, _t2 in svg_a.intersect(svg_b):
        pt = a.point_at_t(t1)
        if not any(pt.distance_to(ex) < tol for ex in intersections):
            intersections.append(pt)
    return intersections


GEOMETRIC_TYPE = (
    Point | Line | Ray | Circle | Segment | Rect | Triangle | InfoBox | CubicBezier
)


def intersect(a: GEOMETRIC_TYPE, b: GEOMETRIC_TYPE) -> list[Point]:
    """Find intersections between two geometrical objects.

    Args:
        a: First object.
        b: Second object.

    Returns:
        list[Point]: List containing intersections or empty list if there are no intersections.
    """
    if isinstance(a, Segment):
        if isinstance(b, Segment):
            return _intersect_linear_linear(a.p1.coords, b.p1.coords, a, b, True, True)
        elif isinstance(b, Ray):
            return _intersect_linear_linear(
                a.p1.coords, b.origin.coords, a, b, True, True
            )
        elif isinstance(b, Line):
            return _intersect_linear_linear(
                a.p1.coords, b.point.coords, a, b, True, False
            )
        elif isinstance(b, Circle):
            t = _intersect_linear_circle(a.p1.coords, a.p2.coords - a.p1.coords, b)
            return [a.point_at_rel_dist(ct) for ct in t if (0 <= ct) and (ct <= 1)]
        elif isinstance(b, CubicBezier):
            # Segment-Bezier intersection (swap and reuse Bezier-Segment logic)
            return intersect(b, a)
    elif isinstance(a, Ray):
        if isinstance(b, Segment):
            return _intersect_linear_linear(
                b.p1.coords, a.origin.coords, b, a, True, True
            )
        elif isinstance(b, Ray):
            return _intersect_linear_linear(
                a.origin.coords, b.origin.coords, a, b, True, True
            )
        elif isinstance(b, Line):
            return _intersect_linear_linear(
                a.origin.coords, b.point.coords, a, b, True, False
            )
        elif isinstance(b, Circle):
            t = _intersect_linear_circle(a.origin.coords, a.unit_direction, b)
            return [
                Point(*(a.origin.coords + ct * a.unit_direction))
                for ct in t
                if (0 <= ct)
            ]
        elif isinstance(b, CubicBezier):
            # Ray-Bezier intersection (swap and reuse Bezier-Ray logic)
            return intersect(b, a)
    elif isinstance(a, Line):
        if isinstance(b, Segment):
            return _intersect_linear_linear(
                b.p1.coords, a.point.coords, b, a, True, False
            )
        elif isinstance(b, Ray):
            return _intersect_linear_linear(
                b.origin.coords, a.point.coords, b, a, True, False
            )
        elif isinstance(b, Line):
            return _intersect_linear_linear(
                a.point.coords, b.point.coords, a, b, False, False
            )
        elif isinstance(b, Circle):
            t = _intersect_linear_circle(a.point.coords, a.unit_direction, b)
            return [Point(*(a.point.coords + ct * a.unit_direction)) for ct in t]
        elif isinstance(b, CubicBezier):
            # Line-Bezier intersection (swap and reuse Bezier-Line logic)
            return intersect(b, a)
    elif isinstance(a, Circle):
        if isinstance(b, Segment):
            t = _intersect_linear_circle(b.p1.coords, b.p2.coords - b.p1.coords, a)
            return [b.point_at_rel_dist(ct) for ct in t if (0 <= ct) and (ct <= 1)]
        elif isinstance(b, Ray):
            t = _intersect_linear_circle(b.origin.coords, b.unit_direction, a)
            return [
                Point(*(b.origin.coords + ct * b.unit_direction))
                for ct in t
                if (0 <= ct)
            ]
        elif isinstance(b, Line):
            t = _intersect_linear_circle(b.point.coords, b.unit_direction, a)
            return [
                Point(*(b.point.coords + ct * b.unit_direction))
                for ct in t
                if (0 <= ct)
            ]
        elif isinstance(b, Circle):
            return _intersect_circle_circle(a, b)
        elif isinstance(b, CubicBezier):
            # Circle-Bezier intersection (swap and reuse Bezier-Circle logic)
            return intersect(b, a)
    elif isinstance(a, CubicBezier):
        if isinstance(b, Segment):
            # Bezier-Segment intersection
            seg_dir = b.unit_direction
            t_values = _intersect_bezier_line(a, b.p1.coords, seg_dir)
            intersections = []
            for t in t_values:
                if 0 <= t <= 1:
                    bezier_point = a.point_at_t(t)
                    # Check if point lies on segment
                    if b.contains_point(bezier_point):
                        intersections.append(bezier_point)
            return intersections
        elif isinstance(b, Ray):
            # Bezier-Ray intersection
            t_values = _intersect_bezier_line(a, b.origin.coords, b.unit_direction)
            intersections = []
            for t in t_values:
                if 0 <= t <= 1:
                    bezier_point = a.point_at_t(t)
                    # Check if point is in ray direction
                    to_point = bezier_point.coords - b.origin.coords
                    if np.dot(to_point, b.unit_direction) >= 0:
                        intersections.append(bezier_point)
            return intersections
        elif isinstance(b, Line):
            # Bezier-Line intersection
            t_values = _intersect_bezier_line(a, b.point.coords, b.unit_direction)
            return [a.point_at_t(t) for t in t_values if 0 <= t <= 1]
        elif isinstance(b, Circle):
            # Bezier-Circle intersection (approximate using sampling)
            intersections = []
            num_samples = 1000
            prev_point = a.point_at_t(0)

            for i in range(1, num_samples + 1):
                t = i / num_samples
                curr_point = a.point_at_t(t)

                # Check if segment crosses circle boundary
                prev_inside = b.contains_point_inside(prev_point)
                curr_inside = b.contains_point_inside(curr_point)

                if prev_inside != curr_inside:
                    # Binary search for more precise intersection
                    t_start = (i - 1) / num_samples
                    t_end = t

                    for _ in range(20):  # Binary search iterations
                        t_mid = (t_start + t_end) / 2
                        mid_point = a.point_at_t(t_mid)
                        mid_inside = b.contains_point_inside(mid_point)

                        if mid_inside == prev_inside:
                            t_start = t_mid
                        else:
                            t_end = t_mid

                    intersections.append(a.point_at_t((t_start + t_end) / 2))

                prev_point = curr_point

            return intersections
        elif isinstance(b, CubicBezier):
            return _intersect_bezier_bezier(a, b)

    raise TypeError(f"Intersection not implemented for {type(a)} and {type(b)}")


def segment_to_intersection(
    start: Point, dir: np.ndarray, obj: GEOMETRIC_TYPE
) -> tuple[Point, Segment]:
    """Creates a Segment from the given start point to the intersection with an object in given direction.

    Args:
        start: Start point of the new segment.
        dir: Direction for finding intersection.
        obj: Other object that is intersected by a ray from start in direction dir.

    Returns:
        Point: Intersection point with obj.
        Segment: Segment from start to intersection with obj in direction dir.
    """
    pt = intersect(Ray(start, dir), obj)[0]
    return pt, Segment(start, pt)
