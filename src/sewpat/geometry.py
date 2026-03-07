"""2D geometry primitives for sewing pattern generation."""

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import shapely.geometry as _sg
from svgpathtools import CubicBezier as _SvgCubicBezier


class DartType(StrEnum):
    """Shape variant of a :class:`Dart`.

    ``str`` mixin allows comparing with plain strings for backward compatibility
    (e.g. ``dart.dart_type == "triangle"`` still works).

    Attributes:
        TRIANGLE: Seam-edge dart — rendered as two stitch lines + fold line.
        RHOMBUS:  Inner-panel dart — rendered as a closed four-point diamond.
    """

    TRIANGLE = "triangle"
    RHOMBUS = "rhombus"


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


def _bezier_closest_t(svg_bezier: _SvgCubicBezier, pt_c: complex) -> float:
    """Return *t* ∈ [0, 1] of the point on *svg_bezier* closest to *pt_c*."""
    return svg_bezier.radialrange(pt_c)[0][1]


@dataclass(frozen=True)
class Point:
    """A 2D point (frozen dataclass). Coordinates stored as a NumPy array."""

    coords: np.ndarray
    name: str | None = None

    def __init__(self, x: float, y: float, name: str | None = None) -> None:
        object.__setattr__(self, "coords", np.array([x, y], dtype=float))
        object.__setattr__(self, "name", name)

    @property
    def x(self) -> float:
        """X coordinate."""
        return float(self.coords[0])

    @property
    def y(self) -> float:
        """Y coordinate."""
        return float(self.coords[1])

    def __str__(self) -> str:
        if self.name:
            return (
                f"Point(name={self.name}, "
                f"x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"
            )
        else:
            return f"Point(x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"

    def distance_to(self, other: Point | np.ndarray) -> float:
        """Calculate the Euclidean distance between this point and another."""
        if isinstance(other, Point):
            return float(np.linalg.norm(self.coords - other.coords))
        else:
            return float(np.linalg.norm(self.coords - other))

    def distance_to_segment(self, seg: Segment) -> float:
        """Return the shortest distance from this point to *seg*.

        If the perpendicular foot lies within the segment the result is the
        perpendicular distance; otherwise it is the distance to the nearer
        endpoint.
        """
        p1 = seg.p1.coords
        d  = seg.p2.coords - p1
        t  = float(np.dot(self.coords - p1, d) / np.dot(d, d))
        foot = Point(*(p1 + max(0.0, min(1.0, t)) * d))
        return self.distance_to(foot)

    def translate(self, dx: float, dy: float) -> Point:
        """Return a copy translated by (dx, dy)."""
        return self + Point(dx, dy)

    def __add__(self, other: Point) -> Point:
        """Offset by *other* as a displacement vector. Returns a new Point."""
        if not isinstance(other, Point):
            return NotImplemented
        return Point(*(self.coords + other.coords))

    def __sub__(self, other: Point) -> Point:
        """Return the difference as a new Point (vector from *other* to *self*)."""
        if not isinstance(other, Point):
            return NotImplemented
        return Point(*(self.coords - other.coords))

    def __mul__(self, scalar: float) -> Point:
        """Scale the position vector by *scalar*."""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Point(*(self.coords * scalar))

    def __rmul__(self, scalar: float) -> Point:
        """Scale the position vector by *scalar* (reflected)."""
        return self.__mul__(scalar)

    def __neg__(self) -> Point:
        """Return the negated point (-x, -y)."""
        return Point(*(-self.coords))

    def __eq__(self, other: object) -> bool:
        """Scalar equality: True when both coordinates and name match exactly."""
        if not isinstance(other, Point):
            return NotImplemented
        return (
            bool(np.array_equal(self.coords, other.coords)) and self.name == other.name
        )

    def __hash__(self) -> int:
        return hash(
            (
                round(float(self.coords[0]), 9),
                round(float(self.coords[1]), 9),
                self.name,
            )
        )

    def rotate(self, center: Point, angle_rad: float) -> Point:
        """Return a copy rotated by *angle_rad* around *center* (counter-clockwise)."""
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        rot = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
        return Point(*(rot @ (self.coords - center.coords) + center.coords))

    def move_towards(
        self,
        curve: Segment | CubicBezier | Ray | Line | Circle,
        arc_length: float,
    ) -> Point:
        """Return the point *arc_length* mm from ``self`` along *curve*.

        ``self`` must lie on *curve*.  Positive *arc_length* follows the
        curve's natural direction; negative moves against it.  Delegates to
        ``curve.point_along_from(self, arc_length)``.

        Raises:
            TypeError: If *curve* is not a supported type.
            ValueError: If the result falls outside a finite curve's bounds.
        """
        if not hasattr(curve, "point_along_from"):
            raise TypeError(
                f"move_towards does not support curve type {type(curve).__name__!r}. "
                "Expected Segment, CubicBezier, Ray, Line, or Circle."
            )
        return curve.point_along_from(self, arc_length)


