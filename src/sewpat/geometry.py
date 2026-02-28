"""
2D Geometry Module for CAD Operations.

This module provides classes for fundamental 2D geometric primitives such as
points, lines, segments, rays, and circles for use in CAD applications.
"""

import math
import numpy as np
from dataclasses import dataclass
from sewpat.units import MM, CM
import shapely.geometry as _sg

from svgpathtools import CubicBezier as _SvgCubicBezier


def _solve_quadratic(a: float, b: float, c: float) -> list[float]:
    """Solve ax² + bx + c = 0. Used by CubicBezier.bounding_box()."""
    if abs(a) < 1e-14:
        return [] if abs(b) < 1e-14 else [-c / b]
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return []
    if abs(discriminant) < 1e-14:
        return [-b / (2 * a)]
    s = math.sqrt(discriminant)
    q = -0.5 * (b + s) if b >= 0 else -0.5 * (b - s)
    x1, x2 = q / a, c / q
    return [x1, x2] if x1 <= x2 else [x2, x1]


def _intersect_lines(
    pt1: np.ndarray, n1: np.ndarray, pt2: np.ndarray, n2: np.ndarray
) -> np.ndarray | None:
    """Find intersection of two infinite lines given a point and unit normal each.

    Uses Shapely's robust GEOS backend instead of manual Cramer's rule.

    Returns:
        np.ndarray | None: Intersection point, or None if lines are parallel.
    """
    # Convert normal → direction (rotate 90°)
    d1 = np.array([n1[1], -n1[0]])
    d2 = np.array([n2[1], -n2[0]])
    far = 1e9
    line1 = _sg.LineString([pt1 - far * d1, pt1 + far * d1])
    line2 = _sg.LineString([pt2 - far * d2, pt2 + far * d2])
    result = line1.intersection(line2)
    if result.is_empty or result.geom_type != "Point":
        return None
    return np.array([result.x, result.y])


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

    def translate(self, dx: float, dy: float) -> Point:
        """Return a new point translated by the given vector.

        Args:
            dx: Translation distance along the x-axis.
            dy: Translation distance along the y-axis.

        Returns:
            Point: A new point translated by the specified vector.
        """
        translation = np.array([dx, dy])
        return Point(*(self.coords + translation))

    def rotate(self, center: Point, angle_rad: float) -> Point:
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

    def project_point(self, point: Point) -> Point:
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

    def contains_point(self, point: Point, tolerance: float = 1e-9) -> bool:
        """Check if a point lies on the line segment.

        Uses Shapely's GEOS backend (``LineString.distance()``) for robust
        floating-point behaviour instead of the triangle-inequality check.

        Args:
            point: The point to check.
            tolerance: The maximum distance (mm) allowed for the point to be
                considered on the segment. Defaults to 1e-9 mm.

        Returns:
            bool: True if the point lies on the line segment within tolerance,
                False otherwise.
        """
        ls = _sg.LineString([(self.p1.x, self.p1.y), (self.p2.x, self.p2.y)])
        return ls.distance(_sg.Point(point.x, point.y)) <= tolerance

    def point_at_length(self, arc_length: float) -> Point:
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

    def bounding_box(self) -> tuple[Point, Point]:
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

    def offset(self, distance: float, center: Point | None = None) -> Segment:
        """Return a new Segment offset perpendicularly by *distance*.

        The offset direction is chosen so that the result moves *away* from
        *center* (i.e. outward from the interior of the pattern piece).  If
        *center* is ``None`` the sign of *distance* controls the direction
        directly: positive = left of the travel direction, negative = right.

        Args:
            distance: Perpendicular offset in mm. When *center* is provided the
                absolute value is used and the sign is derived from *center*.
            center: Interior reference point (e.g. ``PatternPart.centroid``).
                When given the offset is forced *away* from this point.

        Returns:
            A new ``Segment`` with both endpoints shifted by *distance* along
            the outward unit normal.
        """
        normal = self.unit_normal  # points left of travel direction
        if center is not None:
            mid = 0.5 * (self.p1.coords + self.p2.coords)
            # Flip if normal points toward the interior (toward center)
            if np.dot(normal, mid - center.coords) < 0:
                normal = -normal
            offset_vec = normal * abs(distance)
        else:
            offset_vec = normal * distance
        new_p1 = Point(*(self.p1.coords + offset_vec))
        new_p2 = Point(*(self.p2.coords + offset_vec))
        return Segment(new_p1, new_p2, name=self.name)


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
        notes: list[str] | None = None,
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

    def _intersect_with_circle(self, other: Circle) -> list[Point]:
        """Find intersection points with another circle (exact analytical solution)."""
        d = float(np.linalg.norm(self.center.coords - other.center.coords))
        r1, r2 = self.radius, other.radius
        if d > r1 + r2 or d < abs(r1 - r2) or d < 1e-14:
            return []
        a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
        h_sq = r1 * r1 - a * a
        h = math.sqrt(max(h_sq, 0.0))
        direction = (other.center.coords - self.center.coords) / d
        mid = self.center.coords + a * direction
        perp = np.array([-direction[1], direction[0]])
        if h < 1e-14:
            return [Point(*mid)]
        return [Point(*(mid + h * perp)), Point(*(mid - h * perp))]


