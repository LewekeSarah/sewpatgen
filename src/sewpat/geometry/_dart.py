"""Dart geometry: DartType and Dart."""

import math
from collections.abc import Callable
from enum import StrEnum

import numpy as np

from ._bezier import CubicBezier
from ._primitives import Line, Point, Ray, Segment, _LinearGeom


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


def _unwrap_edge(
    edge: object,
) -> tuple[_LinearGeom | CubicBezier, object | None]:
    """Extract geometry and optional source PatternElement from an edge argument."""
    geom_attr = getattr(edge, "geometry", None)
    if geom_attr is not None:
        if not isinstance(geom_attr, (_LinearGeom, CubicBezier)):
            raise ValueError(
                "PatternElement must wrap a Segment, CubicBezier, Ray or Line, "
                f"got {type(geom_attr).__name__!r}"
            )
        return geom_attr, edge
    if isinstance(edge, (_LinearGeom, CubicBezier)):
        return edge, None
    raise TypeError(
        "edge must be a PatternElement, Segment, CubicBezier, Ray or Line, "
        f"got {type(edge).__name__!r}"
    )


def _dart_from_points(
    leg_a: Point,
    leg_b: Point,
    center: Point,
    tip: Point,
    dart_type: DartType | str,
    name: str | None,
    *,
    second_tip: Point | None = None,
    edge_elem: object | None = None,
) -> Dart:
    """Construct a :class:`Dart` from fully-resolved points.

    Single place where ``Dart(...)`` is called by all factory functions,
    so the constructor argument list only exists once.
    """
    return Dart(
        leg_a=leg_a,
        leg_b=leg_b,
        center=center,
        tip=tip,
        dart_type=dart_type,
        name=name,
        second_tip=second_tip,
        _edge_element=edge_elem,
    )


def _resolve_edge_center_normal(
    geom: _LinearGeom | CubicBezier,
    t: float,
) -> tuple[Point, np.ndarray]:
    """Return ``(center, normal)`` for an edge at parameter *t*.

    For a :class:`Segment` or :class:`CubicBezier`, *t* is the standard
    parametric value in ``[0, 1]``.  For a :class:`Ray` or :class:`Line`,
    *t* is treated as an arc-length distance from the origin (those types
    are unbounded and have no intrinsic length to normalise against; prefer
    :func:`dart_from_edge_at_point` for Ray/Line edges).

    The normal is constant for all :class:`_LinearGeom` subclasses
    (:attr:`~_LinearGeom.unit_normal`); only :class:`CubicBezier` evaluates
    the normal at *t* via :meth:`~CubicBezier.normal_at_t`.
    """
    if isinstance(geom, CubicBezier):
        center = geom.point_at_t(t)
        normal: np.ndarray = geom.normal_at_t(t)
    elif isinstance(geom, Segment):
        center = geom.point_at_t(t)
        normal = geom.unit_normal
    else:
        # Ray or Line: unbounded, treat t as arc-length distance
        center = geom.point_at_distance(t)
        normal = geom.unit_normal
    return center, normal


# ---------------------------------------------------------------------------
# Module-level factory functions
# ---------------------------------------------------------------------------


def _validate_t(t: float) -> None:
    """Raise :exc:`ValueError` if *t* is outside ``[0, 1]``."""
    if not (0.0 <= t <= 1.0):
        raise ValueError(f"t must be in [0, 1], got {t}")


def dart_from_tip_center_width(
    tip: Point,
    center: Point,
    width: float,
    dart_type: DartType | str = "triangle",
    name: str | None = None,
    second_tip: Point | None = None,
) -> Dart:
    """Construct a dart from tip, mouth center and width.

    This is the free-function form of :meth:`Dart.from_tip_center_width`.
    """
    fold_seg = Segment(tip, center)
    if fold_seg.length < 1e-9:
        raise ValueError("tip and center must be distinct")
    half = width / 2.0
    perp = fold_seg.unit_normal
    leg_a = center - Point(*perp) * half
    leg_b = center + Point(*perp) * half
    return _dart_from_points(leg_a, leg_b, center, tip, dart_type, name, second_tip=second_tip)


def dart_from_tip_and_legs(
    tip: Point,
    leg_a: Point,
    leg_b: Point,
    dart_type: DartType | str = "triangle",
    name: str | None = None,
    second_tip: Point | None = None,
) -> Dart:
    """Construct a dart from tip and the two explicit mouth endpoints.

    This is the free-function form of :meth:`Dart.from_tip_and_legs`.
    """
    center = Segment(leg_a, leg_b).midpoint
    return _dart_from_points(leg_a, leg_b, center, tip, dart_type, name, second_tip=second_tip)