class Segment:
    """A line segment from p1 to p2."""

    def __init__(self, p1: Point, p2: Point, name: str | None = None) -> None:
        self.p1 = p1
        self.p2 = p2
        self.name = name

    @classmethod
    def from_direction(
        cls,
        start: Point,
        through: Point,
        length: float,
        name: str | None = None,
    ) -> Segment:
        """Create a segment starting at *start*, pointing towards *through*,
        with given *length*.

        The direction is determined by the vector from *start* to *through*;
        the actual distance between them does not matter.

        Args:
            start:   Origin of the new segment.
            through: Any point that defines the direction (need not be the endpoint).
            length:  Desired length of the resulting segment in mm.
            name:    Optional label.

        Returns:
            A :class:`Segment` of exactly *length* mm from *start* in the
            direction of *through*.

        Raises:
            ValueError: If *start* and *through* are the same point.

        Example::

            # Shoulder seam 13 cm long, starting at pt_neck towards pt_arm
            seg_shoulder = Segment.from_direction(pt_neck, pt_arm, 13 * CM)
        """
        d = through.coords - start.coords
        norm = float(np.linalg.norm(d))
        if norm == 0.0:
            raise ValueError("'start' and 'through' must be different points.")
        end_coords = start.coords + (d / norm) * length
        return cls(start, Point(*end_coords), name=name)

    def __str__(self) -> str:
        if self.name:
            return f"Segment(name={self.name}; p1={self.p1}, p2={self.p2})"
        else:
            return f"Segment(p1={self.p1}, p2={self.p2})"

    def __repr__(self) -> str:
        return self.__str__()

    def set_name(self, name: str) -> Segment:
        """Set the name of this segment and return ``self`` for fluent chaining."""
        self.name = name
        return self

    def translate(self, dx: float, dy: float) -> Segment:
        """Return a copy translated by (dx, dy)."""
        return Segment(
            self.p1.translate(dx, dy), self.p2.translate(dx, dy), name=self.name
        )

    @property
    def start(self) -> Point:
        """Start point of the segment (alias for p1)."""
        return self.p1

    @property
    def end(self) -> Point:
        """End point of the segment (alias for p2)."""
        return self.p2

    @property
    def length(self) -> float:
        """Euclidean length."""
        return self.p1.distance_to(self.p2)

    @property
    def direction_unnormalized(self) -> np.ndarray:
        """Direction vector (not normalised)."""
        return self.p2.coords - self.p1.coords

    @property
    def unit_direction(self) -> np.ndarray:
        """Normalised direction vector."""
        d = self.p2.coords - self.p1.coords
        return d / np.linalg.norm(d)

    @property
    def unit_normal(self) -> np.ndarray:
        """Unit normal (left-hand perpendicular of the direction vector)."""
        d = self.unit_direction
        return np.array([-d[1], d[0]])

    @property
    def midpoint(self) -> Point:
        """Midpoint of the segment."""
        return (self.p1 + self.p2) * 0.5

    def point_at_t(self, t: float) -> Point:
        """Return the point at parameter *t* ∈ [0, 1] (0 = p1, 1 = p2)."""
        if not (0 <= t <= 1):
            raise ValueError(f"{t = } expected in [0, 1]")
        return self.p1 * (1.0 - t) + self.p2 * t

    def split(self, t: float) -> tuple[Segment, Segment]:
        """Split at parameter *t* ∈ (0, 1) and return ``(left, right)``.

        Mirrors :meth:`CubicBezier.split` so both geometry types share the
        same split interface.

        Args:
            t: Split parameter in the open interval (0, 1).

        Returns:
            A pair ``(Segment(p1, mid), Segment(mid, p2))`` where
            ``mid = point_at_t(t)``.
        """
        if not (0.0 < t < 1.0):
            raise ValueError(f"t must be in (0, 1), got {t}")
        mid = self.point_at_t(t)
        return Segment(self.p1, mid, name=self.name), Segment(
            mid, self.p2, name=self.name
        )

    def split_at_points(
        self,
        points: list[Point],
        tolerance: float = 0.5,
    ) -> list[Segment]:
        """Split at a list of points that lie on this segment.

        Each point is projected onto the segment's axis using
        :attr:`unit_direction` and :attr:`length` to obtain its arc-length
        parameter *t ∈ [0, 1]*.  The points are then sorted by *t* before
        splitting, so their order in *points* does not matter.  Points within
        *tolerance* mm of either endpoint are silently dropped (they would
        produce a degenerate zero-length stub).

        The method delegates each individual split to :meth:`split`, so the
        two methods share the same underlying arithmetic.

        Args:
            points: List of :class:`Point` objects lying on the segment.
            tolerance: Minimum distance from an endpoint (in mm) for a split
                point to be kept.  Defaults to 0.5 mm.

        Returns:
            List of :class:`Segment` sub-segments in p1→p2 order.  Returns a
            single-element list containing the original segment when all points
            fall within *tolerance* of the endpoints.
        """
        total_len = self.length
        if total_len == 0.0:
            return [Segment(self.p1, self.p2, name=self.name)]

        # Project each point onto [0, 1] using already-available helpers:
        # arc-length from p1 = dot(pt - p1, unit_direction), then divide by length.
        eps = tolerance / total_len
        ts: list[float] = sorted(
            float(np.dot(pt.coords - self.p1.coords, self.unit_direction)) / total_len
            for pt in points
        )
        breakpoints: list[float] = [t for t in ts if eps < t < 1.0 - eps]

        if not breakpoints:
            return [Segment(self.p1, self.p2, name=self.name)]

        # Walk through breakpoints, splitting the remaining tail each time.
        # Re-use split() so there is a single source of truth for the arithmetic.
        tail: Segment = Segment(self.p1, self.p2, name=self.name)
        sub_segments: list[Segment] = []
        consumed: float = 0.0  # fraction of original length already cut off
        for t in breakpoints:
            local_t = (t - consumed) / (1.0 - consumed)
            head, tail = tail.split(local_t)
            sub_segments.append(head)
            consumed = t
        sub_segments.append(tail)
        return sub_segments

    def point_perpendicular(
        self,
        distance: float,
        arc_length: float | None = None,
        t: float | None = None,
    ) -> Point:
        """Return a point offset perpendicularly from the segment.

        Positive *distance* = left of travel direction (p1→p2), negative = right.
        Position is given by *t* (0–1) or *arc_length* (mm from p1);
        defaults to midpoint.

        Raises:
            ValueError: If both *arc_length* and *t* are given.
        """
        # ── Resolve position ─────────────────────────────────────────────────
        if arc_length is not None and t is not None:
            raise ValueError("Specify at most one of 'arc_length' and 't'.")
        if arc_length is not None:
            base = self.p1.coords + arc_length * self.unit_direction
        elif t is not None:
            if not (0.0 <= t <= 1.0):
                raise ValueError(f"t = {t} must be in [0, 1]")
            base = (1.0 - t) * self.p1.coords + t * self.p2.coords
        else:
            base = 0.5 * (self.p1.coords + self.p2.coords)

        return Point(*(base + self.unit_normal * distance))

    def project_point(self, point: Point) -> Point:
        """Return the orthogonal projection of *point* onto this segment's line."""
        p1 = self.p1.coords
        d = self.p2.coords - p1
        t = float(np.dot(point.coords - p1, d) / np.dot(d, d))
        return Point(*(p1 + t * d))

    def reflect_point(self, point: Point) -> Point:
        """Return the mirror image of *point* reflected across this segment's line."""
        foot = self.project_point(point)
        return foot * 2.0 - point

    def contains_point(self, point: Point, tolerance: float = 1e-9) -> bool:
        """Return True if *point* lies on the segment within *tolerance* mm
        (uses Shapely GEOS).
        """
        ls = _sg.LineString([(self.p1.x, self.p1.y), (self.p2.x, self.p2.y)])
        return ls.distance(_sg.Point(point.x, point.y)) <= tolerance

    def point_at_length(self, arc_length: float) -> Point:
        """Return the point at *arc_length* mm from p1.
        Raises ValueError if out of range.
        """
        total = self.length
        return self.point_at_t(arc_length / total)

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this segment from
        *point* (p1→p2 direction).
        """
        pos = float(np.dot(point.coords - self.p1.coords, self.unit_direction))
        return self.point_at_length(pos + arc_length)

    def bounding_box(self) -> tuple[Point, Point]:
        """Return the axis-aligned bounding box as ``(min_point, max_point)``."""
        min_x = min(self.p1.x, self.p2.x)
        min_y = min(self.p1.y, self.p2.y)
        max_x = max(self.p1.x, self.p2.x)
        max_y = max(self.p1.y, self.p2.y)
        return Point(min_x, min_y), Point(max_x, max_y)

    def offset(self, distance: float, center: Point | None = None) -> Segment:
        """Return a new Segment offset perpendicularly by *distance* mm.

        Direction is away from *center* (outward) when given; otherwise the
        sign of *distance* controls the direction (positive = left of travel).
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
        new_p1 = self.p1 + Point(*offset_vec)
        new_p2 = self.p2 + Point(*offset_vec)
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
    ) -> None:
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
            return (
                f"Ray(name={self.name}, origin={self.origin}, "
                f"direction={self.direction})"
            )
        else:
            return f"Ray(origin={self.origin}, direction={self.direction})"

    @property
    def unit_direction(self) -> np.ndarray:
        """Normalised direction vector."""
        return self.direction

    @property
    def unit_normal(self) -> np.ndarray:
        """Unit normal (left-hand perpendicular of the direction vector)."""
        dir_vec = self.direction
        return np.array([-dir_vec[1], dir_vec[0]])

    def point_at_distance(self, distance: float) -> Point:
        """Return the point at *distance* mm along the ray from the origin."""
        return Point(*(self.origin.coords + self.direction * distance))

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Return True if *point* lies on the ray within *tolerance*."""
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

    def point_perpendicular(self, distance: float, arc_length: float) -> Point:
        """Return a point offset perpendicularly by *distance* at *arc_length*
        along the ray.

        Positive *distance* = left of direction, negative = right.
        """
        base = self.origin.coords + arc_length * self.direction
        return Point(*(base + self.unit_normal * distance))

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this ray from *point*
        (away from origin).
        """
        pos = float(np.dot(point.coords - self.origin.coords, self.unit_direction))
        return self.point_at_distance(pos + arc_length)

    def translate(self, dx: float, dy: float) -> Ray:
        """Return a copy translated by (dx, dy)."""
        return Ray(self.origin.translate(dx, dy), self.direction, name=self.name)


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
    ) -> None:
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
            return (
                f"Line(name={self.name}, point={self.point}, "
                f"direction={self.direction})"
            )
        else:
            return f"Line(point={self.point}, direction={self.direction})"

    @property
    def unit_direction(self) -> np.ndarray:
        """Normalized direction vector of the line."""
        return self.direction

    @property
    def unit_normal(self) -> np.ndarray:
        """Unit normal (left-hand perpendicular of the direction vector)."""
        dir_vec = self.direction
        return np.array([-dir_vec[1], dir_vec[0]])

    def point_at_distance(self, distance: float) -> Point:
        """Return the point at *distance* mm along the line from the base point."""
        point_coords = self.point.coords + self.direction * distance
        return Point(*point_coords)

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Return True if *point* lies on the line within *tolerance*."""
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

    def point_perpendicular(self, distance: float, arc_length: float) -> Point:
        """Return a point offset perpendicularly by *distance* at *arc_length*
        along the line.

        Positive *distance* = left of direction, negative = right.
        """
        base = self.point.coords + arc_length * self.direction
        return Point(*(base + self.unit_normal * distance))

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this line from *point*
        (positive = line direction).
        """
        pos = float(np.dot(point.coords - self.point.coords, self.unit_direction))
        return self.point_at_distance(pos + arc_length)

    def translate(self, dx: float, dy: float) -> Line:
        """Return a copy translated by (dx, dy)."""
        return Line(self.point.translate(dx, dy), self.direction, name=self.name)


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
    ) -> None:
        self.origin = origin
        self.width = width
        self.height = height
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return (
                f"Rect(name={self.name}, origin={self.origin}, "
                f"width={self.width:.6g}, height={self.height:.6g})"
            )
        return (
            f"Rect(origin={self.origin}, "
            f"width={self.width:.6g}, height={self.height:.6g})"
        )

    def __repr__(self) -> str:
        return (
            f"Rect(origin={self.origin}, "
            f"width={self.width:.6g}, height={self.height:.6g})"
        )

    def translate(self, dx: float, dy: float) -> Rect:
        """Return a copy translated by (dx, dy)."""
        return Rect(
            self.origin.translate(dx, dy), self.width, self.height, name=self.name
        )

    def set_name(self, name: str) -> Rect:
        """Set the name of this rectangle and return ``self`` for fluent chaining."""
        self.name = name
        return self


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

    def __init__(
        self, p1: Point, p2: Point, p3: Point, name: str | None = None
    ) -> None:
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return (
                f"Triangle(name={self.name}, p1={self.p1}, p2={self.p2}, p3={self.p3})"
            )
        return f"Triangle(p1={self.p1}, p2={self.p2}, p3={self.p3})"

    def __repr__(self) -> str:
        return self.__str__()

    def translate(self, dx: float, dy: float) -> Triangle:
        """Return a copy translated by (dx, dy)."""
        return Triangle(
            self.p1.translate(dx, dy),
            self.p2.translate(dx, dy),
            self.p3.translate(dx, dy),
            name=self.name,
        )

    def set_name(self, name: str) -> Triangle:
        """Set the name of this triangle and return ``self`` for fluent chaining."""
        self.name = name
        return self


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
    ) -> None:
        self.position = position
        self.header = header
        self.notes: list[str] = notes if notes is not None else []
        self.name: str | None = None

    def __str__(self) -> str:
        return f"InfoBox(header={self.header!r}, position={self.position})"

    def __repr__(self) -> str:
        return self.__str__()

    def translate(self, dx: float, dy: float) -> InfoBox:
        """Return a copy translated by (dx, dy)."""
        moved = InfoBox(self.position.translate(dx, dy), self.header, list(self.notes))
        moved.name = self.name
        return moved


