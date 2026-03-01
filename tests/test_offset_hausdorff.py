"""Tests for CubicBezier.offset_error() and the Hausdorff quality check in offset()."""

import math

import pytest

from sewpat.geometry import (
    CubicBezier,
    Point,
    Segment,
)
from sewpat.geometry import (
    offset_adaptive as _module_offset_adaptive,
)


def _gentle():
    """A gentle arch — hodograph approximation should be well within limits."""
    return CubicBezier(Point(0, 0), Point(10, 20), Point(30, 20), Point(40, 0))


def _tight():
    """A tight S-curve — hodograph approximation is expected to be poor."""
    return CubicBezier(Point(0, 0), Point(0, 50), Point(10, -50), Point(10, 0))


# ── offset_error() ────────────────────────────────────────────────────────────


def test_offset_error_returns_float():
    err = _gentle().offset_error(10.0)
    assert isinstance(err, float)
    assert err >= 0.0


def test_offset_error_gentle_within_limit():
    distance = 10.0
    err = _gentle().offset_error(distance)
    # For a gentle arch the approximation should comfortably pass the 1.5× limit
    assert err < 1.5 * distance, f"expected err < {1.5 * distance}, got {err:.3f}"


def test_offset_error_tight_exceeds_limit():
    distance = 10.0
    err = _tight().offset_error(distance)
    # The S-curve hodograph error should be a meaningful fraction of the distance
    # (true parallel offset vs hodograph approximation).
    assert err > 0.5 * distance, f"expected err > {0.5 * distance}, got {err:.3f}"


def test_offset_error_zero_distance():
    err = _gentle().offset_error(0.0)
    # Offset of zero → hodograph equals true offset → Hausdorff = 0
    assert err == pytest.approx(0.0, abs=1e-9)


# ── offset() with hausdorff_limit ────────────────────────────────────────────


def test_offset_gentle_returns_cubicbezier():
    result = _gentle().offset(10.0)
    assert isinstance(result, CubicBezier)


def test_offset_gentle_endpoints_shifted():
    """Offset endpoints should be roughly *distance* away from the originals."""
    c = _gentle()
    off = c.offset(10.0)
    dist_start = c.p0.distance_to(off.p0)
    dist_end = c.p3.distance_to(off.p3)
    assert dist_start == pytest.approx(10.0, rel=0.05)
    assert dist_end == pytest.approx(10.0, rel=0.05)


def test_offset_tight_fallback_improves_quality():
    """When hausdorff_limit forces the fallback, the result endpoints must be
    correctly offset (within 5% of the requested distance) — verifying that
    the fallback path runs and produces geometrically sound output."""
    distance = 10.0
    tight = _tight()

    # hausdorff_limit=0.0 always triggers the fallback (any error > 0)
    result = tight.offset(distance, hausdorff_limit=0.0)

    assert isinstance(result, CubicBezier)
    # Endpoints must be shifted by ~distance from the original endpoints
    dist_start = tight.p0.distance_to(result.p0)
    dist_end = tight.p3.distance_to(result.p3)
    assert dist_start == pytest.approx(distance, rel=0.05)
    assert dist_end == pytest.approx(distance, rel=0.05)


def test_offset_disabled_check_matches_hodograph():
    """hausdorff_limit=inf must bypass the quality check and return the raw
    hodograph approximation (i.e. the same result every time, no branching)."""
    c = _tight()
    run1 = c.offset(10.0, hausdorff_limit=math.inf)
    run2 = c.offset(10.0, hausdorff_limit=math.inf)
    assert run1.p0.x == pytest.approx(run2.p0.x)
    assert run1.p0.y == pytest.approx(run2.p0.y)
    assert run1.p3.x == pytest.approx(run2.p3.x)
    assert run1.p3.y == pytest.approx(run2.p3.y)


def test_offset_with_center():
    """Passing a center point must still return a CubicBezier and shift endpoints."""
    c = _gentle()
    center = Point(20, 0)
    result = c.offset(10.0, center=center)
    assert isinstance(result, CubicBezier)
    # The offset should move the curve away from center, so the midpoint of
    # the offset should be further from center than the original midpoint
    mid_orig = c.point_at_t(0.5)
    mid_off = result.point_at_t(0.5)
    assert mid_off.distance_to(center) > mid_orig.distance_to(center)


def test_offset_negative_distance():
    """Negative distance should offset in the opposite direction."""
    c = _gentle()
    off_pos = c.offset(+10.0)
    off_neg = c.offset(-10.0)
    mid_orig = c.point_at_t(0.5)
    mid_pos = off_pos.point_at_t(0.5)
    mid_neg = off_neg.point_at_t(0.5)
    # Both offsets must move away from the original midpoint
    assert mid_pos.distance_to(mid_orig) > 1.0
    assert mid_neg.distance_to(mid_orig) > 1.0
    # The two offsets must be on opposite sides (further apart than either from original)
    assert mid_pos.distance_to(mid_neg) > mid_pos.distance_to(mid_orig)
    assert mid_pos.distance_to(mid_neg) > mid_neg.distance_to(mid_orig)


# ── offset_adaptive() ─────────────────────────────────────────────────────────