def _intersect_linear_linear(
    p1: np.ndarray,
    p2: np.ndarray,
    a: Segment | Ray | Line,
    b: Segment | Ray | Line,
    check1: bool,
    check2: bool,
) -> list[Point]:
    """Find the intersection point between two linear objects using Shapely."""
    far = 1e9

    def _to_shapely(obj: Segment | Ray | Line) -> _sg.LineString:
        if isinstance(obj, Segment):
            return _sg.LineString([(obj.p1.x, obj.p1.y), (obj.p2.x, obj.p2.y)])
        elif isinstance(obj, Ray):
            end = obj.origin.coords + far * obj.unit_direction
            return _sg.LineString([(obj.origin.x, obj.origin.y), (end[0], end[1])])
        else:  # Line
            start = obj.point.coords - far * obj.unit_direction
            end = obj.point.coords + far * obj.unit_direction
            return _sg.LineString([(start[0], start[1]), (end[0], end[1])])

    result = _to_shapely(a).intersection(_to_shapely(b))
    if result.is_empty or result.geom_type != "Point":
        return []
    pt = Point(result.x, result.y)
    if (check1 and not a.contains_point(pt)) or (check2 and not b.contains_point(pt)):
        return []
    return [pt]


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

    def point_at_length(self, arc_length: float) -> Point:
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

    def point_perpendicular(self, distance_to_obj: float, t: float) -> Point:
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

    def contains_point(self, point: Point, tolerance: float = 0.01) -> bool:
        """Check whether a point lies on the curve within a given tolerance.

        Mirrors ``Segment.contains_point()`` / ``Ray.contains_point()`` /
        ``Line.contains_point()`` for API consistency.

        Uses Shapely's GEOS ``LineString.distance()`` on a 64-segment
        discretisation of the curve — a single C-level call that is
        significantly faster than the previous 200-point Python scan with
        binary search, while being accurate to well under 0.01 mm for typical
        garment curves.

        Args:
            point: The point to test.
            tolerance: Maximum Euclidean distance (mm) allowed for the point
                to be considered on the curve. Defaults to 0.01 mm.

        Returns:
            True if the closest point on the curve is within *tolerance* of
            *point*, False otherwise.
        """
        ls = _bezier_shapely(self)  # 64-segment discretisation
        return ls.distance(_sg.Point(point.x, point.y)) <= tolerance

    def offset(
        self,
        distance: float,
        center: Point | None = None,
        hausdorff_limit: float = 1.5,
    ) -> CubicBezier:
        """Return an approximate offset (parallel) curve shifted by *distance*.

        The offset is constructed by independently moving each of the four
        control points in the outward normal direction at its corresponding
        curve parameter (t = 0, 1/3, 2/3, 1 for p0 … p3).  This is the
        *hodograph approximation* and is accurate to sub-millimetre precision
        for seam allowances ≤ 2 cm on typical garment curves.

        **Quality check:** After computing the approximation, the Hausdorff
        distance between the original and offset polylines (64 segments each)
        is measured via GEOS.  If it exceeds ``hausdorff_limit × |distance|``
        the curve is split at t = 0.5, each half is offset independently, and
        the two results are re-joined into a single ``CubicBezier``.  This
        makes the method self-correcting for tight curvatures such as armscye
        or crotch curves without any manual intervention.

        The offset direction is chosen so that the result moves *away* from
        *center* (outward from the pattern piece interior).  If *center* is
        ``None`` the sign of *distance* controls the direction directly:
        positive = left of travel direction, negative = right.

        Args:
            distance: Offset in mm.  When *center* is provided the absolute
                value is used and direction is derived from *center*.
            center: Interior reference point (e.g. ``PatternPart.centroid``).
            hausdorff_limit: Multiplier applied to ``|distance|`` to form the
                error threshold.  Approximations whose Hausdorff distance
                exceeds ``hausdorff_limit × |distance|`` trigger the split
                fallback.  Defaults to ``1.5``.  Set to ``math.inf`` to
                disable the quality check entirely.

        Returns:
            A new ``CubicBezier`` approximating the offset curve.
        """
        # Resolve signed scalar offset distance
        if center is not None:
            mid = self.point_at_t(0.5)
            n_mid = self.normal_at_t(0.5)
            sign = 1.0 if np.dot(n_mid, mid.coords - center.coords) >= 0 else -1.0
            d = sign * abs(distance)
        else:
            d = distance

        def _hodograph(curve: CubicBezier) -> CubicBezier:
            """Shift each control point by the curve normal at its parameter."""

            def _shifted(pt: Point, t: float) -> Point:
                n = curve.normal_at_t(t)
                return Point(pt.x + d * n[0], pt.y + d * n[1])

            return CubicBezier(
                _shifted(curve.p0, 0.0),
                _shifted(curve.p1, 1 / 3),
                _shifted(curve.p2, 2 / 3),
                _shifted(curve.p3, 1.0),
                name=curve.name,
            )

        approx = _hodograph(self)

        # Hausdorff quality check — compare the hodograph approximation against
        # the true parallel offset (sampled point-by-point) rather than against
        # the original curve.  Comparing against the original always yields ≈
        # distance and never triggers the fallback.
        if abs(distance) > 1e-9 and math.isfinite(hausdorff_limit):
            ls_true = _true_offset_ls(self, d)
            ls_off = _bezier_shapely(approx)
            if ls_true.hausdorff_distance(ls_off) > hausdorff_limit * abs(distance):
                # Split at midpoint and offset each half independently, then
                # re-join: use the inner control points (p2 from the left half,
                # p1 from the right half) which encode the geometry near the
                # split point and produce a much better mid-curve approximation
                # than the outer tangent-only control points.
                left, right = self.split(0.5)
                left_off = _hodograph(left)
                right_off = _hodograph(right)
                return CubicBezier(
                    left_off.p0,
                    left_off.p2,
                    right_off.p1,
                    right_off.p3,
                    name=self.name,
                )

        return approx

    def offset_error(self, distance: float, center: Point | None = None) -> float:
        """Return the Hausdorff distance between the hodograph approximation and
        the true parallel offset of this curve.

        This is a quality metric for :meth:`offset`: it measures how far the
        hodograph approximation deviates from the true parallel curve.  A value
        well below *distance* indicates a reliable approximation; a value above
        ``1.5 × distance`` means the curve is too tightly curved for the
        approximation to be trustworthy.

        The *true* parallel offset is sampled point-by-point (64 perpendicular
        steps along the curve) and compared to the hodograph approximation via
        GEOS ``hausdorff_distance()``.

        Args:
            distance: The intended offset distance in mm.
            center: Interior reference point, forwarded to :meth:`offset` so
                that the direction is determined consistently.

        Returns:
            Hausdorff distance in mm between the true parallel offset and the
            hodograph approximation.

        Example::

            err = curve.offset_error(10.0)
            if err > 1.5 * 10.0:
                left, right = curve.split(0.5)
                sa = [left.offset(10.0), right.offset(10.0)]
            else:
                sa = [curve.offset(10.0)]
        """
        if center is not None:
            mid = self.point_at_t(0.5)
            n_mid = self.normal_at_t(0.5)
            sign = 1.0 if np.dot(n_mid, mid.coords - center.coords) >= 0 else -1.0
            d = sign * abs(distance)
        else:
            d = distance
        approx = self.offset(distance, center=center, hausdorff_limit=math.inf)
        ls_true = _true_offset_ls(self, d)
        ls_off = _bezier_shapely(approx)
        return float(ls_true.hausdorff_distance(ls_off))