class Circle:
    """A circle defined by a center point and radius.

    Attributes:
        center: The center point of the circle.
        radius: The radius of the circle.
        name: Optional, name of the circle.
    """

    def __init__(self, center: Point, radius: float, name: str | None = None) -> None:
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
            return (
                f"Circle(name={self.name}, center={self.center}, "
                f"radius={self.radius:.6g})"
            )
        else:
            return f"Circle(center={self.center}, radius={self.radius:.6g})"

    @property
    def area(self) -> float:
        """Area of the circle."""
        return math.pi * self.radius * self.radius

    @property
    def diameter(self) -> float:
        """Diameter of the circle."""
        return 2 * self.radius

    @property
    def circumference(self) -> float:
        """Circumference of the circle."""
        return 2 * math.pi * self.radius

    def contains_point(self, point: Point, tolerance: float = 1e-14) -> bool:
        """Return True if *point* lies on the circle boundary within *tolerance*."""
        return abs(self.center.distance_to(point) - self.radius) < tolerance

    def contains_point_inside(
        self, point: Point, include_boundary: bool = True
    ) -> bool:
        """Return True if *point* is inside (or on) the circle."""
        d = self.center.distance_to(point)
        return d <= self.radius if include_boundary else d < self.radius

    def point_at_angle(self, angle_rad: float) -> Point:
        """Return the point on the circle at the given angle (radians, CCW from +x)."""
        return Point(
            *(
                self.center.coords
                + self.radius * np.array([math.cos(angle_rad), math.sin(angle_rad)])
            )
        )

    def translate(self, dx: float, dy: float) -> Circle:
        """Return a copy translated by (dx, dy)."""
        return Circle(self.center.translate(dx, dy), self.radius, name=self.name)

    def set_name(self, name: str) -> Circle:
        """Set the name of this circle and return ``self`` for fluent chaining."""
        self.name = name
        return self

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this circle from *point*
        (CCW positive).
        """
        angle0 = math.atan2(point.y - self.center.y, point.x - self.center.x)
        return self.point_at_angle(angle0 + arc_length / self.radius)

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
        mid_pt = Point(*mid)
        perp_pt = Point(*perp)
        return [mid_pt + perp_pt * h, mid_pt - perp_pt * h]


def _intersect_linear_linear(
    p1: np.ndarray | None,
    p2: np.ndarray | None,
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
    ) -> None:
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
        return (
            f"CubicBezier(name={self.name}, p0={self.p0}, p1={self.p1}, "
            f"p2={self.p2}, p3={self.p3})"
        )

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def start(self) -> Point:
        """Start point of the curve (alias for p0)."""
        return self.p0

    @property
    def end(self) -> Point:
        """End point of the curve (alias for p3)."""
        return self.p3

    def translate(self, dx: float, dy: float) -> CubicBezier:
        """Return a copy translated by (dx, dy)."""
        return CubicBezier(
            self.p0.translate(dx, dy),
            self.p1.translate(dx, dy),
            self.p2.translate(dx, dy),
            self.p3.translate(dx, dy),
            name=self.name,
        )

    def set_name(self, name: str) -> CubicBezier:
        """Set the name of this curve and return ``self`` for fluent chaining."""
        self.name = name
        return self

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

    @property
    def length(self) -> float:
        """Exact arc length via Gauss-Legendre quadrature
        (delegated to svgpathtools).
        """
        return self._svg().length()

    def tangent_at_t(self, t: float) -> np.ndarray:
        """Tangent vector at *t* (not normalised), via svgpathtools B'(t)."""
        d = self._svg().derivative(t)
        return np.array([d.real, d.imag])

    def normal_at_t(self, t: float) -> np.ndarray:
        """Unit normal at *t*: 90° counter-clockwise from the tangent (left of travel).

        Falls back to a nearby t when the tangent is degenerate at the exact
        endpoint (e.g. when cp2 == p3 or cp1 == p0).
        """
        svg = self._svg()
        try:
            n = svg.normal(t)
            return np.array([n.real, n.imag])
        except ValueError:
            # Degenerate endpoint — step slightly inward and retry.
            eps = 1e-4
            fallback_t = max(eps, t - eps) if t > 0.5 else min(1.0 - eps, t + eps)
            try:
                n = svg.normal(fallback_t)
                return np.array([n.real, n.imag])
            except ValueError:
                # Last resort: finite-difference tangent from point_at_t.
                dt = 1e-4
                t0 = max(0.0, t - dt)
                t1 = min(1.0, t + dt)
                p0 = self.point_at_t(t0)
                p1 = self.point_at_t(t1)
                dx, dy = p1.x - p0.x, p1.y - p0.y
                length = (dx**2 + dy**2) ** 0.5 or 1.0
                # Rotate 90° CCW: (dx, dy) → (-dy, dx)
                return np.array([-dy / length, dx / length])

    def point_at_length(self, arc_length: float) -> Point:
        """Return the point at *arc_length* mm from p0 (uses svgpathtools.ilength).
        Raises ValueError if out of range.
        """
        total = self.length
        if arc_length < 0 or arc_length > total + 1e-9:
            raise ValueError(f"arc_length {arc_length:.4f} is outside [0, {total:.4f}]")
        t = self._svg().ilength(arc_length)
        return self.point_at_t(t)

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this curve from *point*
        (p0→p3 direction).
        """
        svg = self._svg()
        t0 = _bezier_closest_t(svg, complex(point.x, point.y))
        pos = float(svg.length(t1=t0))
        return self.point_at_length(pos + arc_length)

    def split(self, t: float) -> tuple[CubicBezier, CubicBezier]:
        """Split at *t* into (left, right) using de Casteljau
        (delegated to svgpathtools).
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

    def split_at_points(
        self,
        points: list[Point],
        tolerance: float = 0.5,
    ) -> list[CubicBezier]:
        """Split at a list of points that lie on this curve.

        Each point is located on the curve via :func:`_bezier_closest_t` (the
        same helper used by :meth:`point_along_from`), giving its parameter
        *t ∈ [0, 1]*.  The points are sorted by *t* before splitting, so their
        order in *points* does not matter.  Points within *tolerance* mm of
        either endpoint are silently dropped to avoid degenerate zero-length
        sub-curves.

        Delegates each individual cut to :meth:`split`, keeping one source of
        truth for the de Casteljau arithmetic.

        Args:
            points: List of :class:`Point` objects lying on the curve.
            tolerance: Minimum distance from an endpoint (in mm) for a split
                point to be kept.  Defaults to 0.5 mm.

        Returns:
            List of :class:`CubicBezier` sub-curves in p0→p3 order.  Returns a
            single-element list containing the original curve when all points
            fall within *tolerance* of the endpoints.
        """
        total_len = self.length
        if total_len == 0.0:
            return [CubicBezier(self.p0, self.p1, self.p2, self.p3)]

        svg = self._svg()
        eps = tolerance / total_len

        ts: list[float] = sorted(
            _bezier_closest_t(svg, complex(pt.x, pt.y)) for pt in points
        )
        breakpoints: list[float] = [t for t in ts if eps < t < 1.0 - eps]

        if not breakpoints:
            return [CubicBezier(self.p0, self.p1, self.p2, self.p3)]

        # Walk through breakpoints re-using split(), converting each absolute t
        # into a local parameter on the remaining tail — same pattern as Segment.
        tail: CubicBezier = CubicBezier(self.p0, self.p1, self.p2, self.p3)
        sub_curves: list[CubicBezier] = []
        consumed: float = 0.0
        for t in breakpoints:
            local_t = (t - consumed) / (1.0 - consumed)
            head, tail = tail.split(local_t)
            sub_curves.append(head)
            consumed = t
        sub_curves.append(tail)
        return sub_curves

    def bounding_box(self) -> tuple[Point, Point]:
        """Compute the axis-aligned bounding box by finding B'(t)=0 extrema
        (not the control-point hull).
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

    def point_perpendicular(self, distance: float, t: float) -> Point:
        """Return a point offset by *distance* mm in the normal direction at *t*.

        Positive *distance* = left of travel direction, negative = right.
        """
        pt = self.point_at_t(t)
        nor = self.normal_at_t(t)
        return Point(pt.x + distance * nor[0], pt.y + distance * nor[1])

    def contains_point(self, point: Point, tolerance: float = 0.01) -> bool:
        """Return True if *point* is within *tolerance* mm of the curve
        (Shapely GEOS on 64-segment discretisation).
        """
        ls = _bezier_shapely(self)  # 64-segment discretisation
        return ls.distance(_sg.Point(point.x, point.y)) <= tolerance

    def offset(
        self,
        distance: float,
        center: Point | None = None,
        hausdorff_limit: float = 1.5,
    ) -> CubicBezier:
        """Return an approximate offset curve using the hodograph approximation.

        Direction is away from *center* when given; otherwise sign of *distance*
        controls direction (positive = left of travel).  If the Hausdorff error
        against the true parallel offset exceeds ``hausdorff_limit × |distance|``,
        the curve is split at t=0.5 and the halves are re-joined automatically.
        Set ``hausdorff_limit=math.inf`` to disable the quality check.
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
        """Return the Hausdorff distance (mm) between the hodograph approximation
        and the true parallel offset.

        Values well below *distance* indicate a reliable approximation;
        values above ``1.5 × distance`` suggest the curve is too tightly curved.
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

    def offset_adaptive(
        self,
        distance: float,
        center: Point | None = None,
        eps: float = 0.1,
        _depth: int = 0,
        _max_depth: int = 8,
    ) -> list[CubicBezier]:
        """Return the offset curve as a list of Béziers, recursively split
        until Hausdorff error < *eps* mm.

        Keeps splitting at t=0.5 until every sub-segment is within *eps* of the
        true parallel offset.  Hard depth cap of *_max_depth* (default 8 = up to
        256 segments) prevents infinite recursion on degenerate curves.
        """
        # Resolve signed distance (done once at top level; sub-calls pass
        # center=None with the already-signed distance to avoid re-deriving it).
        if center is not None:
            mid = self.point_at_t(0.5)
            n_mid = self.normal_at_t(0.5)
            sign = 1.0 if np.dot(n_mid, mid.coords - center.coords) >= 0 else -1.0
            d = sign * abs(distance)
        else:
            d = distance

        # Hodograph approximation for this segment.
        def _shifted(pt: Point, t: float) -> Point:
            n = self.normal_at_t(t)
            return Point(pt.x + d * n[0], pt.y + d * n[1])

        approx = CubicBezier(
            _shifted(self.p0, 0.0),
            _shifted(self.p1, 1 / 3),
            _shifted(self.p2, 2 / 3),
            _shifted(self.p3, 1.0),
            name=self.name,
        )

        # Base cases: depth limit or error within tolerance.
        if _depth >= _max_depth:
            return [approx]

        ls_true = _true_offset_ls(self, d)
        ls_off = _bezier_shapely(approx)
        if ls_true.hausdorff_distance(ls_off) <= eps:
            return [approx]

        # Error too large — split and recurse.
        left, right = self.split(0.5)
        return left.offset_adaptive(
            d, center=None, eps=eps, _depth=_depth + 1, _max_depth=_max_depth
        ) + right.offset_adaptive(
            d, center=None, eps=eps, _depth=_depth + 1, _max_depth=_max_depth
        )


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


def geom_to_shapely(g: Segment | CubicBezier) -> _sg.LineString:
    """Convert a Segment or CubicBezier to a Shapely LineString.

    Segments map to a 2-point LineString; CubicBeziers are discretised into
    64 segments (sufficient for sub-0.1 mm accuracy on typical garment curves).

    Useful for nearest-point queries via ``shapely.ops.nearest_points()``.
    """
    if isinstance(g, Segment):
        return _sg.LineString([(g.p1.x, g.p1.y), (g.p2.x, g.p2.y)])
    return _bezier_shapely(g)


def _true_offset_ls(b: CubicBezier, d: float, n: int = 64) -> _sg.LineString:
    """Sample the true parallel offset of *b* at signed distance *d*
    into a Shapely LineString.
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
    """Create a Segment from start to the first intersection with obj
    in direction dir.
    """
    pt = intersect(Ray(start, dir), obj)[0]
    return pt, Segment(start, pt)