def dart_from_edge_at_legs(
    edge: object,
    leg_a: Point,
    leg_b: Point,
    tip: Point,
    dart_type: DartType | str = "triangle",
    name: str | None = None,
) -> Dart:
    """Place a dart on *edge* with explicitly supplied leg points.

    This is the free-function form of :meth:`Dart.from_edge_at_legs`.
    """
    _geom, edge_elem = _unwrap_edge(edge)
    center = Segment(leg_a, leg_b).midpoint
    return _dart_from_points(leg_a, leg_b, center, tip, dart_type, name, edge_elem=edge_elem)


def dart_from_edge_at_t(
    edge: object,
    t: float,
    width: float,
    depth: float,
    dart_type: DartType | str = "triangle",
    name: str | None = None,
) -> Dart:
    """Place a dart orthogonally on *edge* at parameter *t*.

    This is the free-function form of :meth:`Dart.from_edge_at_t`.
    """
    _validate_t(t)
    geom, edge_elem = _unwrap_edge(edge)
    center, normal = _resolve_edge_center_normal(geom, t)
    tip = center + Point(*normal) * depth
    leg_a = geom.point_along_from(center, -width / 2.0)
    leg_b = geom.point_along_from(center, +width / 2.0)
    return _dart_from_points(leg_a, leg_b, center, tip, dart_type, name, edge_elem=edge_elem)


def dart_from_edge_at_point(
    edge: object,
    point: Point,
    width: float,
    depth: float,
    dart_type: DartType | str = "triangle",
    name: str | None = None,
) -> Dart:
    """Place a dart orthogonally on *edge* nearest to *point*.

    This is the free-function form of :meth:`Dart.from_edge_at_point`.
    """
    import shapely.geometry as _sg

    from ._algorithms import geom_to_shapely

    geom, edge_elem = _unwrap_edge(edge)

    if isinstance(geom, (Ray, Line)):
        center = geom.point_at_distance(geom.project_length(point))
        normal: np.ndarray = geom.unit_normal
    else:
        t = float(
            np.clip(
                geom_to_shapely(geom).project(_sg.Point(point.x, point.y), normalized=True),
                0.0,
                1.0,
            )
        )
        center, normal = _resolve_edge_center_normal(geom, t)

    tip = center + Point(*normal) * depth
    leg_a = geom.point_along_from(center, -width / 2.0)
    leg_b = geom.point_along_from(center, +width / 2.0)
    return _dart_from_points(leg_a, leg_b, center, tip, dart_type, name, edge_elem=edge_elem)


def dart_from_edge_free_tip(
    edge: object,
    t: float,
    width: float,
    reference_point: Point,
    tip_shortfall: float = 20.0,
    dart_type: DartType | str = "triangle",
    name: str | None = None,
) -> Dart:
    """Place a dart on *edge* at *t* with the tip aimed at *reference_point*.

    This is the free-function form of :meth:`Dart.from_edge_free_tip`.
    """
    _validate_t(t)
    geom, edge_elem = _unwrap_edge(edge)
    if not isinstance(geom, (Segment, CubicBezier)):
        raise TypeError(
            f"dart_from_edge_free_tip requires a Segment or CubicBezier edge, "
            f"got {type(geom).__name__!r}"
        )
    center = geom.point_at_t(t)
    tip = Segment(reference_point, center).point_along_from(reference_point, tip_shortfall)
    leg_a = geom.point_along_from(center, -width / 2.0)
    leg_b = geom.point_along_from(center, +width / 2.0)
    return _dart_from_points(leg_a, leg_b, center, tip, dart_type, name, edge_elem=edge_elem)


