"""CubicBezier curve and shape-utility helpers.

This module defines :class:`CubicBezier` and the private helper functions that
operate directly on curve geometry (discretisation, closest-t lookup, and
Bézier–Bézier intersection).  The numerically-intensive offset subsystem lives
in :mod:`sewpat.geometry._bezier_offset`.
"""

from collections.abc import Callable, Sequence

import numpy as np
import shapely.geometry as _sg
from svgpathtools import CubicBezier as _SvgCubicBezier

from ._primitives import Point, _split_at_ts


def _bernstein_basis(t: float) -> tuple[float, float, float, float]:
    """Return the four cubic Bernstein basis values at parameter *t* ∈ [0, 1].

    The standard cubic Bernstein polynomials are::

        b0 = (1-t)³
        b1 = 3·t·(1-t)²
        b2 = 3·t²·(1-t)
        b3 = t³

    so that ``b0+b1+b2+b3 = 1`` for every *t*.  Used by both
    :meth:`CubicBezier.point_at_t` and :func:`fit_cubic_bezier`.

    Returns:
        ``(b0, b1, b2, b3)`` as a 4-tuple of :class:`float`.
    """
    mt = 1.0 - t
    return mt**3, 3.0 * t * mt**2, 3.0 * t**2 * mt, t**3


def _bezier_closest_t(svg_bezier: _SvgCubicBezier, pt_c: complex) -> float:
    """Return the parameter *t* ∈ [0, 1] at which *svg_bezier* is closest to *pt_c*.

    Uses svgpathtools' ``radialrange`` (minimum-distance scan) internally.
    """
    return float(svg_bezier.radialrange(pt_c)[0][1])


def _bezier_shapely(b: CubicBezier, n: int = 64) -> _sg.LineString:
    """Discretise *b* into a Shapely LineString using *n+1* uniformly-spaced samples.

    The resulting polyline has *n* segments connecting the sample points at
    ``t = 0, 1/n, 2/n, …, 1``.  Used for Hausdorff-distance checks.
    """
    pts = [b.point_at_t(i / n) for i in range(n + 1)]
    return _sg.LineString([(p.x, p.y) for p in pts])


def _true_offset_ls(b: CubicBezier, d: float, n: int = 64) -> _sg.LineString:
    """Return the true parallel offset of *b* at signed distance *d* as a Shapely LineString.

    Each of the *n+1* sample points is displaced by *d* mm along the unit
    normal at the corresponding *t* value.  Positive *d* moves left of the
    direction of travel (counter-clockwise normal convention).
    """

    def _offset_pt(i: int) -> tuple[float, float]:
        """Return the offset point at parameter *i/n* moved by *d* along the normal."""
        t = i / n
        p, nr = b.point_at_t(t), b.normal_at_t(t)
        return p.x + d * nr[0], p.y + d * nr[1]

    return _sg.LineString([_offset_pt(i) for i in range(n + 1)])


def _intersect_bezier_bezier(a: CubicBezier, b: CubicBezier, tol: float = 1e-12) -> list[Point]:
    """Return the intersection points between cubic Bézier curves *a* and *b*.

    Uses svgpathtools' Bézier-clipping algorithm.  Duplicate points closer than
    *tol* mm to each other are suppressed so that the result contains at most
    one representative per geometric crossing.

    Returns an empty list when the curves do not intersect.
    """
    intersections: list[Point] = []
    for t1, _t2 in a._svg().intersect(b._svg()):
        pt = a.point_at_t(t1)
        if not any(pt.distance_to(ex) < tol for ex in intersections):
            intersections.append(pt)
    return intersections