# ---------------------------------------------------------------------------
# Chain / offset helpers  (used by PatternPart.add_seam_allowance)
# ---------------------------------------------------------------------------

_CHAIN_SNAP = 0.5  # mm — endpoint-matching tolerance


def geom_start(g: Segment | CubicBezier) -> Point:
    """Return the start point of a Segment or CubicBezier."""
    return g.start


def geom_end(g: Segment | CubicBezier) -> Point:
    """Return the end point of a Segment or CubicBezier."""
    return g.end


def edge_tangent(g: Segment | CubicBezier, at_end: bool) -> np.ndarray:
    """Unit tangent of *g* in the direction of travel at its start or end.

    Args:
        at_end: ``True`` → tangent at t=1 (arriving);
            ``False`` → tangent at t=0 (leaving).
    """
    import numpy as _np

    if isinstance(g, Segment):
        d = g.end.coords - g.start.coords
    else:
        d = g.tangent_at_t(1.0) if at_end else g.tangent_at_t(0.0)
    norm = float(_np.linalg.norm(d))
    return d / norm if norm > 1e-12 else d


def with_endpoints(
    g: Segment | CubicBezier, new_start: Point, new_end: Point
) -> Segment | CubicBezier:
    """Return a copy of *g* with replaced start and end points."""
    if isinstance(g, Segment):
        return Segment(new_start, new_end, name=g.name)
    return CubicBezier(new_start, g.p1, g.p2, new_end, name=g.name)