# ---------------------------------------------------------------------------
# Dart class
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

    Use the factory class methods (or the equivalent module-level
    ``dart_from_*`` functions) for the common construction cases rather than
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
        """Initialise a dart from its four key points and optional metadata."""
        try:
            dart_type = DartType(dart_type)
        except ValueError:
            raise ValueError(f"dart_type must be 'triangle' or 'rhombus', got {dart_type!r}")
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
                f"second_tip is only used for rhombus darts, but dart_type is {dart_type!r}. "
                "The second_tip will be ignored.",
                UserWarning,
                stacklevel=2,
            )
        self.stitch_curve_a: Segment | CubicBezier | None = stitch_curve_a
        self.stitch_curve_b: Segment | CubicBezier | None = stitch_curve_b
        self._edge_element = _edge_element

    # ------------------------------------------------------------------
    # Factory class methods — thin wrappers around the module-level functions
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
        """Construct a dart from tip, mouth center and width.

        Delegates to :func:`dart_from_tip_center_width`.
        """
        return dart_from_tip_center_width(tip, center, width, dart_type, name, second_tip)

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
        """Construct a dart from tip and the two mouth endpoints.

        Delegates to :func:`dart_from_tip_and_legs`.
        """
        return dart_from_tip_and_legs(tip, leg_a, leg_b, dart_type, name, second_tip)

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
        """Place a dart on *edge* with explicit leg points.

        Delegates to :func:`dart_from_edge_at_legs`.
        """
        return dart_from_edge_at_legs(edge, leg_a, leg_b, tip, dart_type, name)

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

        Delegates to :func:`dart_from_edge_at_t`.
        """
        return dart_from_edge_at_t(edge, t, width, depth, dart_type, name)

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
        """Place a dart orthogonally on *edge* nearest to *point*.

        Delegates to :func:`dart_from_edge_at_point`.
        """
        return dart_from_edge_at_point(edge, point, width, depth, dart_type, name)

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
        """Place a dart on *edge* at *t* aimed at *reference_point*.

        Delegates to :func:`dart_from_edge_free_tip`.
        """
        return dart_from_edge_free_tip(
            edge, t, width, reference_point, tip_shortfall, dart_type, name
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
        """Abnäherdach peak — corrected seam point on the fold line.

        The *roof* accounts for the fabric tuck: when the dart is folded and
        stitched, the seam at ``center`` must be shifted **outward** (away from
        the tip) by ``roof_height`` so that the finished edge lies flat.
        It is computed as::

            roof_height = tan(intake_angle) * (width / 2)
            roof = center - fold_direction * roof_height

        where ``fold_direction`` points from ``center`` toward ``tip``, so
        subtracting it moves the roof *past* ``center`` in the outward direction.

        The roof therefore lies on the infinite extension of the fold line on
        the far side of ``center`` from ``tip`` for typical darts, but its
        exact position depends on the dart's proportions and edge curvature:

        * For typical darts it lies **beyond** ``center`` (outward past the seam).
        * For very wide or shallow darts ``roof_height`` can become very large.
        * On curved edges the normal may not point directly away from the mouth,
          so ``tip`` itself can be offset, shifting where ``roof`` falls.
        """
        roof_height = math.tan(self.intake_angle) * (self.width / 2.0)
        fold_dir = self.fold_line.unit_direction  # center → tip
        return self.center + Point(*(-fold_dir * roof_height))

    @property
    def fold_line(self) -> Segment:
        """Full fold/crease line from mouth center to tip.

        Runs ``center → tip``, i.e. from the base of the dart to its apex.
        ``fold_line.unit_direction`` therefore points *towards* the tip and is
        used as the reference direction for dart transfer and rotation.

        Note: :attr:`roof` is a derived *point* on the infinite extension of
        this segment.  For typical darts it lies on the **far side of**
        ``center`` from ``tip`` (outward past the seam), though exact position
        depends on the dart's proportions and edge curvature.
        """
        return Segment(self.center, self.tip)

    @property
    def stitch_line_a(self) -> Segment | CubicBezier:
        """Stitch line from tip to leg_a.

        Returns :attr:`stitch_curve_a` if set, otherwise a straight
        :class:`Segment` from ``tip`` to ``leg_a``.
        """
        if self.stitch_curve_a is not None:
            return self.stitch_curve_a
        return Segment(self.tip, self.leg_a)

    @property
    def stitch_line_b(self) -> Segment | CubicBezier:
        """Stitch line from tip to leg_b.

        Returns :attr:`stitch_curve_b` if set, otherwise a straight
        :class:`Segment` from ``tip`` to ``leg_b``.
        """
        if self.stitch_curve_b is not None:
            return self.stitch_curve_b
        return Segment(self.tip, self.leg_b)

    @property
    def width(self) -> float:
        """Mouth opening width in mm (leg_a → leg_b)."""
        return self.leg_a.distance_to(self.leg_b)

    @property
    def depth(self) -> float:
        """Depth in mm (mouth center → tip)."""
        return self.center.distance_to(self.tip)

    @property
    def mirror_tip(self) -> Point:
        """Tip reflected across the mouth line — default second apex for rhombus darts."""
        return Segment(self.leg_a, self.leg_b).reflect_point(self.tip)

    @property
    def effective_second_tip(self) -> Point:
        """Second apex for rhombus darts: ``second_tip`` if set, else ``mirror_tip``."""
        return self.second_tip if self.second_tip is not None else self.mirror_tip

    @property
    def intake_angle(self) -> float:
        """Full intake angle in radians (leg_a–tip–leg_b).

        Computed as twice the arctangent of half-width over depth::

            intake_angle = 2 * atan2(width / 2, depth)

        Handles ``depth = 0`` (flat dart) gracefully — returns ``π`` rather
        than raising :exc:`ZeroDivisionError`.
        """
        return 2.0 * math.atan2(self.width / 2.0, self.depth)

    @property
    def intake_angle_deg(self) -> float:
        """Full intake angle in degrees (leg_a–tip–leg_b).

        Equivalent to ``math.degrees(self.intake_angle)``.
        """
        return math.degrees(self.intake_angle)

    # ------------------------------------------------------------------
    # Transformations
    # ------------------------------------------------------------------

    @staticmethod
    def _transform_curve(
        c: Segment | CubicBezier | None,
        fn: Callable[[Point], Point],
    ) -> Segment | CubicBezier | None:
        """Apply point-transform *fn* to every control point of *c*."""
        if c is None:
            return None
        if isinstance(c, Segment):
            return Segment(fn(c.start), fn(c.end))
        return CubicBezier(fn(c.p0), fn(c.p1), fn(c.p2), fn(c.p3))

    def translate(self, dx: float, dy: float) -> Dart:
        """Return a translated copy."""

        def mv(p: Point) -> Point:
            return p.translate(dx, dy)

        return Dart(
            leg_a=mv(self.leg_a),
            leg_b=mv(self.leg_b),
            center=mv(self.center),
            tip=mv(self.tip),
            dart_type=self.dart_type,
            name=self.name,
            second_tip=mv(self.second_tip) if self.second_tip else None,
            stitch_curve_a=self._transform_curve(self.stitch_curve_a, mv),
            stitch_curve_b=self._transform_curve(self.stitch_curve_b, mv),
        )

    def set_name(self, name: str) -> Dart:
        """Return a copy of this dart with *name* set.

        All other fields are unchanged.  Returns a new :class:`Dart` rather
        than mutating ``self``, consistent with :meth:`translate` and
        :meth:`rotate`.
        """
        return Dart(
            leg_a=self.leg_a,
            leg_b=self.leg_b,
            center=self.center,
            tip=self.tip,
            dart_type=self.dart_type,
            name=name,
            second_tip=self.second_tip,
            stitch_curve_a=self.stitch_curve_a,
            stitch_curve_b=self.stitch_curve_b,
        )

    def rotate(self, pivot: Point, angle_rad: float) -> Dart:
        """Return a rotated copy (CCW around *pivot*)."""

        def rot(p: Point) -> Point:
            return p.rotate(pivot, angle_rad)

        return Dart(
            leg_a=rot(self.leg_a),
            leg_b=rot(self.leg_b),
            center=rot(self.center),
            tip=rot(self.tip),
            dart_type=self.dart_type,
            name=self.name,
            second_tip=rot(self.second_tip) if self.second_tip else None,
            stitch_curve_a=self._transform_curve(self.stitch_curve_a, rot),
            stitch_curve_b=self._transform_curve(self.stitch_curve_b, rot),
        )

    def split(self, ratio: float = 0.5) -> tuple[Dart, Dart]:
        """Split into two sub-darts sharing the same tip."""
        if not (0.0 < ratio < 1.0):
            raise ValueError(f"ratio must be in (0, 1), got {ratio}")
        split_angle = self.intake_angle * ratio
        da = self.leg_a.coords - self.tip.coords
        db = self.leg_b.coords - self.tip.coords
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
        """Return an unambiguous string representation."""
        return (
            f"Dart(name={self.name!r}, leg_a={self.leg_a}, leg_b={self.leg_b}, "
            f"center={self.center}, tip={self.tip}, dart_type={self.dart_type!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Value-based equality on all seven defining fields.

        Fields compared: ``leg_a``, ``leg_b``, ``center``, ``tip``,
        ``dart_type``, ``name``, ``second_tip``.
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
        """Hash based on tip coordinates, width and depth."""
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
