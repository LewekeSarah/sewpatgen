"""2D geometry primitives for sewing-pattern construction.

Classes
-------
Point        -- immutable 2-D point / displacement vector
_LinearGeom  -- abstract base for Segment, Ray, Line
Segment      -- finite directed line segment
Ray          -- half-line from an origin in a given direction
Line         -- infinite line through a point in a given direction
Rect         -- axis-aligned rectangle (bounding / layout use)
Triangle     -- triangle defined by three vertices
Circle       -- circle defined by a centre and radius
InfoBox      -- labelled text annotation at a position

Notes:
-----
* All coordinates and distances are in **millimetres** unless stated otherwise.
* :class:`Point` doubles as a 2-D displacement vector; arithmetic operators
  (``+``, ``-``, ``*``) operate on the underlying NumPy coordinate array.
* Shapely is **not** imported here; all geometry is pure-math.
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self

import numpy as np


@dataclass(frozen=True)
class Point:
    """An immutable 2-D point (and displacement vector).

    Internally the coordinates are stored as a length-2 NumPy array so that
    vector arithmetic (``+``, ``-``, scalar ``*``) works naturally between
    :class:`Point` instances.

    Args:
        x: X coordinate in mm.
        y: Y coordinate in mm.
        name: Optional label, used in string representations and debugging.

    Example:
        >>> a = Point(3, 0)
        >>> b = Point(0, 4)
        >>> (a - b).distance_to(Point(0, 0))
        5.0
    """

    coords: np.ndarray
    name: str | None = None

    def __init__(self, x: float, y: float, name: str | None = None) -> None:
        """Initialise with coordinates *x*, *y* and optional *name*."""
        object.__setattr__(self, "coords", np.array([x, y], dtype=float))
        object.__setattr__(self, "name", name)

    @property
    def x(self) -> float:
        """X coordinate in mm."""
        return float(self.coords[0])

    @property
    def y(self) -> float:
        """Y coordinate in mm."""
        return float(self.coords[1])

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return f"Point(name={self.name}, x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"
        else:
            return f"Point(x={self.coords[0]:.6g}, y={self.coords[1]:.6g})"

    def distance_to(self, other: Point | np.ndarray) -> float:
        """Return the Euclidean distance to *other*.

        Args:
            other: Another :class:`Point` or a length-2 NumPy array.

        Returns:
            Distance in mm as a :class:`float`.
        """
        if isinstance(other, Point):
            return float(np.linalg.norm(self.coords - other.coords))
        else:
            return float(np.linalg.norm(self.coords - other))

    def distance_to_segment(self, seg: Segment) -> float:
        """Return the shortest distance from this point to *seg*.

        Args:
            seg: The segment to measure against.

        Returns:
            Distance in mm; zero when the point lies exactly on the segment.
        """
        t = seg.project_length(self) / seg.length
        foot = seg.point_at_t(max(0.0, min(1.0, t)))
        return self.distance_to(foot)

    def translate(self, dx: float, dy: float) -> Point:
        """Return a copy translated by *(dx, dy)*.

        Args:
            dx: Displacement in mm along X.
            dy: Displacement in mm along Y.

        Returns:
            A new :class:`Point` offset by *(dx, dy)*.
        """
        return self + Point(dx, dy)

    def __add__(self, other: Point) -> Point:
        """Return ``self + other`` as a new :class:`Point` (vector addition)."""
        if not isinstance(other, Point):
            return NotImplemented
        return Point(*(self.coords + other.coords))

    def __sub__(self, other: Point) -> Point:
        """Return ``self - other`` as a new :class:`Point` (vector subtraction)."""
        if not isinstance(other, Point):
            return NotImplemented
        return Point(*(self.coords - other.coords))

    def __mul__(self, scalar: float) -> Point:
        """Return ``self * scalar`` (uniform scaling of the position vector)."""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Point(*(self.coords * scalar))

    def __rmul__(self, scalar: float) -> Point:
        """Return ``scalar * self`` (reflected scalar multiplication)."""
        return self.__mul__(scalar)

    def __neg__(self) -> Point:
        """Return the negated point ``(-x, -y)``."""
        return Point(*(-self.coords))

    def __eq__(self, other: object) -> bool:
        """Return ``True`` when both coordinates **and** name match exactly.

        Note:
            For approximate spatial equality use :meth:`distance_to` with a
            tolerance instead.
        """
        if not isinstance(other, Point):
            return NotImplemented
        return bool(np.array_equal(self.coords, other.coords)) and self.name == other.name

    def __hash__(self) -> int:
        """Hash based on coordinates rounded to 9 decimal places and name."""
        return hash(
            (
                round(float(self.coords[0]), 9),
                round(float(self.coords[1]), 9),
                self.name,
            )
        )

    def rotate(self, center: Point, angle_rad: float) -> Point:
        """Return a copy rotated counter-clockwise by *angle_rad* around *center*.

        Args:
            center: The pivot point.
            angle_rad: Rotation angle in radians (positive = counter-clockwise).

        Returns:
            A new :class:`Point` at the rotated position.
        """
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        rot = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
        return Point(*(rot @ (self.coords - center.coords) + center.coords))

    def rep_point(self) -> Point:
        """Return the representative point — a :class:`Point` is its own anchor."""
        return self


class _LinearGeom(ABC):
    """Abstract base for all linear geometries.

    Concrete subclasses (:class:`Segment`, :class:`Ray`, :class:`Line`) must
    expose ``_origin`` and ``_direction`` (unit vector) so that the shared
    implementations of :meth:`unit_normal`, :meth:`project_length`,
    :meth:`point_at_distance`, :meth:`point_perpendicular`,
    :meth:`point_along_from`, and :meth:`contains_point` work without any
    override.

    The shared :meth:`contains_point` pattern is:

    1. Compute the perpendicular distance via :meth:`_contains_point_on_axis`.
    2. Optionally check :meth:`project_length` against the extent of the
       geometry (unbounded for :class:`Line`, forward-only for :class:`Ray`,
       ``[0, length]`` for :class:`Segment`).
    """

    # Optional name carried by many concrete geometry types. Declared here so
    # that static type checkers recognise the attribute on all subclasses and
    # assignments of ``None`` are accepted.
    name: str | None = None

    def set_name(self, name: str) -> Self:
        """Set the name of this segment and return ``self`` for fluent chaining.

        Returns the concrete subclass (e.g. :class:`Segment`, :class:`Line`,
        :class:`Ray`) so fluent calls preserve the input type.
        """
        self.name = name
        return self

    @property
    @abstractmethod
    def _origin(self) -> Point:
        """A reference point on the geometry's axis."""

    @property
    @abstractmethod
    def _direction(self) -> np.ndarray:
        """Unit direction vector of the geometry's axis."""

    @property
    def unit_direction(self) -> np.ndarray:
        """Normalised direction vector (unit length, shape ``(2,)``)."""
        return self._direction

    @property
    def unit_normal(self) -> np.ndarray:
        """Unit normal vector (left-hand perpendicular of :attr:`unit_direction`)."""
        d = self._direction
        return np.array([-d[1], d[0]])

    def project_length(self, point: Point) -> float:
        """Return the signed projection of *point* onto the axis.

        Args:
            point: The point to project.

        Returns:
            Signed distance in mm from :attr:`_origin` to the foot of the
            perpendicular from *point*.  Negative when *point* is behind the
            origin relative to :attr:`_direction`.
        """
        return float(np.dot(point.coords - self._origin.coords, self._direction))

    def point_at_distance(self, distance: float) -> Point:
        """Return the point at *distance* mm from :attr:`_origin` along the axis.

        Args:
            distance: Signed distance in mm.  Negative values move opposite
                to :attr:`_direction`.

        Returns:
            The corresponding :class:`Point` on the axis.
        """
        return Point(*(self._origin.coords + self._direction * distance))

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along the axis from *point*.

        Args:
            point: Reference point (need not lie exactly on the axis).
            arc_length: Signed offset in mm from the projection of *point*.

        Returns:
            The resulting :class:`Point` on the axis.
        """
        return self.point_at_distance(self.project_length(point) + arc_length)

    def project_point(self, point: Point) -> Point:
        """Return the orthogonal projection of *point* onto the axis.

        Args:
            point: The point to project.

        Returns:
            The foot of the perpendicular from *point* to the axis.

        Note:
            The result may lie outside finite bounds (e.g. beyond a
            :class:`Segment`'s endpoints) — this is an infinite-line
            projection.
        """
        return self.point_at_distance(self.project_length(point))

    def reflect_point(self, point: Point) -> Point:
        """Return the mirror image of *point* reflected across the axis.

        Args:
            point: The point to reflect.

        Returns:
            A new :class:`Point` on the opposite side of the axis, at the
            same perpendicular distance.
        """
        foot = self.project_point(point)
        return foot + (foot - point)

    def point_perpendicular(self, distance: float, arc_length: float) -> Point:
        """Return a point offset perpendicularly from the axis.

        Args:
            distance: Perpendicular offset in mm (positive = left of direction).
            arc_length: Position along the axis in mm from :attr:`_origin`.

        Returns:
            The offset :class:`Point`.
        """
        return Point(*(self.point_at_distance(arc_length).coords + self.unit_normal * distance))

    @abstractmethod
    def contains_point(self, point: Point, tolerance: float = 1e-9) -> bool:
        """Return ``True`` if *point* lies on this geometry within *tolerance* mm.

        Args:
            point: The point to test.
            tolerance: Maximum allowed distance in mm from the geometry.
                Defaults to ``1e-9`` mm (effectively exact).

        Returns:
            ``True`` if *point* is within *tolerance* mm of the geometry.
        """

    def _contains_point_on_axis(self, point: Point, tolerance: float) -> bool:
        """Return ``True`` if *point* is within *tolerance* mm of the infinite axis.

        This is the shared perpendicular-distance test used by all three
        :meth:`contains_point` implementations.  It does **not** check whether
        the projection falls within the bounded extent of the geometry —
        callers must add that check themselves (see :class:`Ray` and
        :class:`Segment`).

        Args:
            point: The point to test.
            tolerance: Maximum allowed perpendicular distance in mm.

        Returns:
            ``True`` if the foot of the perpendicular from *point* to the axis
            is within *tolerance* mm of *point* itself.
        """
        foot = self.project_point(point)
        return point.distance_to(foot) <= tolerance


def _split_at_ts[T](obj: T, breakpoints: list[float]) -> list[T]:
    """Split *obj* at each *t* in *breakpoints* using ``obj.split(t)``.

    *breakpoints* must be sorted, non-empty, and all strictly inside (0, 1).
    The ``consumed`` / ``local_t`` bookkeeping maps each global-*t* back to
    the parameter space of the running tail after every previous split.

    Returns a list of ``len(breakpoints) + 1`` sub-objects in order.
    """
    tail = obj
    pieces: list[T] = []
    consumed: float = 0.0
    for t in breakpoints:
        local_t = (t - consumed) / (1.0 - consumed)
        head, tail = tail.split(local_t)  # type: ignore[attr-defined]
        pieces.append(head)
        consumed = t
    pieces.append(tail)
    return pieces


class Segment(_LinearGeom):
    """A line segment from p1 to p2."""

    def __init__(self, p1: Point, p2: Point, name: str | None = None) -> None:
        """Initialise from endpoints *p1* and *p2* with optional *name*."""
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
        """Create a segment starting at *start*, pointing towards *through*, with given *length*."""
        d = through.coords - start.coords
        norm = float(np.linalg.norm(d))
        if norm == 0.0:
            raise ValueError("'start' and 'through' must be different points.")
        end_coords = start.coords + (d / norm) * length
        return cls(start, Point(*end_coords), name=name)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return f"Segment(name={self.name}; p1={self.p1}, p2={self.p2})"
        else:
            return f"Segment(p1={self.p1}, p2={self.p2})"

    def __repr__(self) -> str:
        """Return the same as ``__str__``."""
        return self.__str__()

    def translate(self, dx: float, dy: float) -> Segment:
        """Return a copy translated by (dx, dy)."""
        return Segment(self.p1.translate(dx, dy), self.p2.translate(dx, dy), name=self.name)

    def rotate(self, center: Point, angle_rad: float) -> Segment:
        """Return a copy rotated counter-clockwise by *angle_rad* around *center*."""
        return Segment(
            self.p1.rotate(center, angle_rad), self.p2.rotate(center, angle_rad), name=self.name
        )

    @property
    def _origin(self) -> Point:
        """Axis origin — the segment start point ``p1``."""
        return self.p1

    @property
    def _direction(self) -> np.ndarray:
        """Unit direction vector from ``p1`` to ``p2``."""
        return self.unit_direction

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
        return np.asarray(self.p2.coords - self.p1.coords)

    @property
    def unit_direction(self) -> np.ndarray:
        """Normalised direction vector."""
        d = self.p2.coords - self.p1.coords
        n = float(np.linalg.norm(d))
        return np.array(d / n, dtype=float)

    @property
    def midpoint(self) -> Point:
        """Midpoint of the segment."""
        return self.point_at_t(0.5)

    def rep_point(self) -> Point:
        """Return the representative point — the midpoint of the segment."""
        return self.midpoint

    def point_at_t(self, t: float) -> Point:
        """Return the point at parameter *t* ∈ [0, 1] (0 = p1, 1 = p2)."""
        if not (0.0 <= t <= 1.0):
            raise ValueError(f"t must be in [0, 1], got {t}")
        return self.p1 * (1.0 - t) + self.p2 * t

    def split(self, t: float) -> tuple[Segment, Segment]:
        """Split at parameter *t* ∈ (0, 1) and return ``(left, right)``."""
        if not (0.0 < t < 1.0):
            raise ValueError(f"t must be in (0, 1), got {t}")
        mid = self.point_at_t(t)
        return Segment(self.p1, mid, name=self.name), Segment(mid, self.p2, name=self.name)

    def split_at_points(
        self,
        points: list[Point],
        tolerance: float = 0.5,
    ) -> list[Segment]:
        """Split at a list of points that lie on this segment."""
        total_len = self.length
        if total_len == 0.0:
            return [Segment(self.p1, self.p2, name=self.name)]

        eps = tolerance / total_len
        ts: list[float] = sorted(self.project_length(pt) / total_len for pt in points)
        breakpoints: list[float] = [t for t in ts if eps < t < 1.0 - eps]

        if not breakpoints:
            return [Segment(self.p1, self.p2, name=self.name)]

        return _split_at_ts(Segment(self.p1, self.p2, name=self.name), breakpoints)

    def point_perpendicular(
        self,
        distance: float,
        arc_length: float | None = None,
        t: float | None = None,
    ) -> Point:
        """Return a point offset perpendicularly from the segment."""
        if arc_length is not None and t is not None:
            raise ValueError("Specify at most one of 'arc_length' and 't'.")
        if arc_length is not None:
            base = self.point_at_length(arc_length).coords
        elif t is not None:
            base = self.point_at_t(t).coords  # bounds check included
        else:
            base = self.midpoint.coords

        return Point(*(base + self.unit_normal * distance))

    def contains_point(self, point: Point, tolerance: float = 1e-9) -> bool:
        """Return ``True`` if *point* lies on the segment within *tolerance* mm."""
        proj = self.project_length(point)
        return -tolerance <= proj <= self.length + tolerance and self._contains_point_on_axis(
            point, tolerance
        )

    def point_at_length(self, arc_length: float) -> Point:
        """Return the point at *arc_length* mm from p1; raises ValueError if out of range."""
        total = self.length
        return self.point_at_t(arc_length / total)

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this segment from *point*.

        Raises ValueError if the result falls outside the segment bounds.
        """
        return self.point_at_length(self.project_length(point) + arc_length)

    def bounding_box(self) -> tuple[Point, Point]:
        """Return the axis-aligned bounding box as ``(min_point, max_point)``."""
        min_x = min(self.p1.x, self.p2.x)
        min_y = min(self.p1.y, self.p2.y)
        max_x = max(self.p1.x, self.p2.x)
        max_y = max(self.p1.y, self.p2.y)
        return Point(min_x, min_y), Point(max_x, max_y)

    def offset(self, distance: float, center: Point | None = None) -> Segment:
        """Return a new Segment offset perpendicularly by *distance* mm."""
        normal = self.unit_normal
        if center is not None:
            if np.dot(normal, self.midpoint.coords - center.coords) < 0:
                normal = -normal
            offset_vec = normal * abs(distance)
        else:
            offset_vec = normal * distance
        new_p1 = self.p1 + Point(*offset_vec)
        new_p2 = self.p2 + Point(*offset_vec)
        return Segment(new_p1, new_p2, name=self.name)


class Ray(_LinearGeom):
    """A ray starting from a point and going in a specific direction."""

    def __init__(
        self,
        origin: Point,
        direction: tuple[float, float] | list[float] | np.ndarray,
        name: str | None = None,
    ) -> None:
        """Initialize a ray with an origin point and direction vector."""
        self.origin = origin
        if not isinstance(direction, np.ndarray):
            direction = np.array(direction, dtype=float)
        magnitude = float(np.linalg.norm(direction))
        if magnitude < 1e-14:
            raise ValueError("Direction vector cannot be zero")
        self.direction: np.ndarray = np.asarray(direction / magnitude, dtype=float)
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return f"Ray(name={self.name}, origin={self.origin}, direction={self.direction})"
        return f"Ray(origin={self.origin}, direction={self.direction})"

    @property
    def _origin(self) -> Point:  # Ray override
        """Axis origin — the ray's ``origin`` point."""
        return self.origin

    @property
    def _direction(self) -> np.ndarray:  # Ray override
        """Unit direction vector of the ray."""
        return self.direction

    def contains_point(self, point: Point, tolerance: float = 1e-9) -> bool:
        """Return ``True`` if *point* lies on the ray within *tolerance* mm.

        A point behind the origin (negative projection) is never on the ray.
        """
        return self.project_length(point) >= -tolerance and self._contains_point_on_axis(
            point, tolerance
        )

    def translate(self, dx: float, dy: float) -> Ray:
        """Return a copy translated by (dx, dy)."""
        return Ray(self.origin.translate(dx, dy), self.direction, name=self.name)


class Line(_LinearGeom):
    """An infinite line going in a specific direction."""

    def __init__(
        self,
        point: Point,
        direction: tuple[float, float] | list[float] | np.ndarray,
        name: str | None = None,
    ) -> None:
        """Initialize a line with a point and direction vector."""
        self.point = point
        if not isinstance(direction, np.ndarray):
            direction = np.array(direction, dtype=float)
        magnitude = float(np.linalg.norm(direction))
        if magnitude < 1e-14:
            raise ValueError("Direction vector cannot be zero")
        self.direction: np.ndarray = np.asarray(direction / magnitude, dtype=float)
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return f"Line(name={self.name}, point={self.point}, direction={self.direction})"
        return f"Line(point={self.point}, direction={self.direction})"

    @property
    def _origin(self) -> Point:  # Line override
        """Axis origin — the line's reference ``point``."""
        return self.point

    @property
    def _direction(self) -> np.ndarray:  # Line override
        """Unit direction vector of the line."""
        return self.direction

    def contains_point(self, point: Point, tolerance: float = 1e-9) -> bool:
        """Return ``True`` if *point* lies on the line within *tolerance* mm."""
        return self._contains_point_on_axis(point, tolerance)

    def translate(self, dx: float, dy: float) -> Line:
        """Return a copy translated by (dx, dy)."""
        return Line(self.point.translate(dx, dy), self.direction, name=self.name)


class Rect:
    """An axis-aligned rectangle defined by its top-left corner, width and height."""

    def __init__(
        self,
        origin: Point,
        width: float,
        height: float,
        name: str | None = None,
    ) -> None:
        """Initialise from top-left *origin*, *width*, *height*, and optional *name*."""
        self.origin = origin
        self.width = width
        self.height = height
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return (
                f"Rect(name={self.name}, origin={self.origin}, "
                f"width={self.width:.6g}, height={self.height:.6g})"
            )
        return f"Rect(origin={self.origin}, width={self.width:.6g}, height={self.height:.6g})"

    def __repr__(self) -> str:
        """Return an unambiguous string representation."""
        return f"Rect(origin={self.origin}, width={self.width:.6g}, height={self.height:.6g})"

    def translate(self, dx: float, dy: float) -> Rect:
        """Return a copy translated by (dx, dy)."""
        return Rect(self.origin.translate(dx, dy), self.width, self.height, name=self.name)

    def set_name(self, name: str) -> Rect:
        """Set the name of this rectangle and return ``self`` for fluent chaining."""
        self.name = name
        return self

    @property
    def length(self) -> float:
        """Perimeter of the rectangle: ``2 * (width + height)``."""
        return 2 * (self.width + self.height)

    def rep_point(self) -> Point:
        """Return the representative point — the centre of the rectangle."""
        return Point(self.origin.x + self.width / 2.0, self.origin.y + self.height / 2.0)


class Triangle:
    """A triangle defined by three points."""

    def __init__(self, p1: Point, p2: Point, p3: Point, name: str | None = None) -> None:
        """Initialise from three vertices *p1*, *p2*, *p3* and optional *name*."""
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return f"Triangle(name={self.name}, p1={self.p1}, p2={self.p2}, p3={self.p3})"
        return f"Triangle(p1={self.p1}, p2={self.p2}, p3={self.p3})"

    def __repr__(self) -> str:
        """Return the same as ``__str__``."""
        return self.__str__()

    def translate(self, dx: float, dy: float) -> Triangle:
        """Return a copy translated by (dx, dy)."""
        return Triangle(
            self.p1.translate(dx, dy),
            self.p2.translate(dx, dy),
            self.p3.translate(dx, dy),
            name=self.name,
        )

    def rotate(self, center: Point, angle_rad: float) -> Triangle:
        """Return a copy rotated counter-clockwise by *angle_rad* around *center*."""
        return Triangle(
            self.p1.rotate(center, angle_rad),
            self.p2.rotate(center, angle_rad),
            self.p3.rotate(center, angle_rad),
            name=self.name,
        )

    def set_name(self, name: str) -> Triangle:
        """Set the name of this triangle and return ``self`` for fluent chaining."""
        self.name = name
        return self

    @property
    def base_midpoint(self) -> Point:
        """Midpoint of the base edge (``p1`` ↔ ``p2``)."""
        return Point((self.p1.x + self.p2.x) / 2, (self.p1.y + self.p2.y) / 2)

    @property
    def length(self) -> float:
        """Perimeter of the triangle: sum of the three side lengths."""
        return (
            self.p1.distance_to(self.p2)
            + self.p2.distance_to(self.p3)
            + self.p3.distance_to(self.p1)
        )

    def rep_point(self) -> Point:
        """Return the representative point — the centroid of the three vertices."""
        return Point(
            (self.p1.x + self.p2.x + self.p3.x) / 3.0,
            (self.p1.y + self.p2.y + self.p3.y) / 3.0,
        )


class InfoBox:
    """A text info box displayed at a given position."""

    def __init__(
        self,
        position: Point,
        header: str,
        notes: list[str] | None = None,
    ) -> None:
        """Initialise with display *position*, bold *header*, and optional *notes*."""
        self.position = position
        self.header = header
        self.notes: list[str] = notes if notes is not None else []
        self.name: str | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"InfoBox(header={self.header!r}, position={self.position})"

    def __repr__(self) -> str:
        """Return the same as ``__str__``."""
        return self.__str__()

    def translate(self, dx: float, dy: float) -> InfoBox:
        """Return a copy translated by (dx, dy)."""
        moved = InfoBox(self.position.translate(dx, dy), self.header, list(self.notes))
        moved.name = self.name
        return moved

    def rotate(self, center: Point, angle_rad: float) -> InfoBox:
        """Return a copy rotated counter-clockwise by *angle_rad* around *center*."""
        moved = InfoBox(self.position.rotate(center, angle_rad), self.header, list(self.notes))
        moved.name = self.name
        return moved

    def rep_point(self) -> Point:
        """Return the representative point — the display position of the info box."""
        return self.position


class Circle:
    """A circle defined by a center point and radius."""

    def __init__(self, center: Point, radius: float, name: str | None = None) -> None:
        """Initialize a circle with center point and radius."""
        if radius <= 0:
            raise ValueError("Radius must be positive")

        self.center = center
        self.radius = radius
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.name:
            return f"Circle(name={self.name}, center={self.center}, radius={self.radius:.6g})"
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

    def contains_point_inside(self, point: Point, include_boundary: bool = True) -> bool:
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

    def rotate(self, center: Point, angle_rad: float) -> Circle:
        """Return a copy rotated counter-clockwise by *angle_rad* around *center*."""
        return Circle(self.center.rotate(center, angle_rad), self.radius, name=self.name)

    def set_name(self, name: str) -> Circle:
        """Set the name of this circle and return ``self`` for fluent chaining."""
        self.name = name
        return self

    def rep_point(self) -> Point:
        """Return the representative point — the centre of the circle."""
        return self.center

    @property
    def length(self) -> float:
        """Circumference of the circle: ``2 * π * radius``.

        Alias for :attr:`circumference` so that :class:`Circle` participates
        uniformly in :meth:`~sewpat.pattern.PatternPart.seam_length`.
        """
        return self.circumference

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this circle from *point* (CCW)."""
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
