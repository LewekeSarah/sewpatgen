"""Offset subsystem for CubicBezier curves.

This module implements the three public offset operations that were previously
methods on ``CubicBezier``.  They are exposed here as module-level functions so
that the curve class itself stays focused on curve geometry, while the
numerically-intensive approximation logic lives in one dedicated place.

Public API
----------
bezier_offset          -- hodograph-based single-Bézier approximation with
                          split-and-stitch Hausdorff quality guard
bezier_offset_error    -- Hausdorff distance between the approximation and the
                          true parallel offset
bezier_offset_adaptive -- recursive adaptive split until Hausdorff error < eps
"""

import math

import numpy as np

from ._bezier import CubicBezier, _bezier_shapely, _true_offset_ls
from ._primitives import Point


def _resolve_d(curve: CubicBezier, distance: float, center: Point | None) -> float:
    """Return the signed offset distance, resolving direction from *center* if given.

    When *center* is ``None``, *distance* is returned unchanged.  Otherwise the
    sign is chosen so that the offset moves *away* from *center*: the midpoint
    normal at ``t=0.5`` is compared to the vector from *center* to the midpoint,
    and ``abs(distance)`` is negated if they point in opposite directions.

    Args:
        curve: The source :class:`CubicBezier`.
        distance: Requested signed offset in mm.  When *center* is provided
            only the magnitude is used; the sign is determined geometrically.
        center: Optional reference point.  When given the sign of *distance*
            is overridden so the offset moves away from *center*.

    Returns:
        Signed offset distance in mm.
    """
    if center is None:
        return distance
    mid = curve.point_at_t(0.5)
    n_mid = curve.normal_at_t(0.5)
    sign = 1.0 if np.dot(n_mid, mid.coords - center.coords) >= 0 else -1.0
    return sign * abs(distance)


def _hodograph_offset(curve: CubicBezier, d: float) -> CubicBezier:
    """Return the hodograph approximation of the parallel offset of *curve* by *d* mm.

    Each of the four control points is shifted by ``d`` along the unit normal
    at the corresponding canonical parameter value:

    * ``p0`` → ``t = 0``
    * ``p1`` → ``t = 1/3``
    * ``p2`` → ``t = 2/3``
    * ``p3`` → ``t = 1``

    This is an approximation: the true offset of a cubic Bézier is not itself
    a cubic Bézier.  Use :func:`bezier_offset_error` to measure the error and
    :func:`bezier_offset_adaptive` when the error must stay within a budget.

    Args:
        curve: The source :class:`CubicBezier`.
        d: Signed offset in mm.

    Returns:
        A new :class:`CubicBezier` with :attr:`~CubicBezier.name` inherited
        from *curve*.
    """

    def _shifted(pt: Point, t: float) -> Point:
        """Shift *pt* by distance *d* along the curve normal at parameter *t*."""
        n = curve.normal_at_t(t)
        return Point(pt.x + d * n[0], pt.y + d * n[1])

    return CubicBezier(
        _shifted(curve.p0, 0.0),
        _shifted(curve.p1, 1 / 3),
        _shifted(curve.p2, 2 / 3),
        _shifted(curve.p3, 1.0),
        name=curve.name,
    )


def bezier_offset(
    curve: CubicBezier,
    distance: float,
    center: Point | None = None,
    hausdorff_limit: float = 1.5,
) -> CubicBezier:
    """Return a single-Bézier approximation of the parallel offset curve.

    The result is the hodograph approximation (see :func:`_hodograph_offset`).
    When the Hausdorff distance between this approximation and the true
    parallel offset exceeds ``hausdorff_limit * abs(distance)``, the curve is
    split at ``t=0.5`` and a better composite approximation is stitched into a
    single Bézier by borrowing the *inner* control points from each half:

    * ``p0`` — offset start of the left half
    * ``p1`` — second control point of the left-half offset (inner handle)
    * ``p2`` — first control point of the right-half offset (inner handle)
    * ``p3`` — offset end of the right half

    Using the inner handles (rather than the shared midpoint) preserves the
    G1 tangent direction at both ends of the stitched curve.

    Args:
        curve: The source :class:`CubicBezier`.
        distance: Signed offset in mm.  Positive moves left of travel.
            When *center* is provided the sign of this value is ignored;
            only the magnitude is used.
        center: Optional reference point.  When given, the sign of *distance*
            is overridden so the offset moves *away* from *center*.
        hausdorff_limit: Quality threshold as a multiplier on ``abs(distance)``.
            Pass ``math.inf`` to skip the quality check entirely and always
            return the raw hodograph approximation.

    Returns:
        An offset :class:`CubicBezier`.
    """
    d = _resolve_d(curve, distance, center)
    approx = _hodograph_offset(curve, d)

    if abs(d) > 1e-9 and math.isfinite(hausdorff_limit):
        ls_true = _true_offset_ls(curve, d)
        ls_off = _bezier_shapely(approx)
        if ls_true.hausdorff_distance(ls_off) > hausdorff_limit * abs(d):
            left, right = curve.split(0.5)
            left_off = _hodograph_offset(left, d)
            right_off = _hodograph_offset(right, d)
            # Stitch using the inner control points of each half-offset to
            # preserve the G1 tangent direction at both endpoints.
            return CubicBezier(
                left_off.p0,
                left_off.p2,
                right_off.p1,
                right_off.p3,
                name=curve.name,
            )

    return approx