def _reverse_geom(g: Segment | CubicBezier) -> Segment | CubicBezier:
    """Return a copy of *g* with its direction reversed."""
    if isinstance(g, Segment):
        return Segment(g.p2, g.p1, name=g.name)
    return CubicBezier(g.p3, g.p2, g.p1, g.p0, name=g.name)


def build_chain(
    geoms: list[Segment | CubicBezier],
) -> list[Segment | CubicBezier]:
    """Sort *geoms* into a single connected chain, reversing pieces as needed.

    Grows the chain greedily from **both ends**: after each successful
    attachment the loop restarts so that newly freed endpoints on either the
    head or tail are tried immediately.  A piece is reversed when only its
    end (not its start) snaps to the current head/tail.

    Any pieces that cannot be connected to either end after a full pass are
    appended as-is (preserving the previous behaviour for genuinely
    disconnected outlines such as darts).
    """
    chain: list[Segment | CubicBezier] = [geoms[0]]
    remaining: list[Segment | CubicBezier] = list(geoms[1:])

    changed = True
    while remaining and changed:
        changed = False
        tail = geom_end(chain[-1])
        head = geom_start(chain[0])

        for i, g in enumerate(remaining):
            gs, ge = geom_start(g), geom_end(g)

            # ── attach to tail ──────────────────────────────────────────────
            if tail.distance_to(gs) < _CHAIN_SNAP:
                chain.append(remaining.pop(i))
                changed = True
                break
            if tail.distance_to(ge) < _CHAIN_SNAP:
                chain.append(_reverse_geom(remaining.pop(i)))
                changed = True
                break

            # ── attach to head ──────────────────────────────────────────────
            if head.distance_to(ge) < _CHAIN_SNAP:
                chain.insert(0, remaining.pop(i))
                changed = True
                break
            if head.distance_to(gs) < _CHAIN_SNAP:
                chain.insert(0, _reverse_geom(remaining.pop(i)))
                changed = True
                break

    if remaining:
        chain.extend(remaining)  # gap — append remainder as-is
    return chain


def miter_corner(
    ga: Segment | CubicBezier,
    gb: Segment | CubicBezier,
    sa_distance: float,
    miter_limit: float = 4.0,
    check_reflex: bool = True,
) -> Point:
    """Return the miter-join corner between the end of *ga* and the start of *gb*.

    Extends the end-tangent of *ga* and start-tangent of *gb* as infinite lines
    and returns their intersection.  Falls back to the bevel midpoint when the
    lines are parallel, the miter extension exceeds *miter_limit* × *sa_distance*,
    or (when *check_reflex* is True) the corner is reflex (concave on the offset
    curve).

    Args:
        check_reflex: When ``False`` the reflex-corner check is skipped.  Use
            this for zero-gap corners where the two offset endpoints have
            diverged from a shared outline point (e.g. a Bézier with a
            degenerate start control point) — the intersection is still the
            correct outward corner even though it appears behind the end tangent.
    """
    end_a = geom_end(ga)
    start_b = geom_start(gb)
    ta = edge_tangent(ga, at_end=True)
    tb = edge_tangent(gb, at_end=False)

    bevel_mid = (end_a + start_b) * 0.5

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
    if check_reflex and float(np.dot(pt - end_a.coords, ta)) < 0.0:
        return bevel_mid

    if (
        sa_distance > 1e-9
        and float(np.linalg.norm(pt - end_a.coords)) > miter_limit * sa_distance
    ):
        return bevel_mid
    return Point(*pt)


def round_corner(
    ga: Segment | CubicBezier,
    gb: Segment | CubicBezier,
) -> CubicBezier | Point:
    """Return a cubic Bézier arc for a round join at a convex corner.

    Connects ``geom_end(ga)`` to ``geom_start(gb)`` using handle lengths from
    the standard **k = (4/3) tan(θ/4)** formula (< 0.027 % radial error up to
    90°).  Falls back to a :class:`Point` bevel midpoint for parallel/anti-parallel
    tangents, reflex corners, or degenerate geometry.
    """
    end_a = geom_end(ga)
    start_b = geom_start(gb)
    bevel_mid = (end_a + start_b) * 0.5

    ta = edge_tangent(ga, at_end=True)
    tb = edge_tangent(gb, at_end=False)

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
    cp1 = end_a + Point(*(handle * ta))
    cp2 = start_b - Point(*(handle * tb))

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
    ring_coords = [(geom_start(g).x, geom_start(g).y) for g in geoms]
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
    bezier_samples: int = 64,
) -> _sg.Polygon | None:
    """Build a Shapely Polygon from a list of Segments and CubicBeziers.

    The geometries are first sorted into a connected ring via :func:`build_chain`
    (which also reverses individual elements as needed).  Segments contribute
    their start point; CubicBeziers are discretised into *bezier_samples* evenly
    spaced points (default 64 for sub-mm accuracy on typical garment curves).
    The endpoint of the last geometry is appended to close the ring precisely.
    Returns ``None`` if fewer than 3 vertices are produced.
    """
    if not geoms:
        return None
    ordered = build_chain(geoms)
    coords: list[tuple[float, float]] = []
    for g in ordered:
        if isinstance(g, Segment):
            coords.append((g.start.x, g.start.y))
        else:
            for i in range(bezier_samples):
                pt = g.point_at_t(i / bezier_samples)
                coords.append((pt.x, pt.y))
    # Append the endpoint of the last geometry so the ring closes accurately.
    ep = geom_end(ordered[-1])
    coords.append((ep.x, ep.y))
    if len(coords) < 3:
        return None
    return _sg.Polygon(coords)