def fit_cubic_bezier(
    start: Point,
    end: Point,
    ref: Sequence[Point],
    t_params: Sequence[float] = (0.25, 0.50, 0.75),
) -> CubicBezier:
    """Fit a cubic Bézier from *start* to *end* passing near N reference points.

    The curve is constrained to have a **horizontal tangent at** *end* —
    i.e. ``p2.y = end.y`` — so it arrives level at the endpoint.  This
    matches the requirement for a sleeve cap curve that must be horizontal
    at the crown.

    The two free control points ``p1`` and ``p2`` are found by least-squares
    minimisation over the N parameter values given in *t_params*:

    * **y component** — N equations / 1 unknown (``p1.y``):
      solved as a weighted dot product using :func:`_bernstein_basis`.
    * **x component** — N equations / 2 unknowns (``p1.x``, ``p2.x``):
      solved via :func:`numpy.linalg.lstsq`.

    *ref* and *t_params* must have the same length (≥ 3).

    Args:
        start:    Start point of the curve (``p0``).
        end:      End point of the curve (``p3``).  The curve arrives here
                  with a horizontal tangent (``p2.y = end.y``).
        ref:      Reference points the curve should pass near, at the
                  parameters given by *t_params*.
        t_params: Parameter values at which *ref* is evaluated.
                  Defaults to ``(0.25, 0.50, 0.75)``.

    Returns:
        A :class:`CubicBezier` with ``p0=start``, ``p3=end``, and
        ``p2.y = end.y``.
    """
    crown_y = end.y

    b1_col: list[float] = []
    rhs_y: list[float] = []
    b1x_col: list[float] = []
    b2x_col: list[float] = []
    rhs_x: list[float] = []

    for t, r in zip(t_params, ref, strict=True):
        b0, b1, b2, b3 = _bernstein_basis(t)
        # Y: p2.y = p3.y = crown_y, so (b2+b3) is the combined known coefficient.
        rhs_y.append(r.y - b0 * start.y - (b2 + b3) * crown_y)
        b1_col.append(b1)
        # X: p1.x and p2.x are both free unknowns.
        rhs_x.append(r.x - b0 * start.x - b3 * end.x)
        b1x_col.append(b1)
        b2x_col.append(b2)

    # ── Y component: 1 unknown — closed-form least-squares (normal equation) ─
    b1_arr = np.array(b1_col)
    p1_y = float(np.dot(b1_arr, rhs_y) / np.dot(b1_arr, b1_arr))

    # ── X component: 2 unknowns — least-squares via numpy ────────────────────
    A = np.column_stack([b1x_col, b2x_col])
    p1_x, p2_x = np.linalg.lstsq(A, rhs_x, rcond=None)[0]

    return CubicBezier(start, Point(float(p1_x), p1_y), Point(float(p2_x), crown_y), end)


def fit_cubic_bezier_free(
    start: Point,
    end: Point,
    ref: Sequence[Point],
    t_params: Sequence[float],
) -> CubicBezier:
    """Fit a cubic Bézier from *start* to *end* with both control points free.

    Unlike :func:`fit_cubic_bezier`, there is **no** horizontal-tangent
    constraint at *end*: all four coordinates of ``p1`` and ``p2`` are
    determined simultaneously by least-squares over *ref* / *t_params*.

    When ``len(ref) == 2`` (exactly two reference points for two unknowns per
    dimension) the system is square and the curve passes **exactly** through
    both points.

    Args:
        start:    Start point (``p0``).
        end:      End point (``p3``).
        ref:      Reference points the curve should pass near (≥ 2).
        t_params: Parameter values matching each entry of *ref*.

    Returns:
        A :class:`CubicBezier` from *start* to *end*.
    """
    b1_col: list[float] = []
    b2_col: list[float] = []
    rhs_x: list[float] = []
    rhs_y: list[float] = []

    for t, r in zip(t_params, ref, strict=True):
        b0, b1, b2, b3 = _bernstein_basis(t)
        rhs_x.append(r.x - b0 * start.x - b3 * end.x)
        rhs_y.append(r.y - b0 * start.y - b3 * end.y)
        b1_col.append(b1)
        b2_col.append(b2)

    A = np.column_stack([b1_col, b2_col])
    p1_x, p2_x = np.linalg.lstsq(A, rhs_x, rcond=None)[0]
    p1_y, p2_y = np.linalg.lstsq(A, rhs_y, rcond=None)[0]

    return CubicBezier(
        start,
        Point(float(p1_x), float(p1_y)),
        Point(float(p2_x), float(p2_y)),
        end,
    )


