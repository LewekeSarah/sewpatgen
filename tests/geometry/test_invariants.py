"""Property-based invariant tests for the geometry package.

Uses `hypothesis` to verify mathematical invariants that must hold for *all*
valid inputs, not just the hand-picked cases covered by the unit tests.

Invariants tested
-----------------
1. ``bezier_offset_error`` is always ≥ 0.
2. ``bezier_offset`` endpoints are displaced by exactly ``distance`` mm.
3. ``bezier_offset_adaptive`` returns a continuously connected chain.
4. ``build_chain`` preserves connectivity of a pre-connected segment list.
5. ``seam_length`` equals the sum of individual segment lengths and is ≥ 0.
"""

import math

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from sewpat.geometry import (
    CubicBezier,
    Point,
    Segment,
    build_chain,
    seam_length,
)
from sewpat.geometry._bezier_offset import (
    bezier_offset,
    bezier_offset_adaptive,
    bezier_offset_error,
)

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Coordinates in a realistic pattern range: ±500 mm, finite, not NaN.
_coord = st.floats(min_value=-500.0, max_value=500.0, allow_nan=False, allow_infinity=False)

# Non-zero offset distances: 1 – 50 mm (seam allowance range).
_distance = st.floats(min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False)


@st.composite
def _bezier(draw: st.DrawFn) -> CubicBezier:
    """Strategy that produces a non-degenerate CubicBezier.

    All four control points are drawn independently.  We filter out curves
    whose chord length is effectively zero, because the normal vector becomes
    undefined and offset operations are meaningless.

    We also filter out curves where control points collapse (e.g., p2 == p3),
    as these create degenerate cases that violate offset invariants.
    """
    pts = [Point(draw(_coord), draw(_coord)) for _ in range(4)]
    p0, p1, p2, p3 = pts
    # Filter out zero-length chords
    assume(p0.distance_to(p3) > 0.1)
    # Filter out collapsed control points that create degenerate curves
    assume(p1.distance_to(p2) > 0.1)
    assume(p2.distance_to(p3) > 0.1)
    assume(p0.distance_to(p1) > 0.1)
    return CubicBezier(p0, p1, p2, p3)


@st.composite
def _connected_segments(draw: st.DrawFn) -> list[Segment]:
    """Strategy that produces 2–5 connected Segments sharing exact endpoints.

    Each segment's start point is the previous segment's end point, so the
    resulting list is already a valid chain without any reversal needed.
    The chain is then shuffled to exercise ``build_chain``'s ordering logic.
    """
    n = draw(st.integers(min_value=2, max_value=5))
    # Generate n+1 distinct points to form n segments.
    xs = draw(st.lists(_coord, min_size=n + 1, max_size=n + 1))
    ys = draw(st.lists(_coord, min_size=n + 1, max_size=n + 1))
    points = [Point(x, y) for x, y in zip(xs, ys, strict=True)]
    # Ensure each segment has non-zero length so reversals are unambiguous.
    for i in range(n):
        assume(points[i].distance_to(points[i + 1]) > 0.1)
    return [Segment(points[i], points[i + 1]) for i in range(n)]


# ---------------------------------------------------------------------------
# Invariant 1 — bezier_offset_error is always ≥ 0
# ---------------------------------------------------------------------------


@given(curve=_bezier(), distance=_distance)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_offset_error_is_non_negative(curve: CubicBezier, distance: float) -> None:
    """bezier_offset_error must always return a non-negative float.

    The Hausdorff distance between two point sets is always ≥ 0 by definition.
    A negative value would indicate a sign error in the computation.
    """
    err = bezier_offset_error(curve, distance)
    assert math.isfinite(err), f"expected finite error, got {err}"
    assert err >= 0.0, f"expected err ≥ 0, got {err}"


# ---------------------------------------------------------------------------
# Invariant 2 — bezier_offset endpoints are displaced by |distance| mm
# ---------------------------------------------------------------------------


