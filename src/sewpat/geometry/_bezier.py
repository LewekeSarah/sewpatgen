"""CubicBezier curve and its private helpers."""

import math

import numpy as np
import shapely.geometry as _sg
from svgpathtools import CubicBezier as _SvgCubicBezier

from ._primitives import Point

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


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


def _bezier_closest_t(svg_bezier: _SvgCubicBezier, pt_c: complex) -> float:
    """Return *t* ∈ [0, 1] of the point on *svg_bezier* closest to *pt_c*."""
    return float(svg_bezier.radialrange(pt_c)[0][1])


def _bezier_shapely(b: CubicBezier, n: int = 64) -> _sg.LineString:
    """Discretise a CubicBezier into a Shapely LineString with *n* segments."""
    return _sg.LineString([(b.point_at_t(i / n).x, b.point_at_t(i / n).y) for i in range(n + 1)])


def _true_offset_ls(b: CubicBezier, d: float, n: int = 64) -> _sg.LineString:
    """Sample the true parallel offset of *b* at signed distance *d* into a Shapely LineString."""
    pts = []
    for i in range(n + 1):
        t = i / n
        pt = b.point_at_t(t)
        nor = b.normal_at_t(t)
        pts.append((pt.x + d * nor[0], pt.y + d * nor[1]))
    return _sg.LineString(pts)


def _intersect_bezier_bezier(a: CubicBezier, b: CubicBezier, tol: float = 1e-12) -> list[Point]:
    """Find intersections between two cubic Bézier curves using svgpathtools."""
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