def seam_length(geoms: list[Segment | CubicBezier]) -> float:
    """Return the total arc length in mm of a list of Segments and/or CubicBeziers."""
    total = 0.0
    for g in geoms:
        total += g.length
    return total


def project_onto_edge(
    edge: Segment | CubicBezier,
    ref: Point,
    inward_ref: Point | None = None,
) -> tuple[Point, np.ndarray, np.ndarray]:
    """Project *ref* onto *edge* and return ``(notch_pt, along, normal)``.

    ``along`` is the unit tangent at the projected point; ``normal`` is the
    unit normal flipped to point toward *inward_ref* when given.
    """
    import shapely.ops as _so

    if isinstance(edge, Segment):
        notch_pt = edge.project_point(ref)
        along = edge.unit_direction
        normal = edge.unit_normal
    else:
        ls = geom_to_shapely(edge)
        _, nearest = _so.nearest_points(_sg.Point(ref.x, ref.y), ls)
        notch_pt = Point(nearest.x, nearest.y)
        # Use svgpathtools radialrange to get the true Bézier parameter t at
        # the closest point
        t_c = _bezier_closest_t(edge._svg(), complex(nearest.x, nearest.y))
        raw = edge.tangent_at_t(t_c)
        norm = float(np.linalg.norm(raw))
        along = raw / norm if norm > 1e-12 else raw
        normal = edge.normal_at_t(t_c)

    if inward_ref is not None:
        dot = float(normal[0]) * (inward_ref.x - notch_pt.x) + float(normal[1]) * (
            inward_ref.y - notch_pt.y
        )
        if dot < 0:
            normal = -normal

    return notch_pt, along, normal


def offset_adaptive(
    geom: Segment | CubicBezier,
    distance: float,
    center: Point | None = None,
    eps: float = 0.1,
) -> list[Segment | CubicBezier]:
    """Offset *geom* outward by *distance* mm, splitting until Hausdorff error < *eps*.

    Segments are offset in a single step; CubicBeziers delegate to
    :meth:`CubicBezier.offset_adaptive` for recursive refinement.
    """
    if isinstance(geom, Segment):
        return [geom.offset(distance, center=center)]
    result: list[Segment | CubicBezier] = list(
        geom.offset_adaptive(distance, center=center, eps=eps)
    )
    return result


# ---------------------------------------------------------------------------
# Dart geometry
# ---------------------------------------------------------------------------