def bezier_offset_error(
    curve: CubicBezier,
    distance: float,
    center: Point | None = None,
) -> float:
    """Return the Hausdorff distance (mm) between the hodograph and the true offset.

    The true parallel offset is sampled at 64 equidistant *t* values via
    :func:`_true_offset_ls` and compared to the raw hodograph approximation
    (``hausdorff_limit=math.inf`` — no quality fallback).

    Args:
        curve: The source :class:`CubicBezier`.
        distance: Signed offset in mm.  When *center* is provided the sign of
            this value is ignored; only the magnitude is used.
        center: Optional reference point for sign determination.

    Returns:
        Non-negative Hausdorff distance in mm.  Returns ``0.0`` when
        *distance* is zero.
    """
    d = _resolve_d(curve, distance, center)
    approx = bezier_offset(curve, d, center=None, hausdorff_limit=math.inf)
    ls_true = _true_offset_ls(curve, d)
    ls_off = _bezier_shapely(approx)
    return float(ls_true.hausdorff_distance(ls_off))


def bezier_offset_adaptive(
    curve: CubicBezier,
    distance: float,
    center: Point | None = None,
    eps: float = 0.1,
    _depth: int = 0,
    _max_depth: int = 8,
) -> list[CubicBezier]:
    """Return the offset as a list of Béziers with Hausdorff error < *eps* mm.

    The curve is recursively bisected at ``t=0.5`` until every sub-arc's
    hodograph approximation is within *eps* mm of the true parallel offset, or
    the recursion reaches *_max_depth* levels.  When the depth cap is hit the
    best available hodograph approximation is returned for that segment
    regardless of its error, so callers that require a strict accuracy
    guarantee should not lower *_max_depth*.

    Args:
        curve: The source :class:`CubicBezier`.
        distance: Signed offset in mm.  Positive moves left of travel.
            When *center* is provided the sign of this value is ignored;
            only the magnitude is used.
        center: Optional reference point for sign determination.  Applied once
            at the top level; sub-calls pass ``center=None`` to reuse the
            already-resolved signed *d*.
        eps: Maximum allowed Hausdorff error per segment in mm.
        _depth: Current recursion depth — **do not set manually**.
        _max_depth: Hard recursion cap (default 8 → at most 256 output
            segments) — **do not set manually**.

    Returns:
        An ordered list of :class:`CubicBezier` segments whose union
        approximates the true parallel offset within *eps* mm (subject to the
        depth cap).
    """
    d = _resolve_d(curve, distance, center)
    approx = _hodograph_offset(curve, d)

    if _depth >= _max_depth:
        return [approx]

    ls_true = _true_offset_ls(curve, d)
    ls_off = _bezier_shapely(approx)
    if ls_true.hausdorff_distance(ls_off) <= eps:
        return [approx]

    left, right = curve.split(0.5)
    left_segs = bezier_offset_adaptive(
        left, d, center=None, eps=eps, _depth=_depth + 1, _max_depth=_max_depth
    )
    right_segs = bezier_offset_adaptive(
        right, d, center=None, eps=eps, _depth=_depth + 1, _max_depth=_max_depth
    )
    # Snap the join point: the end of the left chain and the start of the right
    # chain must coincide.  At inflection points the hodograph normal flips sign,
    # so the two half-offsets may land at different positions.  We resolve the
    # gap by moving both endpoints to their midpoint.
    join = left_segs[-1].p3
    start = right_segs[0].p0
    if join.distance_to(start) > 1e-9:
        mid = Point((join.x + start.x) * 0.5, (join.y + start.y) * 0.5)
        last = left_segs[-1]
        left_segs[-1] = CubicBezier(last.p0, last.p1, last.p2, mid, name=last.name)
        first = right_segs[0]
        right_segs[0] = CubicBezier(mid, first.p1, first.p2, first.p3, name=first.name)
    return left_segs + right_segs