def _intersect_bezier_bezier(
    a: CubicBezier, b: CubicBezier, tol: float = 1e-12
) -> list[Point]:
    """Find intersections between two cubic Bézier curves.

    Uses ``svgpathtools`` as a backend, which implements the numerically robust
    Bézier-clipping algorithm (Sederberg & Nishita 1990).
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


def _bezier_shapely(b: CubicBezier, n: int = 64) -> _sg.LineString:
    """Discretise a CubicBezier into a Shapely LineString with *n* segments."""
    return _sg.LineString(
        [(b.point_at_t(i / n).x, b.point_at_t(i / n).y) for i in range(n + 1)]
    )


def _true_offset_ls(b: CubicBezier, d: float, n: int = 64) -> _sg.LineString:
    """Return the true parallel offset of *b* at signed distance *d* as a
    Shapely LineString.

    Each of the *n+1* sample points is shifted perpendicularly by *d* along
    the curve normal at that parameter value.  This is the ground-truth
    reference used by :meth:`CubicBezier.offset_error` and the Hausdorff
    quality check in :meth:`CubicBezier.offset`.
    """
    pts = []
    for i in range(n + 1):
        t = i / n
        pt = b.point_at_t(t)
        nor = b.normal_at_t(t)
        pts.append((pt.x + d * nor[0], pt.y + d * nor[1]))
    return _sg.LineString(pts)


def _linear_shapely(obj: Segment | Ray | Line, far: float = 1e9) -> _sg.LineString:
    """Convert a Segment, Ray or Line to a Shapely LineString."""
    if isinstance(obj, Segment):
        return _sg.LineString([(obj.p1.x, obj.p1.y), (obj.p2.x, obj.p2.y)])
    elif isinstance(obj, Ray):
        end = obj.origin.coords + far * obj.unit_direction
        return _sg.LineString([(obj.origin.x, obj.origin.y), (end[0], end[1])])
    else:  # Line
        start = obj.point.coords - far * obj.unit_direction
        end = obj.point.coords + far * obj.unit_direction
        return _sg.LineString([(start[0], start[1]), (end[0], end[1])])


def _shapely_to_points(result: _sg.base.BaseGeometry) -> list[Point]:
    """Extract a list of Points from a Shapely intersection result."""
    if result.is_empty:
        return []
    if result.geom_type == "Point":
        return [Point(result.x, result.y)]
    if result.geom_type in ("MultiPoint", "GeometryCollection"):
        return [Point(g.x, g.y) for g in result.geoms if g.geom_type == "Point"]
    return []


GEOMETRIC_TYPE = (
    Point | Line | Ray | Circle | Segment | Rect | Triangle | InfoBox | CubicBezier
)


def intersect(a: GEOMETRIC_TYPE, b: GEOMETRIC_TYPE) -> list[Point]:
    """Find intersections between two geometric objects.

    Linear objects (Segment, Ray, Line) and circles are handled via Shapely's
    GEOS backend.  Bézier–Bézier intersections use svgpathtools (Bézier-clipping).
    Bézier–linear and Bézier–circle intersections discretise the curve and use
    Shapely.

    Returns:
        list[Point]: Intersection points, or empty list if none.
    """
    # ── linear × linear ──────────────────────────────────────────────────────
    if isinstance(a, (Segment, Ray, Line)) and isinstance(b, (Segment, Ray, Line)):
        return _intersect_linear_linear(
            None, None, a, b, isinstance(a, Segment), isinstance(b, Segment)
        )

    # ── linear × circle ──────────────────────────────────────────────────────
    if isinstance(a, (Segment, Ray, Line)) and isinstance(b, Circle):
        circle_shape = _sg.Point(b.center.x, b.center.y).buffer(b.radius)
        result = _linear_shapely(a).intersection(circle_shape.exterior)
        return _shapely_to_points(result)

    if isinstance(a, Circle) and isinstance(b, (Segment, Ray, Line)):
        return intersect(b, a)

    # ── circle × circle ──────────────────────────────────────────────────────
    if isinstance(a, Circle) and isinstance(b, Circle):
        return a._intersect_with_circle(b)

    # ── Bézier × Bézier ──────────────────────────────────────────────────────
    if isinstance(a, CubicBezier) and isinstance(b, CubicBezier):
        return _intersect_bezier_bezier(a, b)

    # ── Bézier × linear ──────────────────────────────────────────────────────
    if isinstance(a, CubicBezier) and isinstance(b, (Segment, Ray, Line)):
        result = _bezier_shapely(a).intersection(_linear_shapely(b))
        return _shapely_to_points(result)

    if isinstance(a, (Segment, Ray, Line)) and isinstance(b, CubicBezier):
        return intersect(b, a)

    # ── Bézier × circle ──────────────────────────────────────────────────────
    if isinstance(a, CubicBezier) and isinstance(b, Circle):
        circle_shape = _sg.Point(b.center.x, b.center.y).buffer(b.radius)
        result = _bezier_shapely(a).intersection(circle_shape.exterior)
        return _shapely_to_points(result)

    if isinstance(a, Circle) and isinstance(b, CubicBezier):
        return intersect(b, a)

    raise TypeError(f"Intersection not implemented for {type(a)} and {type(b)}")


def segment_to_intersection(
    start: Point, dir: np.ndarray, obj: GEOMETRIC_TYPE
) -> tuple[Point, Segment]:
    """Create a Segment from start to the first intersection with obj in direction dir."""
    pt = intersect(Ray(start, dir), obj)[0]
    return pt, Segment(start, pt)


# ---------------------------------------------------------------------------
# Chain / offset helpers  (used by PatternPart.add_seam_allowance)
# ---------------------------------------------------------------------------

_CHAIN_SNAP = 0.5  # mm — endpoint-matching tolerance


def geom_start(g: Segment | CubicBezier) -> Point:
    """Return the start point of a Segment or CubicBezier."""
    return g.p1 if isinstance(g, Segment) else g.p0


def geom_end(g: Segment | CubicBezier) -> Point:
    """Return the end point of a Segment or CubicBezier."""
    return g.p2 if isinstance(g, Segment) else g.p3


def with_endpoints(
    g: Segment | CubicBezier, new_start: Point, new_end: Point
) -> Segment | CubicBezier:
    """Return a copy of *g* with replaced start and end points."""
    if isinstance(g, Segment):
        return Segment(new_start, new_end, name=g.name)
    return CubicBezier(new_start, g.p1, g.p2, new_end, name=g.name)


def build_chain(
    geoms: list[Segment | CubicBezier],
) -> list[Segment | CubicBezier]:
    """Sort *geoms* into a single connected chain, reversing pieces as needed.

    Walks through *geoms* greedily: the next piece whose start or end lies
    within ``_CHAIN_SNAP`` mm of the current tail is appended (reversed if
    necessary).  Any unconnected remainder is appended as-is.
    """
    chain = [geoms[0]]
    remaining = list(geoms[1:])
    while remaining:
        tail = geom_end(chain[-1])
        for i, g in enumerate(remaining):
            if tail.distance_to(geom_start(g)) < _CHAIN_SNAP:
                chain.append(remaining.pop(i))
                break
            elif tail.distance_to(geom_end(g)) < _CHAIN_SNAP:
                rev: Segment | CubicBezier = (
                    Segment(g.p2, g.p1, name=g.name)
                    if isinstance(g, Segment)
                    else CubicBezier(g.p3, g.p2, g.p1, g.p0, name=g.name)
                )
                chain.append(rev)
                remaining.pop(i)
                break
        else:
            chain.extend(remaining)  # gap — append remainder as-is
            break
    return chain


def miter_corner(
    ga: Segment | CubicBezier,
    gb: Segment | CubicBezier,
    sa_distance: float,
    miter_limit: float = 4.0,
) -> Point:
    """Return the miter-join corner between the end of *ga* and the start of *gb*.

    Extends the end-tangent of *ga* and the start-tangent of *gb* as infinite
    lines and returns their intersection.  Falls back to the bevel midpoint
    when:

    * the lines are parallel,
    * the miter extension exceeds *miter_limit* × *sa_distance*, or
    * the corner is a **reflex** angle (interior angle > 180°, i.e. a
      concave corner on the offset curve).  For reflex corners the miter
      intersection would shoot inward and create a spike; using the bevel
      midpoint keeps the offset curve well-behaved.
    """

    def _unit_tangent(g: Segment | CubicBezier, at_end: bool) -> np.ndarray:
        d = (
            g.p2.coords - g.p1.coords
            if isinstance(g, Segment)
            else (g.tangent_at_t(1.0) if at_end else g.tangent_at_t(0.0))
        )
        norm = float(np.linalg.norm(d))
        return d / norm if norm > 1e-12 else d

    end_a = geom_end(ga)
    start_b = geom_start(gb)
    ta = _unit_tangent(ga, at_end=True)
    tb = _unit_tangent(gb, at_end=False)

    bevel_mid = Point(*(0.5 * (end_a.coords + start_b.coords)))

    pt = _intersect_lines(
        end_a.coords,
        np.array([-ta[1], ta[0]]),
        start_b.coords,
        np.array([-tb[1], tb[0]]),
    )
    if pt is None:
        return bevel_mid

    # Reflex-corner detection: if the intersection point lies *behind* the
    # end of ga (i.e. in the opposite direction of ta) the corner is concave
    # on the offset curve and the miter would punch inward, creating a spike.
    # This check is winding-direction-independent: dot(pt - end_a, ta) < 0
    # is true for reflex corners regardless of whether the outline is CW or CCW.
    if float(np.dot(pt - end_a.coords, ta)) < 0.0:
        return bevel_mid

    if (
        sa_distance > 1e-9
        and float(np.linalg.norm(pt - end_a.coords)) > miter_limit * sa_distance
    ):
        return bevel_mid
    return Point(*pt)


def round_corner(
    ga: "Segment | CubicBezier",
    gb: "Segment | CubicBezier",
) -> "CubicBezier | Point":
    """Return a cubic Bézier arc approximation for a round join at a convex corner.

    Constructs a cubic Bézier that approximates the circular arc connecting
    ``geom_end(ga)`` to ``geom_start(gb)`` around the outside of the corner.
    The arc centre is the intersection of the outward normals at the two
    endpoints (i.e. the miter point).  Handle lengths follow the standard
    **k = (4/3) tan(θ/4)** formula, giving a maximum radial error < 0.027 %
    of the arc radius for included angles up to 90°.

    Falls back to the bevel midpoint (as a :class:`Point`) for:

    * parallel or anti-parallel tangents (degenerate corner),
    * reflex (concave) corners where the arc would curve inward,
    * degenerate geometry (zero chord, zero radius, …).

    Args:
        ga: The outgoing offset element whose *end* point is the arc start.
        gb: The incoming offset element whose *start* point is the arc end.

    Returns:
        A :class:`CubicBezier` arc, or a :class:`Point` bevel midpoint
        fallback.
    """

    def _unit_tangent(g: "Segment | CubicBezier", at_end: bool) -> np.ndarray:
        d = (
            g.p2.coords - g.p1.coords  # type: ignore[union-attr]
            if isinstance(g, Segment)
            else (g.tangent_at_t(1.0) if at_end else g.tangent_at_t(0.0))
        )
        norm = float(np.linalg.norm(d))
        return d / norm if norm > 1e-12 else d

    end_a = geom_end(ga)
    start_b = geom_start(gb)
    bevel_mid = Point(*(0.5 * (end_a.coords + start_b.coords)))

    ta = _unit_tangent(ga, at_end=True)
    tb = _unit_tangent(gb, at_end=False)

    # Signed angle from ta to tb.  Positive → left turn (convex outward arc).
    cross = float(ta[0] * tb[1] - ta[1] * tb[0])
    dot_ = float(ta[0] * tb[0] + ta[1] * tb[1])
    angle = math.atan2(cross, dot_)  # in (-π, π]

    # Only produce an arc for convex corners (positive included angle ≤ π).
    if angle <= 1e-6 or angle > math.pi - 1e-6:
        return bevel_mid

    # Arc centre: intersection of the outward normals at end_a and start_b.
    # For a clockwise-wound offset curve (SVG y-down) the outward normal is
    # the *right-hand* perpendicular of the tangent: (ta[1], -ta[0]).
    na = np.array([ta[1], -ta[0]])
    nb = np.array([tb[1], -tb[0]])
    centre_pt = _intersect_lines(
        end_a.coords,
        na,
        start_b.coords,
        nb,
    )
    if centre_pt is None:
        return bevel_mid

    # Verify the arc centre is on the correct (outside) side of the corner.
    if float(np.dot(centre_pt - end_a.coords, na)) < 0.0:
        return bevel_mid

    r = float(np.linalg.norm(centre_pt - end_a.coords))
    if r < 1e-9:
        return bevel_mid

    # Verify start_b is also on the circle (sanity check).
    r2 = float(np.linalg.norm(centre_pt - start_b.coords))
    if abs(r2 - r) > r * 0.01:  # > 1 % discrepancy → degenerate
        return bevel_mid

    # k = (4/3) * tan(angle/4) → handle length = k * r (tangential, standard formula).
    k = (4.0 / 3.0) * math.tan(angle / 4.0)
    handle = k * r

    # Control points along the tangent directions at each endpoint.
    cp1 = Point(*(end_a.coords + handle * ta))
    cp2 = Point(*(start_b.coords - handle * tb))

    return CubicBezier(end_a, cp1, cp2, start_b)


def buffer_chain(
    geoms: list[Segment | CubicBezier],
    distance: float,
    join_style: int = 2,
    mitre_limit: float = 4.0,
) -> list[tuple[float, float]]:
    """Buffer a connected chain of Segments outward by *distance* using Shapely.

    Builds a Shapely Polygon from the chain, applies ``Polygon.buffer()``,
    and returns the exterior ring as a list of (x, y) coordinate tuples.
    Only valid for pure-segment chains; call ``build_chain`` first.

    Args:
        geoms: Connected chain of Segments (no CubicBeziers).
        distance: Offset distance in mm (must be positive).
        join_style: Shapely join style (2 = Miter, 1 = Round, 3 = Bevel).
        mitre_limit: Maximum miter ratio before fallback to bevel.

    Returns:
        List of (x, y) coordinate tuples forming the buffered exterior ring.
    """
    ring_coords = [(g.p1.x, g.p1.y) for g in geoms]  # type: ignore[union-attr]
    poly = _sg.Polygon(ring_coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return list(
        poly.buffer(
            distance, join_style=join_style, mitre_limit=mitre_limit
        ).exterior.coords
    )


def outline_polygon(
    geoms: list[Segment | CubicBezier],
    bezier_samples: int = 32,
) -> _sg.Polygon | None:
    """Build a Shapely Polygon from a list of Segments and CubicBeziers.

    Segments contribute their start point; CubicBeziers are discretised into
    *bezier_samples* evenly spaced points.  Returns ``None`` if fewer than 3
    vertices are produced.
    """
    coords: list[tuple[float, float]] = []
    for g in geoms:
        if isinstance(g, Segment):
            coords.append((g.p1.x, g.p1.y))
        else:
            for i in range(bezier_samples):
                pt = g.point_at_t(i / bezier_samples)
                coords.append((pt.x, pt.y))
    if len(coords) < 3:
        return None
    return _sg.Polygon(coords)


def seam_length(geoms: list[Segment | CubicBezier]) -> float:
    """Return the total arc length of a list of Segments and/or CubicBeziers.

    Each element contributes its exact arc length:

    * ``Segment`` — Euclidean distance between its two endpoints.
    * ``CubicBezier`` — Gauss-Legendre quadrature via ``svgpathtools``
      (the same method used internally by ``CubicBezier.length()``).

    Typical use: compare a seam edge on the front piece against the
    matching seam edge on the back piece before finalising a pattern.

    Args:
        geoms: Any mix of ``Segment`` and ``CubicBezier`` objects that
            together form one seam edge.  The elements do not need to be
            connected or sorted.

    Returns:
        Total arc length in mm.

    Example::

        front_inseam = [front_inner_leg]          # CubicBezier
        back_inseam  = [back_inner_seam]          # CubicBezier
        diff = seam_length(front_inseam) - seam_length(back_inseam)
        print(f"inseam difference: {diff:.1f} mm")
    """
    total = 0.0
    for g in geoms:
        if isinstance(g, Segment):
            total += g.length
        else:
            total += g.length()
    return total