class Dart:
    """Immutable dart (Abnäher) geometry.

    Defined by four key points: *leg_a*, *leg_b* (mouth endpoints), *center*
    (mouth midpoint, base of the fold line) and *tip* (apex).  All secondary
    geometry is derived as properties.

    For rhombus darts a *second_tip* may be supplied explicitly; when omitted
    it defaults to ``mirror_tip`` (reflection of *tip* across the mouth line).

    Curved stitching legs (*stitch_curve_a*, *stitch_curve_b*) replace the
    straight stitch lines when set.  Both run **tip → leg** so direction is
    always consistent with straight legs.

    Use the factory class methods for the common construction cases rather than
    supplying all four points by hand.
    """

    def __init__(
        self,
        leg_a: Point,
        leg_b: Point,
        center: Point,
        tip: Point,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
        second_tip: Point | None = None,
        stitch_curve_a: Segment | CubicBezier | None = None,
        stitch_curve_b: Segment | CubicBezier | None = None,
        _edge_element: object | None = None,
    ) -> None:
        try:
            dart_type = DartType(dart_type)
        except ValueError:
            raise ValueError(
                f"dart_type must be 'triangle' or 'rhombus', got {dart_type!r}"
            )
        self.leg_a = leg_a
        self.leg_b = leg_b
        self.center = center
        self.tip = tip
        self.dart_type: DartType = dart_type
        self.name = name
        self.second_tip: Point | None = second_tip
        if second_tip is not None and dart_type is not DartType.RHOMBUS:
            import warnings
            warnings.warn(
                f"second_tip is only used for rhombus darts, but dart_type is "
                f"{dart_type!r}. The second_tip will be ignored.",
                UserWarning,
                stacklevel=2,
            )
        self.stitch_curve_a: Segment | CubicBezier | None = stitch_curve_a
        self.stitch_curve_b: Segment | CubicBezier | None = stitch_curve_b
        # Internal: the source PatternElement (carries edge style for roof rendering).
        self._edge_element = _edge_element

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_tip_center_width(
        cls,
        tip: Point,
        center: Point,
        width: float,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
        second_tip: Point | None = None,
    ) -> Dart:
        """Construct a dart from tip, mouth centre and width.

        The mouth is placed orthogonally to the fold line (tip→center) at
        *center*, with *leg_a* and *leg_b* each ``width/2`` to either side.
        """
        fold_seg = Segment(tip, center)
        if fold_seg.length < 1e-9:
            raise ValueError("tip and center must be distinct")
        perp = fold_seg.unit_normal  # ⊥ to fold line, already unit-length
        half = width / 2.0
        leg_a = center - Point(*perp) * half
        leg_b = center + Point(*perp) * half
        return cls(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            dart_type=dart_type,
            second_tip=second_tip,
            name=name,
        )

    @classmethod
    def from_edge_at_legs(
        cls,
        edge: object,
        leg_a: Point,
        leg_b: Point,
        tip: Point,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
    ) -> Dart:
        """Place a dart on *edge* with explicitly computed leg points.

        Use this when both legs lie on the same edge but are placed
        asymmetrically — for example one leg projected from a landmark and the
        other a fixed arc-length further along the curve — so none of the
        symmetric :meth:`from_edge_at_t` / :meth:`from_edge_at_point` factories
        apply.  ``_edge_element`` is set automatically so
        :meth:`~sewpat.pattern.PatternPart.add_dart` will split *edge* in-place
        at the dart legs.

        Args:
            edge: ``PatternElement`` wrapping a ``Segment`` or ``CubicBezier``,
                or the geometry object itself.  Must already be in the part
                before :meth:`~sewpat.pattern.PatternPart.add_dart` is called.
            leg_a: First mouth endpoint (already on *edge*).
            leg_b: Second mouth endpoint (already on *edge*).
            tip: Dart tip (apex).
        """
        _geom, edge_elem = _unwrap_edge(edge)
        center = Segment(leg_a, leg_b).midpoint
        return cls(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            dart_type=dart_type,
            name=name,
            _edge_element=edge_elem,
        )

    @classmethod
    def from_tip_and_legs(
        cls,
        tip: Point,
        leg_a: Point,
        leg_b: Point,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
        second_tip: Point | None = None,
    ) -> Dart:
        """Construct a dart from tip and the two explicit mouth endpoints.

        The mouth centre is the midpoint of *leg_a* and *leg_b*.

        Use this factory when the dart legs are **pre-existing named points on
        two separate seam segments** (e.g. the endpoints of two shoulder pieces
        that already define the mouth) and no single source edge needs to be
        split.  ``_edge_element`` is always ``None`` on the result, so
        :meth:`~sewpat.pattern.PatternPart.add_dart` will *not* attempt an
        in-place edge split — the outline is already correct without one.

        If both legs lie on the **same continuous edge** and that edge should
        be trimmed at the dart mouth, use one of the :meth:`from_edge_at_t`,
        :meth:`from_edge_at_point`, or :meth:`from_edge_free_tip` factories
        instead (they set ``_edge_element`` automatically).  If you need
        asymmetric leg placement on a single edge *and* want the in-place
        split, construct the dart directly via ``Dart(..., _edge_element=elem)``
        after computing the leg points yourself.

        Args:
            second_tip: Explicit second apex for rhombus darts.  Defaults to
                the reflection of *tip* across the mouth line.
        """
        center = Segment(leg_a, leg_b).midpoint
        return cls(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            dart_type=dart_type,
            name=name,
            second_tip=second_tip,
        )

    @classmethod
    def from_edge_at_t(
        cls,
        edge: object,
        t: float,
        width: float,
        depth: float,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
    ) -> Dart:
        """Place a dart orthogonally on *edge* at parameter *t*.

        The mouth centre is ``edge.point_at_t(t)``.  The tip is placed
        *depth* mm along the inward normal.  *leg_a* and *leg_b* are
        ``width/2`` to either side along the edge.

        Args:
            edge: ``PatternElement`` wrapping a ``Segment`` or ``CubicBezier``,
                or the geometry object itself.
            t: Parameter ∈ [0, 1] on *edge* for the mouth centre.
        """
        if not (0.0 <= t <= 1.0):
            raise ValueError(f"t must be in [0, 1], got {t}")
        geom, edge_elem = _unwrap_edge(edge)
        if not isinstance(geom, (Segment, CubicBezier)):
            raise TypeError(
                f"from_edge_at_t requires a Segment or CubicBezier edge, "
                f"got {type(geom).__name__!r}"
            )
        center = geom.point_at_t(t)
        # CubicBezier has a position-dependent normal; Segment/Ray/Line expose
        # a constant unit_normal property.
        normal: np.ndarray = (
            geom.normal_at_t(t) if isinstance(geom, CubicBezier) else geom.unit_normal
        )
        tip = center + Point(*normal) * depth
        leg_a = center.move_towards(geom, -width / 2.0)
        leg_b = center.move_towards(geom, +width / 2.0)
        return cls(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            dart_type=dart_type,
            name=name,
            _edge_element=edge_elem,
        )

    @classmethod
    def from_edge_at_point(
        cls,
        edge: object,
        point: Point,
        width: float,
        depth: float,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
    ) -> Dart:
        """Place a dart orthogonally on *edge* at a fixed point on the edge.

        The point is projected onto *edge* to find the mouth centre.
        Supports ``Segment``, ``CubicBezier``, ``Ray`` and ``Line``
        (wrapped in a ``PatternElement`` or passed directly).

        For ``Segment`` and ``CubicBezier`` the normalised Shapely projection
        yields a *t* parameter which is forwarded to :meth:`from_edge_at_t`.

        For ``Ray`` and ``Line`` the foot of the perpendicular from *point* is
        computed directly via a dot product — no bounded *t* parameter applies.
        """
        geom, edge_elem = _unwrap_edge(edge)

        if isinstance(geom, (Ray, Line)):
            # Project point onto the infinite direction via dot product.
            origin: Point = geom.origin if isinstance(geom, Ray) else geom.point
            s = float(np.dot(point.coords - origin.coords, geom.unit_direction))
            center = origin + Point(*geom.unit_direction) * s
            normal: np.ndarray = geom.unit_normal
        else:
            # Segment or CubicBezier — find t via Shapely projection.
            t = float(
                np.clip(
                    geom_to_shapely(geom).project(
                        _sg.Point(point.x, point.y), normalized=True
                    ),
                    0.0,
                    1.0,
                )
            )
            center = geom.point_at_t(t)
            normal = (
                geom.normal_at_t(t)
                if isinstance(geom, CubicBezier)
                else geom.unit_normal
            )

        tip = center + Point(*normal) * depth
        leg_a = center.move_towards(geom, -width / 2.0)
        leg_b = center.move_towards(geom, +width / 2.0)
        return cls(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            dart_type=dart_type,
            name=name,
            _edge_element=edge_elem,
        )

    @classmethod
    def from_edge_free_tip(
        cls,
        edge: object,
        t: float,
        width: float,
        reference_point: Point,
        tip_shortfall: float = 20.0,
        dart_type: DartType | str = DartType.TRIANGLE,
        name: str | None = None,
    ) -> Dart:
        """Place a dart on *edge* at parameter *t* with the tip aimed at a landmark.

        The tip is *tip_shortfall* mm short of *reference_point* along the
        straight line from *reference_point* to the mouth centre.
        """
        if not (0.0 <= t <= 1.0):
            raise ValueError(f"t must be in [0, 1], got {t}")
        geom, edge_elem = _unwrap_edge(edge)
        if not isinstance(geom, (Segment, CubicBezier)):
            raise TypeError(
                f"from_edge_free_tip requires a Segment or CubicBezier edge, "
                f"got {type(geom).__name__!r}"
            )
        center = geom.point_at_t(t)
        tip = reference_point.move_towards(
            Segment(reference_point, center), tip_shortfall
        )
        leg_a = center.move_towards(geom, -width / 2.0)
        leg_b = center.move_towards(geom, +width / 2.0)
        return cls(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            dart_type=dart_type,
            name=name,
            _edge_element=edge_elem,
        )

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def is_triangle(self) -> bool:
        """``True`` for a seam-edge triangle dart."""
        return self.dart_type is DartType.TRIANGLE

    @property
    def roof(self) -> Point:
        """Abnäherdach peak — the corrected seam point above the mouth centre.

        Displaces the mouth centre outward (away from the tip) along the fold
        line by ``h = tan(intake_angle) × (width/2)``.  This ensures the
        folded dart lies flat: when the two stitch legs are brought together
        the roof point becomes a smooth continuation of the seam edge.
        """
        roof_height = float(math.tan(self.intake_angle) * (self.width / 2))
        return self.center.move_towards(
            Ray(self.tip, self.tip.coords - self.center.coords), arc_length=-roof_height
        )

    @property
    def fold_line(self) -> Segment:
        """Fold/crease line from mouth centre to tip."""
        return Segment(self.center, self.tip)

    @property
    def stitch_line_a(self) -> Segment | CubicBezier:
        """Stitch line from tip to leg_a (straight or curved)."""
        if self.stitch_curve_a is not None:
            return self.stitch_curve_a
        return Segment(self.tip, self.leg_a)

    @property
    def stitch_line_b(self) -> Segment | CubicBezier:
        """Stitch line from tip to leg_b (straight or curved)."""
        if self.stitch_curve_b is not None:
            return self.stitch_curve_b
        return Segment(self.tip, self.leg_b)

    @property
    def width(self) -> float:
        """Mouth opening width in mm (leg_a → leg_b)."""
        return self.leg_a.distance_to(self.leg_b)

    @property
    def depth(self) -> float:
        """Depth in mm (mouth centre → tip)."""
        return self.center.distance_to(self.tip)

    @property
    def mirror_tip(self) -> Point:
        """Tip reflected across the mouth line —
        default second apex for rhombus darts.
        """
        return Segment(self.leg_a, self.leg_b).reflect_point(self.tip)

    @property
    def effective_second_tip(self) -> Point:
        """Second apex for rhombus darts: ``second_tip`` if set, else ``mirror_tip``."""
        return self.second_tip if self.second_tip is not None else self.mirror_tip

    @property
    def intake_angle(self) -> float:
        """Full intake angle in radians (leg_a–tip–leg_b)."""
        return float(2 * math.atan(self.width / (2 * self.depth)))

    @property
    def intake_angle_deg(self) -> float:
        """Full intake angle in degrees (leg_a–tip–leg_b).

        Convenience wrapper around :attr:`intake_angle` for human-readable
        output; sewers typically think in degrees rather than radians.
        """
        return math.degrees(self.intake_angle)

    # ------------------------------------------------------------------
    # Transformations
    # ------------------------------------------------------------------

    def translate(self, dx: float, dy: float) -> Dart:
        """Return a translated copy."""

        def _translate_curve(
            c: Segment | CubicBezier | None,
        ) -> Segment | CubicBezier | None:
            if c is None:
                return None
            if isinstance(c, Segment):
                return Segment(c.p1.translate(dx, dy), c.p2.translate(dx, dy))
            # CubicBezier — attributes are p0, p1, p2, p3
            return CubicBezier(
                c.p0.translate(dx, dy),
                c.p1.translate(dx, dy),
                c.p2.translate(dx, dy),
                c.p3.translate(dx, dy),
            )

        return Dart(
            leg_a=self.leg_a.translate(dx, dy),
            leg_b=self.leg_b.translate(dx, dy),
            center=self.center.translate(dx, dy),
            tip=self.tip.translate(dx, dy),
            dart_type=self.dart_type,
            name=self.name,
            second_tip=self.second_tip.translate(dx, dy) if self.second_tip else None,
            stitch_curve_a=_translate_curve(self.stitch_curve_a),
            stitch_curve_b=_translate_curve(self.stitch_curve_b),
        )

    def set_name(self, name: str) -> Dart:
        """Set the name of this dart and return ``self`` for fluent chaining."""
        self.name = name
        return self

    def rotate(self, pivot: Point, angle_rad: float) -> Dart:
        """Return a rotated copy (CCW around *pivot*).

        Preserves intake angle and depth — used for pivot-method dart transfer.
        """

        def _rotate_curve(
            c: Segment | CubicBezier | None,
        ) -> Segment | CubicBezier | None:
            if c is None:
                return None
            if isinstance(c, Segment):
                return Segment(
                    c.p1.rotate(pivot, angle_rad), c.p2.rotate(pivot, angle_rad)
                )
            # CubicBezier — attributes are p0, p1, p2, p3
            return CubicBezier(
                c.p0.rotate(pivot, angle_rad),
                c.p1.rotate(pivot, angle_rad),
                c.p2.rotate(pivot, angle_rad),
                c.p3.rotate(pivot, angle_rad),
            )

        return Dart(
            leg_a=self.leg_a.rotate(pivot, angle_rad),
            leg_b=self.leg_b.rotate(pivot, angle_rad),
            center=self.center.rotate(pivot, angle_rad),
            tip=self.tip.rotate(pivot, angle_rad),
            dart_type=self.dart_type,
            name=self.name,
            second_tip=self.second_tip.rotate(pivot, angle_rad)
            if self.second_tip
            else None,
            stitch_curve_a=_rotate_curve(self.stitch_curve_a),
            stitch_curve_b=_rotate_curve(self.stitch_curve_b),
        )

    def split(self, ratio: float = 0.5) -> tuple[Dart, Dart]:
        """Split into two sub-darts sharing the same tip.

        The intake angle is divided *ratio* : (1 − *ratio*).

        **Preserved on both sub-darts — regardless of** ``dart_type``:

        * ``dart_type`` — both sub-darts have the same type as the parent
          (``TRIANGLE`` *or* ``RHOMBUS``).
        * Name suffixes — when the parent dart has a name, the sub-darts are
          named ``"<name> A"`` and ``"<name> B"`` respectively; when the
          parent is unnamed both sub-darts receive ``None``.  This behaviour
          is identical for ``TRIANGLE`` and ``RHOMBUS`` darts.

        Args:
            ratio: Fraction of the intake angle in the first sub-dart ∈ (0, 1).

        Returns:
            ``(dart_a, dart_b)`` — dart_a covers *ratio* of the total intake
            angle, dart_b covers the remaining ``1 − ratio``.
        """
        if not (0.0 < ratio < 1.0):
            raise ValueError(f"ratio must be in (0, 1), got {ratio}")
        split_angle = self.intake_angle * ratio
        da = np.array(self.leg_a.coords) - np.array(self.tip.coords)
        db = np.array(self.leg_b.coords) - np.array(self.tip.coords)
        sign = 1.0 if float(da[0] * db[1] - da[1] * db[0]) >= 0 else -1.0
        split_leg = self.leg_a.rotate(self.tip, sign * split_angle)
        mid_a = (self.leg_a + split_leg) * 0.5
        mid_b = (split_leg + self.leg_b) * 0.5
        dart_a = Dart(
            leg_a=self.leg_a,
            leg_b=split_leg,
            center=mid_a,
            tip=self.tip,
            dart_type=self.dart_type,
            name=(f"{self.name} A" if self.name else None),
        )
        dart_b = Dart(
            leg_a=split_leg,
            leg_b=self.leg_b,
            center=mid_b,
            tip=self.tip,
            dart_type=self.dart_type,
            name=(f"{self.name} B" if self.name else None),
        )
        return dart_a, dart_b

    def __repr__(self) -> str:
        return (
            f"Dart(name={self.name!r}, leg_a={self.leg_a}, leg_b={self.leg_b}, "
            f"center={self.center}, tip={self.tip}, dart_type={self.dart_type!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Value-based equality on all five defining fields plus dart_type and name.

        Two ``Dart`` instances are equal when their geometry (leg_a, leg_b,
        center, tip, second_tip) and metadata (dart_type, name) compare equal.
        ``stitch_curve_a/b`` and the internal ``_edge_element`` are intentionally
        excluded — they are rendering hints, not part of the dart's mathematical
        identity.
        """
        if not isinstance(other, Dart):
            return NotImplemented
        return (
            self.leg_a == other.leg_a
            and self.leg_b == other.leg_b
            and self.center == other.center
            and self.tip == other.tip
            and self.dart_type == other.dart_type
            and self.name == other.name
            and self.second_tip == other.second_tip
        )

    def __hash__(self) -> int:
        """Hash based on tip coordinates, width and depth for use in sets/dicts."""
        return hash(
            (
                round(self.tip.x, 6),
                round(self.tip.y, 6),
                round(self.width, 6),
                round(self.depth, 6),
                self.dart_type,
                self.name,
            )
        )


def _unwrap_edge(
    edge: object,
) -> tuple[Segment | CubicBezier | Ray | Line, object | None]:
    """Extract geometry and optional source PatternElement from an edge argument.

    Accepts a ``PatternElement`` wrapping a ``Segment``, ``CubicBezier``,
    ``Ray`` or ``Line``, or any of those geometry objects directly.
    Returns ``(geometry, element_or_None)``.
    """
    _LINEAR = (Segment, CubicBezier, Ray, Line)
    geom_attr = getattr(edge, "geometry", None)
    if geom_attr is not None:
        if not isinstance(geom_attr, _LINEAR):
            raise ValueError(
                "PatternElement must wrap a Segment, CubicBezier, Ray or Line, "
                f"got {type(geom_attr).__name__!r}"
            )
        return geom_attr, edge
    if isinstance(edge, _LINEAR):
        return edge, None
    raise TypeError(
        "edge must be a PatternElement, Segment, CubicBezier, Ray or Line, "
        f"got {type(edge).__name__!r}"
    )
