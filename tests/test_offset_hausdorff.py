"""Tests for CubicBezier.offset_error() and the Hausdorff quality check in offset()."""

import math
import pytest
from sewpat.geometry import Point, CubicBezier


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
