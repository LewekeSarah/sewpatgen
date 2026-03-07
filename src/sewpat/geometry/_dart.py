"""Dart geometry: DartType and Dart."""

import math
from enum import StrEnum

import numpy as np

from ._bezier import CubicBezier
from ._primitives import Line, Point, Ray, Segment


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
) -> tuple[Segment | CubicBezier | Ray | Line, object | None]:
    """Extract geometry and optional source PatternElement from an edge argument."""
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
                f"second_tip is only used for rhombus darts, but dart_type is "
                f"{dart_type!r}. The second_tip will be ignored.",
                UserWarning,
                stacklevel=2,
            )
        self.stitch_curve_a: Segment | CubicBezier | None = stitch_curve_a
        self.stitch_curve_b: Segment | CubicBezier | None = stitch_curve_b
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
        """Construct a dart from tip, mouth centre and width."""
        fold_seg = Segment(tip, center)
        if fold_seg.length < 1e-9:
            raise ValueError("tip and center must be distinct")
        perp = fold_seg.unit_normal
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
        """Place a dart on *edge* with explicitly computed leg points."""
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
        """Construct a dart from tip and the two explicit mouth endpoints."""
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
        """Place a dart orthogonally on *edge* at parameter *t*."""
        if not (0.0 <= t <= 1.0):
            raise ValueError(f"t must be in [0, 1], got {t}")
        geom, edge_elem = _unwrap_edge(edge)
        if not isinstance(geom, (Segment, CubicBezier)):
            raise TypeError(
                f"from_edge_at_t requires a Segment or CubicBezier edge, "
                f"got {type(geom).__name__!r}"
            )
        center = geom.point_at_t(t)
        normal: np.ndarray = (
            geom.normal_at_t(t) if isinstance(geom, CubicBezier) else geom.unit_normal
        )
        tip = center + Point(*normal) * depth
        leg_a = geom.point_along_from(center, -width / 2.0)
        leg_b = geom.point_along_from(center, +width / 2.0)
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
        """Place a dart orthogonally on *edge* at a fixed point on the edge."""
        import shapely.geometry as _sg

        from ._algorithms import geom_to_shapely

        geom, edge_elem = _unwrap_edge(edge)

        if isinstance(geom, (Ray, Line)):
            origin: Point = geom.origin if isinstance(geom, Ray) else geom.point
            s = float(np.dot(point.coords - origin.coords, geom.unit_direction))
            center = origin + Point(*geom.unit_direction) * s
            normal: np.ndarray = geom.unit_normal
        else:
            t = float(
                np.clip(
                    geom_to_shapely(geom).project(_sg.Point(point.x, point.y), normalized=True),
                    0.0,
                    1.0,
                )
            )
            center = geom.point_at_t(t)
            normal = geom.normal_at_t(t) if isinstance(geom, CubicBezier) else geom.unit_normal

        tip = center + Point(*normal) * depth
        leg_a = geom.point_along_from(center, -width / 2.0)
        leg_b = geom.point_along_from(center, +width / 2.0)
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
        """Place a dart on *edge* at parameter *t* with the tip aimed at a landmark."""
        if not (0.0 <= t <= 1.0):
            raise ValueError(f"t must be in [0, 1], got {t}")
        geom, edge_elem = _unwrap_edge(edge)
        if not isinstance(geom, (Segment, CubicBezier)):
            raise TypeError(
                f"from_edge_free_tip requires a Segment or CubicBezier edge, "
                f"got {type(geom).__name__!r}"
            )
        center = geom.point_at_t(t)
        tip = Segment(reference_point, center).point_along_from(reference_point, tip_shortfall)
        leg_a = geom.point_along_from(center, -width / 2.0)
        leg_b = geom.point_along_from(center, +width / 2.0)
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
        """Abnäherdach peak — the corrected seam point above the mouth centre."""
        roof_height = float(math.tan(self.intake_angle) * (self.width / 2))
        return Ray(self.tip, self.tip.coords - self.center.coords).point_along_from(
            self.center, -roof_height
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
        """Tip reflected across the mouth line — default second apex for rhombus darts."""
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
        """Full intake angle in degrees (leg_a–tip–leg_b)."""
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
        """Return a rotated copy (CCW around *pivot*)."""

        def _rotate_curve(
            c: Segment | CubicBezier | None,
        ) -> Segment | CubicBezier | None:
            if c is None:
                return None
            if isinstance(c, Segment):
                return Segment(c.p1.rotate(pivot, angle_rad), c.p2.rotate(pivot, angle_rad))
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
            second_tip=self.second_tip.rotate(pivot, angle_rad) if self.second_tip else None,
            stitch_curve_a=_rotate_curve(self.stitch_curve_a),
            stitch_curve_b=_rotate_curve(self.stitch_curve_b),
        )

    def split(self, ratio: float = 0.5) -> tuple[Dart, Dart]:
        """Split into two sub-darts sharing the same tip."""
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
        """Return an unambiguous string representation."""
        return (
            f"Dart(name={self.name!r}, leg_a={self.leg_a}, leg_b={self.leg_b}, "
            f"center={self.center}, tip={self.tip}, dart_type={self.dart_type!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Value-based equality on all five defining fields plus dart_type and name."""
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