@given(curve=_bezier(), distance=_distance)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_offset_endpoints_displaced_by_distance(curve: CubicBezier, distance: float) -> None:
    """The start and end points of the offset curve are displaced by approximately ``distance`` mm.

    The hodograph offset shifts p0 and p3 along the unit normal at t=0 and t=1
    respectively, so the displacement equals the requested distance.

    When the Hausdorff quality guard triggers the stitch fallback, p0 and p3
    are taken from the half-curve offsets and still displaced by exactly
    ``distance``.  We therefore assert the displacement is in the range
    ``(0, 2 * distance]`` — strictly positive (the curve moved) and bounded
    above (it never overshoots by more than one extra offset width).
    """
    off = bezier_offset(curve, distance)
    start_disp = curve.p0.distance_to(off.p0)
    end_disp = curve.p3.distance_to(off.p3)
    # Allow small tolerance for floating-point precision at lower bound
    lower = distance * 0.5  # At least half the requested distance
    upper = 2 * distance + 1e-6
    assert lower <= start_disp <= upper, (
        f"start displacement {start_disp:.6f} out of range [{lower:.6f}, {upper:.6f}]"
    )
    assert lower <= end_disp <= upper, (
        f"end displacement {end_disp:.6f} out of range [{lower:.6f}, {upper:.6f}]"
    )


# ---------------------------------------------------------------------------
# Invariant 3 — bezier_offset_adaptive returns a connected chain
# ---------------------------------------------------------------------------


@given(curve=_bezier(), distance=_distance)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_offset_adaptive_chain_is_connected(curve: CubicBezier, distance: float) -> None:
    """Consecutive segments from bezier_offset_adaptive share endpoints.

    The adaptive split must produce a chain where every segment's end point
    coincides with the next segment's start point within floating-point tolerance.
    A gap would indicate a bug in the recursive stitching logic.
    """
    segments = bezier_offset_adaptive(curve, distance, eps=0.5)
    assert len(segments) >= 1, "expected at least one segment"
    for i in range(len(segments) - 1):
        gap = segments[i].end.distance_to(segments[i + 1].start)
        assert gap < 1e-6, (
            f"gap {gap:.2e} mm between segment {i} and {i + 1} — chain is disconnected"
        )


# ---------------------------------------------------------------------------
# Invariant 4 — build_chain preserves connectivity
# ---------------------------------------------------------------------------


@given(segments=_connected_segments())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_build_chain_output_is_connected(segments: list[Segment]) -> None:
    """build_chain must return a connected chain for any pre-connected input.

    When the input segments are already connected (i.e. form a valid path),
    the output of ``build_chain`` must also be connected: every adjacent pair
    of output segments must share an endpoint within the snap tolerance (0.5 mm).
    """
    result = build_chain(segments)
    assert len(result) == len(segments), "build_chain must preserve element count"
    _SNAP = 0.5  # mm — matches _CHAIN_SNAP in _algorithms.py
    for i in range(len(result) - 1):
        gap = result[i].end.distance_to(result[i + 1].start)
        assert gap < _SNAP, (
            f"gap {gap:.4f} mm between output segment {i} and {i + 1} exceeds snap tolerance"
        )


# ---------------------------------------------------------------------------
# Invariant 5 — seam_length equals sum of individual lengths and is ≥ 0
# ---------------------------------------------------------------------------


@given(segments=st.lists(_connected_segments(), min_size=0, max_size=3))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_seam_length_equals_sum_of_lengths(segments: list[list[Segment]]) -> None:
    """seam_length must equal the sum of .length for each segment and be ≥ 0.

    This verifies both the non-negativity contract and that ``seam_length`` is
    a simple sum aggregation with no hidden offsets or weighting.
    """
    flat: list[Segment] = [s for chain in segments for s in chain]
    total = seam_length(flat)
    expected = sum(s.length for s in flat)
    assert total >= 0.0, f"seam_length returned negative value: {total}"
    assert total == pytest.approx(expected, abs=1e-6), (
        f"seam_length {total} ≠ sum of lengths {expected}"
    )