class CubicBezier:
    """A 2-D cubic Bézier curve defined by four control points.

    The curve is parameterised by *t* ∈ [0, 1] using the standard cubic
    Bernstein basis::

        B(t) = (1-t)³·p0 + 3(1-t)²t·p1 + 3(1-t)t²·p2 + t³·p3

    ``p0`` and ``p3`` are the on-curve endpoints; ``p1`` and ``p2`` are the
    off-curve control points that pull the curve without lying on it.

    Attributes:
        p0: Start point (on-curve, ``t=0``).
        p1: First control point (off-curve).
        p2: Second control point (off-curve).
        p3: End point (on-curve, ``t=1``).
        name: Optional human-readable label.  Preserved through ``split``,
            ``translate``, and all copy-returning operations.
    """

    def __init__(self, p0: Point, p1: Point, p2: Point, p3: Point, name: str | None = None) -> None:
        """Initialise a cubic Bézier from four control points.

        Args:
            p0: Start point of the curve (``t=0``).
            p1: First off-curve control point.
            p2: Second off-curve control point.
            p3: End point of the curve (``t=1``).
            name: Optional label used in string representations and debugging.
        """
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.name = name

    def __str__(self) -> str:
        """Return a human-readable representation including all four control points."""
        return (
            f"CubicBezier(name={self.name}, p0={self.p0}, p1={self.p1}, p2={self.p2}, p3={self.p3})"
        )

    def __repr__(self) -> str:
        """Return the same string as :meth:`__str__`."""
        return self.__str__()

    @property
    def start(self) -> Point:
        """On-curve start point; alias for :attr:`p0`."""
        return self.p0

    @property
    def end(self) -> Point:
        """On-curve end point; alias for :attr:`p3`."""
        return self.p3

    def translate(self, dx: float, dy: float) -> CubicBezier:
        """Return a copy of this curve shifted by *(dx, dy)* mm.

        All four control points are translated; :attr:`name` is preserved.
        """
        return CubicBezier(
            self.p0.translate(dx, dy),
            self.p1.translate(dx, dy),
            self.p2.translate(dx, dy),
            self.p3.translate(dx, dy),
            name=self.name,
        )

    def set_name(self, name: str) -> CubicBezier:
        """Set :attr:`name` and return ``self`` for fluent chaining."""
        self.name = name
        return self

    def point_at_t(self, t: float) -> Point:
        """Evaluate the curve at parameter *t* ∈ [0, 1].

        Computed directly from the Bernstein basis via :func:`_bernstein_basis`
        — no library call.  ``t=0`` returns :attr:`p0`; ``t=1`` returns
        :attr:`p3`.
        """
        b0, b1, b2, b3 = _bernstein_basis(t)
        x = b0 * self.p0.x + b1 * self.p1.x + b2 * self.p2.x + b3 * self.p3.x
        y = b0 * self.p0.y + b1 * self.p1.y + b2 * self.p2.y + b3 * self.p3.y
        return Point(x, y)

    def _svg(self) -> _SvgCubicBezier:
        """Return an equivalent ``svgpathtools.CubicBezier`` for delegated maths.

        A new object is constructed on each call; there is no caching.  Call
        sites that need multiple operations on the same curve should store the
        result in a local variable rather than calling ``_svg()`` repeatedly.
        """
        return _SvgCubicBezier(
            complex(self.p0.x, self.p0.y),
            complex(self.p1.x, self.p1.y),
            complex(self.p2.x, self.p2.y),
            complex(self.p3.x, self.p3.y),
        )

    @property
    def length(self) -> float:
        """Arc length in mm, computed via Gauss-Legendre quadrature (svgpathtools)."""
        return float(self._svg().length())

    def tangent_at_t(self, t: float) -> np.ndarray:
        """Return the (unnormalised) tangent vector B'(t) at parameter *t*.

        The vector points in the direction of travel and has magnitude
        proportional to the curve speed at *t*.  Use :meth:`normal_at_t` for
        the perpendicular unit vector.

        Returns:
            A length-2 NumPy array ``[dx, dy]`` in mm/unit-t.
        """
        d = self._svg().derivative(t)
        return np.array([d.real, d.imag])

    def normal_at_t(self, t: float) -> np.ndarray:
        """Return the unit normal vector at parameter *t*.

        The normal is rotated 90° counter-clockwise from the tangent, i.e. it
        points *left* of the direction of travel.

        Falls back gracefully when the tangent is degenerate (zero-length
        derivative):

        1. Try ``svg.normal(t)`` directly.
        2. If that raises ``ValueError``, nudge *t* by ±1e-4 toward the
           nearer interior and retry.
        3. If still degenerate, use a finite-difference approximation over a
           ±1e-4 window.

        Returns:
            A length-2 NumPy array ``[nx, ny]`` with ``‖n‖ = 1``.
        """
        svg = self._svg()
        try:
            n = svg.normal(t)
            return np.array([n.real, n.imag])
        except ValueError:  # pragma: no cover
            eps = 1e-4
            fallback_t = max(eps, t - eps) if t > 0.5 else min(1.0 - eps, t + eps)
            try:
                n = svg.normal(fallback_t)
                return np.array([n.real, n.imag])
            except ValueError:
                dt = 1e-4
                pt_lo = self.point_at_t(max(0.0, t - dt))
                pt_hi = self.point_at_t(min(1.0, t + dt))
                dx, dy = pt_hi.x - pt_lo.x, pt_hi.y - pt_lo.y
                length = (dx**2 + dy**2) ** 0.5 or 1.0
                return np.array([-dy / length, dx / length])

    def point_at_length(self, arc_length: float) -> Point:
        """Return the point at *arc_length* mm from :attr:`p0` along the curve.

        Args:
            arc_length: Distance in mm, measured along the curve.  Must satisfy
                ``0 ≤ arc_length ≤ self.length``.

        Returns:
            The :class:`Point` at the requested arc length.

        Raises:
            ValueError: If *arc_length* is negative or exceeds the total curve
                length (a 1 nm tolerance is allowed for floating-point noise).
        """
        svg = self._svg()
        total = float(svg.length())
        if arc_length < 0 or arc_length > total + 1e-9:
            raise ValueError(f"arc_length {arc_length:.4f} is outside [0, {total:.4f}]")
        return self.point_at_t(svg.ilength(arc_length))

    def point_along_from(self, point: Point, arc_length: float) -> Point:
        """Return the point *arc_length* mm further along the curve from *point*.

        *point* is snapped to the nearest location on the curve via
        :func:`_bezier_closest_t`, so it need not lie exactly on the curve.

        Args:
            point: Reference location on (or near) the curve.
            arc_length: Additional distance to travel in mm.  May be negative
                to travel backwards.
        """
        svg = self._svg()
        t0 = _bezier_closest_t(svg, complex(point.x, point.y))
        pos = float(svg.length(t1=t0))
        return self.point_at_length(pos + arc_length)

    def arc_length_from_end(self, point: Point) -> float:
        """Return the arc distance from the closest on-curve location to *point* to the end (p3).

        Snaps *point* to the nearest location on the curve, then returns
        ``self.length − arc_distance_from_p0``.  Useful when you know a notch
        position relative to one end of a curve and need to mirror it onto a
        second curve measured from the *other* end.

        Args:
            point: Reference point (need not lie exactly on the curve).

        Returns:
            Arc distance in mm from the snapped location to :attr:`p3`.
        """
        svg = self._svg()
        t0 = _bezier_closest_t(svg, complex(point.x, point.y))
        arc_from_start = float(svg.length(t1=t0))
        return self.length - arc_from_start

    def split(self, t: float) -> tuple[CubicBezier, CubicBezier]:
        """Split the curve at *t* ∈ (0, 1) and return ``(left, right)``.

        Uses de Casteljau subdivision (delegated to svgpathtools).  Both
        sub-curves inherit :attr:`name` from this curve.
        """
        left, right = self._svg().split(t)
        return (
            CubicBezier(
                Point(left.start.real, left.start.imag),
                Point(left.control1.real, left.control1.imag),
                Point(left.control2.real, left.control2.imag),
                Point(left.end.real, left.end.imag),
                name=self.name,
            ),
            CubicBezier(
                Point(right.start.real, right.start.imag),
                Point(right.control1.real, right.control1.imag),
                Point(right.control2.real, right.control2.imag),
                Point(right.end.real, right.end.imag),
                name=self.name,
            ),
        )

    def split_at_points(
        self,
        points: list[Point],
        tolerance: float = 0.5,
    ) -> list[CubicBezier]:
        """Split the curve at each point in *points* and return the sub-curves in order.

        Each point is projected onto the curve via :func:`_bezier_closest_t`.
        Points that project within *tolerance* mm of either endpoint are treated
        as outside the curve interior and ignored.  Duplicate projections (two
        points mapping to the same *t*) are deduplicated by the sort; only one
        split is performed at each unique *t*.

        Args:
            points: Points that lie on (or very near) the curve.
            tolerance: Points whose projected *t* falls within
                ``tolerance / length`` of 0 or 1 are discarded.  Defaults to
                0.5 mm.

        Returns:
            An ordered list of sub-curves.  Returns ``[self-copy]`` when
            *points* is empty or all points fall outside the interior.
        """
        total_len = self.length
        if total_len == 0.0:
            return [CubicBezier(self.p0, self.p1, self.p2, self.p3, name=self.name)]

        svg = self._svg()
        eps = tolerance / total_len
        ts: list[float] = sorted(_bezier_closest_t(svg, complex(pt.x, pt.y)) for pt in points)
        breakpoints: list[float] = [t for t in ts if eps < t < 1.0 - eps]

        if not breakpoints:
            return [CubicBezier(self.p0, self.p1, self.p2, self.p3, name=self.name)]

        return _split_at_ts(
            CubicBezier(self.p0, self.p1, self.p2, self.p3, name=self.name), breakpoints
        )

    def bounding_box(self) -> tuple[Point, Point]:
        """Return the tight axis-aligned bounding box of the curve.

        Delegates to ``svgpathtools.CubicBezier.bbox()``, which finds the
        exact extrema by solving B'(t) = 0 analytically.  The result reflects
        the actual curve extent, not the convex hull of the control points.

        Returns:
            ``(min_corner, max_corner)`` where *min_corner* is
            ``Point(xmin, ymin)`` and *max_corner* is ``Point(xmax, ymax)``.
        """
        xmin, xmax, ymin, ymax = self._svg().bbox()
        return Point(xmin, ymin), Point(xmax, ymax)

    def point_perpendicular(self, distance: float, t: float) -> Point:
        """Return a point offset perpendicularly from the curve at parameter *t*.

        Args:
            distance: Offset in mm.  Positive moves left of travel (the
                counter-clockwise normal direction); negative moves right.
            t: Curve parameter ∈ [0, 1] at which to apply the offset.
        """
        pt = self.point_at_t(t)
        nor = self.normal_at_t(t)
        return Point(pt.x + distance * nor[0], pt.y + distance * nor[1])

    def contains_point(self, point: Point, tolerance: float = 0.01) -> bool:
        """Return ``True`` if *point* is within *tolerance* mm of the curve.

        The check is approximate: the curve is discretised into 64 segments
        and the Shapely distance to the resulting polyline is tested.  Points
        very close to the true curve but between sample locations may read as
        outside when *tolerance* is very tight.
        """
        ls = _bezier_shapely(self)
        return bool(ls.distance(_sg.Point(point.x, point.y)) <= tolerance)

    def offset(
        self,
        distance: float,
        center: Point | None = None,
        hausdorff_limit: float = 1.5,
    ) -> CubicBezier:
        """Return a single-Bézier approximation of the parallel offset curve.

        Args:
            distance: Signed offset in mm.  Positive moves left of travel.
            center: When given, the sign of *distance* is overridden so the
                offset moves *away* from *center*.
            hausdorff_limit: Quality threshold as a multiple of
                ``abs(distance)``.  If the hodograph approximation's Hausdorff
                error exceeds this, the curve is bisected and re-approximated.
                Pass ``math.inf`` to skip the quality check.

        Delegates to :func:`~sewpat.geometry._bezier_offset.bezier_offset`.
        """
        from ._bezier_offset import bezier_offset  # local import avoids circular dep

        return bezier_offset(self, distance, center=center, hausdorff_limit=hausdorff_limit)

    def offset_error(self, distance: float, center: Point | None = None) -> float:
        """Return the Hausdorff error (mm) between the hodograph approximation and the true offset.

        Args:
            distance: Signed offset in mm.
            center: When given, determines the sign of *distance* (see
                :meth:`offset`).

        Returns:
            Non-negative Hausdorff error in mm.

        Delegates to :func:`~sewpat.geometry._bezier_offset.bezier_offset_error`.
        """
        from ._bezier_offset import bezier_offset_error

        return bezier_offset_error(self, distance, center=center)

    def offset_adaptive(
        self,
        distance: float,
        center: Point | None = None,
        eps: float = 0.1,
        _depth: int = 0,
        _max_depth: int = 8,
    ) -> list[CubicBezier]:
        """Return the offset as a list of Béziers with Hausdorff error < *eps* mm.

        The curve is recursively bisected at ``t=0.5`` until every segment's
        hodograph approximation is within *eps* mm of the true parallel offset,
        or the recursion reaches *_max_depth* levels (default 8, giving at most
        256 output segments).

        Args:
            distance: Signed offset in mm.  Positive moves left of travel.
            center: When given, determines the sign of *distance* (see
                :meth:`offset`).
            eps: Maximum allowed Hausdorff error per segment in mm.
            _depth: Current recursion depth — **do not set manually**.
            _max_depth: Hard recursion cap — **do not set manually**.

        Returns:
            An ordered list of :class:`CubicBezier` segments whose union
            approximates the true parallel offset within *eps* mm.

        Delegates to :func:`~sewpat.geometry._bezier_offset.bezier_offset_adaptive`.
        """
        from ._bezier_offset import bezier_offset_adaptive

        return bezier_offset_adaptive(
            self,
            distance,
            center=center,
            eps=eps,
            _depth=_depth,
            _max_depth=_max_depth,
        )