# ---------------------------------------------------------------------------
# CubicBezier
# ---------------------------------------------------------------------------


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

    def __init__(self, p0: Point, p1: Point, p2: Point, p3: Point, name: str | None = None) -> None:
        """Initialize a cubic Bezier curve with four control points."""
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"CubicBezier(name={self.name}, p0={self.p0}, p1={self.p1}, p2={self.p2}, p3={self.p3})"
        )

    def __repr__(self) -> str:
        """Return the same as ``__str__``."""
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
        """Evaluate the Bezier curve at parameter t."""
        t2 = t * t
        t3 = t2 * t
        mt = 1.0 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        x = mt3 * self.p0.x + 3 * mt2 * t * self.p1.x + 3 * mt * t2 * self.p2.x + t3 * self.p3.x
        y = mt3 * self.p0.y + 3 * mt2 * t * self.p1.y + 3 * mt * t2 * self.p2.y + t3 * self.p3.y

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
        """Exact arc length via Gauss-Legendre quadrature (delegated to svgpathtools)."""
        return float(self._svg().length())

    def tangent_at_t(self, t: float) -> np.ndarray:
        """Tangent vector at *t* (not normalised), via svgpathtools B'(t)."""
        d = self._svg().derivative(t)
        return np.array([d.real, d.imag])

    def normal_at_t(self, t: float) -> np.ndarray:
        """Unit normal at *t*: 90° counter-clockwise from the tangent (left of travel)."""
        svg = self._svg()
        try:
            n = svg.normal(t)
            return np.array([n.real, n.imag])
        except ValueError:
            eps = 1e-4
            fallback_t = max(eps, t - eps) if t > 0.5 else min(1.0 - eps, t + eps)
            try:
                n = svg.normal(fallback_t)
                return np.array([n.real, n.imag])
            except ValueError:
                dt = 1e-4
                t0 = max(0.0, t - dt)
                t1 = min(1.0, t + dt)
                p0 = self.point_at_t(t0)
                p1 = self.point_at_t(t1)
                dx, dy = p1.x - p0.x, p1.y - p0.y
                length = (dx**2 + dy**2) ** 0.5 or 1.0
                return np.array([-dy / length, dx / length])

    def point_at_length(self, arc_length: float) -> Point:
        """Return the point at *arc_length* mm from p0; raises ValueError if out of range."""
        total = self.length
        if arc_length < 0 or arc_length > total + 1e-9:
            raise ValueError(f"arc_length {arc_length:.4f} is outside [0, {total:.4f}]")
        t = self._svg().ilength(arc_length)
        return self.point_at_t(t)

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along this curve from *point*."""
        svg = self._svg()
        t0 = _bezier_closest_t(svg, complex(point.x, point.y))
        pos = float(svg.length(t1=t0))
        return self.point_at_length(pos + arc_length)

    def split(self, t: float) -> tuple[CubicBezier, CubicBezier]:
        """Split at *t* into (left, right) using de Casteljau (delegated to svgpathtools)."""
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
        """Split at a list of points that lie on this curve."""
        total_len = self.length
        if total_len == 0.0:
            return [CubicBezier(self.p0, self.p1, self.p2, self.p3)]

        svg = self._svg()
        eps = tolerance / total_len

        ts: list[float] = sorted(_bezier_closest_t(svg, complex(pt.x, pt.y)) for pt in points)
        breakpoints: list[float] = [t for t in ts if eps < t < 1.0 - eps]

        if not breakpoints:
            return [CubicBezier(self.p0, self.p1, self.p2, self.p3)]

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
        """Compute the axis-aligned bounding box by finding B'(t)=0 extrema."""
        x_coords = [self.p0.x, self.p3.x]
        y_coords = [self.p0.y, self.p3.y]

        a_x = 3 * (self.p3.x - 3 * self.p2.x + 3 * self.p1.x - self.p0.x)
        b_x = 6 * (self.p2.x - 2 * self.p1.x + self.p0.x)
        c_x = 3 * (self.p1.x - self.p0.x)

        a_y = 3 * (self.p3.y - 3 * self.p2.y + 3 * self.p1.y - self.p0.y)
        b_y = 6 * (self.p2.y - 2 * self.p1.y + self.p0.y)
        c_y = 3 * (self.p1.y - self.p0.y)

        for a, b, c in [(a_x, b_x, c_x), (a_y, b_y, c_y)]:
            if abs(a) > 1e-10:
                roots = _solve_quadratic(a, b, c)
                for t in roots:
                    if 0 <= t <= 1:
                        point = self.point_at_t(t)
                        x_coords.append(point.x)
                        y_coords.append(point.y)
            elif abs(b) > 1e-10:
                t = -c / b
                if 0 <= t <= 1:
                    point = self.point_at_t(t)
                    x_coords.append(point.x)
                    y_coords.append(point.y)

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        return Point(min_x, min_y), Point(max_x, max_y)

    def point_perpendicular(self, distance: float, t: float) -> Point:
        """Return a point offset by *distance* mm in the normal direction at *t*."""
        pt = self.point_at_t(t)
        nor = self.normal_at_t(t)
        return Point(pt.x + distance * nor[0], pt.y + distance * nor[1])

    def contains_point(self, point: Point, tolerance: float = 0.01) -> bool:
        """Return True if *point* is within *tolerance* mm of the curve."""
        ls = _bezier_shapely(self)
        return bool(ls.distance(_sg.Point(point.x, point.y)) <= tolerance)

    def offset(
        self,
        distance: float,
        center: Point | None = None,
        hausdorff_limit: float = 1.5,
    ) -> CubicBezier:
        """Return an approximate offset curve using the hodograph approximation."""
        if center is not None:
            mid = self.point_at_t(0.5)
            n_mid = self.normal_at_t(0.5)
            sign = 1.0 if np.dot(n_mid, mid.coords - center.coords) >= 0 else -1.0
            d = sign * abs(distance)
        else:
            d = distance

        def _hodograph(curve: CubicBezier) -> CubicBezier:
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

        if abs(distance) > 1e-9 and math.isfinite(hausdorff_limit):
            ls_true = _true_offset_ls(self, d)
            ls_off = _bezier_shapely(approx)
            if ls_true.hausdorff_distance(ls_off) > hausdorff_limit * abs(distance):
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
        """Return the Hausdorff distance (mm) between the hodograph and the true offset."""
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
        """Return the offset as a list of Béziers, split until Hausdorff error < *eps* mm."""
        if center is not None:
            mid = self.point_at_t(0.5)
            n_mid = self.normal_at_t(0.5)
            sign = 1.0 if np.dot(n_mid, mid.coords - center.coords) >= 0 else -1.0
            d = sign * abs(distance)
        else:
            d = distance

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

        if _depth >= _max_depth:
            return [approx]

        ls_true = _true_offset_ls(self, d)
        ls_off = _bezier_shapely(approx)
        if ls_true.hausdorff_distance(ls_off) <= eps:
            return [approx]

        left, right = self.split(0.5)
        return left.offset_adaptive(
            d, center=None, eps=eps, _depth=_depth + 1, _max_depth=_max_depth
        ) + right.offset_adaptive(d, center=None, eps=eps, _depth=_depth + 1, _max_depth=_max_depth)