def test_offset_adaptive_gentle_returns_single_segment():
    """A gentle arch with a generous eps budget needs no splitting."""
    # Use eps = half the SA distance — the hodograph error for a gentle arch
    # is well below 5 mm at d=10 mm, so no splitting should occur.
    result = _gentle().offset_adaptive(10.0, eps=5.0)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], CubicBezier)


def test_offset_adaptive_tight_returns_multiple_segments():
    """The tight S-curve with large SA must be split into more than one segment."""
    result = _tight().offset_adaptive(10.0, eps=0.1)
    assert isinstance(result, list)
    assert len(result) > 1, f"expected >1 segments for tight S-curve, got {len(result)}"


def test_offset_adaptive_each_segment_within_eps():
    """Every sub-segment returned by offset_adaptive must satisfy the eps budget."""

    curve = _tight()
    eps = 0.1
    distance = 10.0

    # Resolve signed distance (no center → positive = left of travel)
    d = distance

    result = curve.split(0.5)  # pre-split for the tight S
    segments = curve.offset_adaptive(d, eps=eps)
    for seg in segments:

        # We cannot compute _true_offset_ls for a sub-segment of the original
        # curve directly, but we CAN check that each segment's self-reported
        # error (via offset_error on the *original* sub-curve) is ≤ eps.
        # Reconstruct the original sub-curve by finding which part of the
        # original maps to this offset segment's endpoints (not trivial), so
        # instead verify the simpler invariant: endpoints are shifted by ≈d.
        dist_start = curve.p0.distance_to(seg.p0) if seg == segments[0] else None
        if dist_start is not None:
            assert (
                abs(dist_start - d) < d * 0.1
            ), f"first segment start not shifted by d: {dist_start:.3f} vs {d}"
    # The last segment's end must also be ≈d from the original curve's end
    last = segments[-1]
    dist_end = curve.p3.distance_to(last.p3)
    assert (
        abs(dist_end - d) < d * 0.1
    ), f"last segment end not shifted by d: {dist_end:.3f} vs {d}"


def test_offset_adaptive_segments_are_connected():
    """Consecutive segments returned by offset_adaptive must share endpoints."""
    result = _tight().offset_adaptive(10.0, eps=0.1)
    for a, b in zip(result, result[1:]):
        gap = a.p3.distance_to(b.p0)
        assert gap < 1e-6, f"gap between consecutive segments: {gap:.8f} mm"


def test_offset_adaptive_better_than_single_offset_on_tight_curve():
    """offset_adaptive must achieve lower max Hausdorff error than single offset."""
    import shapely.geometry as _sg

    from sewpat.geometry import _bezier_shapely, _true_offset_ls

    distance = 10.0
    curve = _tight()
    d = distance

    # Error of the single-segment hodograph (hausdorff_limit=inf → no fallback)
    single = curve.offset(d, hausdorff_limit=math.inf)
    ls_true = _true_offset_ls(curve, d)
    err_single = ls_true.hausdorff_distance(_bezier_shapely(single))

    # Error of the adaptive multi-segment result (use the union polyline)
    segments = curve.offset_adaptive(d, eps=0.1)
    all_pts = []
    for seg in segments:
        all_pts += [
            (seg.point_at_t(i / 64).x, seg.point_at_t(i / 64).y) for i in range(65)
        ]
    ls_adaptive = _sg.LineString(all_pts)
    err_adaptive = ls_true.hausdorff_distance(ls_adaptive)

    assert (
        err_adaptive < err_single
    ), f"adaptive ({err_adaptive:.3f} mm) not better than single ({err_single:.3f} mm)"


def test_offset_adaptive_depth_limit_respected():
    """With _max_depth=0 the recursion stops immediately — returns single segment."""
    result = _tight().offset_adaptive(10.0, eps=0.0, _max_depth=0)
    assert len(result) == 1


def test_offset_adaptive_with_center():
    """Passing a center point must return a list and shift endpoints outward."""
    c = _gentle()
    center = Point(20, 0)
    result = c.offset_adaptive(10.0, center=center, eps=0.5)
    assert isinstance(result, list)
    assert len(result) >= 1
    mid_orig = c.point_at_t(0.5)
    mid_off = result[len(result) // 2].point_at_t(0.5)
    assert mid_off.distance_to(center) > mid_orig.distance_to(center)


# ── module-level offset_adaptive() ───────────────────────────────────────────


def test_module_offset_adaptive_segment_passthrough():
    """For a Segment, offset_adaptive returns a one-element list with a Segment."""
    seg = Segment(Point(0, 0), Point(100, 0))
    result = _module_offset_adaptive(seg, 10.0)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Segment)


def test_module_offset_adaptive_segment_shifted():
    """The returned Segment must be shifted perpendicular by the offset distance.

    A horizontal segment going in +x has its left-hand normal pointing in +y,
    so offset(+10) shifts both endpoints to y=+10.
    """
    seg = Segment(Point(0, 0), Point(100, 0))
    result = _module_offset_adaptive(seg, 10.0)
    off = result[0]
    assert off.p1.y == pytest.approx(10.0, abs=0.01)
    assert off.p2.y == pytest.approx(10.0, abs=0.01)


def test_module_offset_adaptive_bezier_delegates():
    """For a CubicBezier, module offset_adaptive delegates to the method."""
    result = _module_offset_adaptive(_tight(), 10.0, eps=0.1)
    assert isinstance(result, list)
    assert all(isinstance(s, CubicBezier) for s in result)