# ---------------------------------------------------------------------------
# Split-Bézier seam helper
# ---------------------------------------------------------------------------


def split_bezier_seam_fn(
    left_curve: CubicBezier,
    right_curve: CubicBezier,
    total_length: float,
) -> Callable[[float], Point]:
    """Return a callable that maps a straight-seam projection onto a split-Bézier seam.

    The two sub-curves together span a straight reference segment of
    *total_length* mm.  The resulting callable converts a linear arc-length
    projection along that straight segment to the corresponding point on the
    shaped Bézier seam, splitting at the midpoint (``t = 0.5``):

    * ``proj ∈ [0, total_length / 2]``  →  ``left_curve.point_at_t(2·t)``
    * ``proj ∈ (total_length / 2, …]``  →  ``right_curve.point_at_t(2·t − 1)``

    This mapping is exact when each sub-curve was fitted with its two interior
    reference points placed at ``t = 1/3`` and ``t = 2/3``
    (as produced by :func:`fit_cubic_bezier_free` with
    ``t_params=(1/3, 2/3)``).  The returned callable is suitable for passing
    as *curved_seam_fn* to :meth:`~sewpat.pleat.Pleat.build_along_seam`.

    Args:
        left_curve:   Left-half Bézier (seam-left endpoint → split midpoint).
        right_curve:  Right-half Bézier (split midpoint → seam-right endpoint).
        total_length: Arc-length of the straight reference segment in mm.

    Returns:
        A callable ``fn(proj: float) -> Point``.
    """

    def _fn(proj: float) -> Point:
        t = max(0.0, min(1.0, proj / total_length))
        return left_curve.point_at_t(2.0 * t) if t <= 0.5 else right_curve.point_at_t(2.0 * t - 1.0)

    return _fn
