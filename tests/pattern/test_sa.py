"""Tests for src/sewpat/pattern/_sa.py coverage gaps."""

from unittest.mock import patch

import pytest

import sewpat.pattern._sa as sa_module
from sewpat.element import PatternElement
from sewpat.geometry import CubicBezier, Dart, Point, Rect, Segment, Triangle
from sewpat.pattern import PatternPart
from sewpat.pattern._sa import (
    _closest_sa_edge,
    _fold_line_sa_point,
    _is_double_notch,
    _orient_dart_roof_pairs,
    _project_dart_notches_to_sa,
    add_seam_allowance,
)
from sewpat.style import StyleOptions

from .conftest import _square_part

# ---------------------------------------------------------------------------
# _closest_sa_edge
# ---------------------------------------------------------------------------


def test_closest_sa_edge_empty_list_returns_none():
    """Empty sa_geoms list returns None immediately (line 89)."""
    assert _closest_sa_edge(Point(0, 0), []) is None


def test_closest_sa_edge_zero_length_segment():
    """Zero-length segment (start == end) falls back to distance_to(start) (line 98)."""
    degenerate = Segment(Point(5, 5), Point(5, 5))
    result = _closest_sa_edge(Point(0, 0), [degenerate])
    assert result is degenerate


# ---------------------------------------------------------------------------
# _orient_dart_roof_pairs
# ---------------------------------------------------------------------------


def test_orient_dart_roof_pairs_visited_set_skips_second_appearance():
    """An index already in visited is skipped — covers the visited-set guard (line 159).

    elem0 bridges two peaks: peak_X=(5,0) and peak_Y=(0,10).
    elem1 shares peak_X with elem0 → pair (0,1) is processed, both added to visited.
    elem2 shares peak_Y with elem0 → pair (0,2) has i0=0 already in visited → line 159.
    """
    peak_x = Point(5, 0)
    peak_y = Point(0, 10)

    # elem0: start=peak_Y, end=peak_X — its index appears in both peak keys
    elem0 = PatternElement(Segment(peak_y, peak_x))
    elem0.role = "dart_roof"
    # elem1 shares peak_X → pair (elem0, elem1) processed first
    elem1 = PatternElement(Segment(Point(10, 10), peak_x))
    elem1.role = "dart_roof"
    # elem2 shares peak_Y → pair would be (elem0, elem2) but elem0 already visited
    elem2 = PatternElement(Segment(Point(-5, 5), peak_y))
    elem2.role = "dart_roof"

    result = _orient_dart_roof_pairs([elem0, elem1, elem2])
    # Should complete without error; 3 elements back
    assert len(result) == 3


def test_orient_dart_roof_pairs_reverses_g0_that_starts_at_peak():
    """g0 whose start is at the peak is reversed so it ends at the peak (lines 171-173)."""
    peak = Point(5, 0)

    # elem0 STARTS at the peak — wrong orientation, must be reversed
    elem0 = PatternElement(Segment(peak, Point(0, 10)))
    elem0.role = "dart_roof"
    # elem1 ends at the peak (correct for g1: should START at peak after fix)
    elem1 = PatternElement(Segment(Point(10, 10), peak))
    elem1.role = "dart_roof"

    result = _orient_dart_roof_pairs([elem0, elem1])

    # After reversal elem0 must END at peak
    assert result[0].geometry.end.x == pytest.approx(5.0)
    assert result[0].geometry.end.y == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _is_double_notch
# ---------------------------------------------------------------------------


def test_is_double_notch_non_triangle_geometry_returns_false():
    """Element with non-Triangle geometry always returns False (line 318)."""
    elem = PatternElement(Segment(Point(0, 0), Point(10, 0)))
    elem.role = "dart_notch"
    assert _is_double_notch(elem, []) is False


# ---------------------------------------------------------------------------
# add_seam_allowance — public API guards
# ---------------------------------------------------------------------------


def test_add_seam_allowance_invalid_corner_join_raises():
    """Invalid corner_join value raises ValueError (line 455)."""
    part = _square_part()
    with pytest.raises(ValueError, match="corner_join"):
        add_seam_allowance(part, 10.0, corner_join="invalid")


def test_add_seam_allowance_non_positive_distance_raises():
    """distance ≤ 0 raises ValueError (line 457)."""
    part = _square_part()
    with pytest.raises(ValueError, match="positive"):
        add_seam_allowance(part, -5.0)


def test_add_seam_allowance_zero_distance_raises():
    """distance == 0 raises ValueError."""
    part = _square_part()
    with pytest.raises(ValueError, match="positive"):
        add_seam_allowance(part, 0.0)


def test_add_seam_allowance_empty_outline_elements_returns_empty():
    """Explicit empty outline_elements list returns [] (line 464)."""
    part = _square_part()
    result = add_seam_allowance(part, 10.0, outline_elements=[])
    assert result == []


def test_add_seam_allowance_part_with_no_outline_returns_empty():
    """Part with no is_outline elements returns [] without crashing."""
    part = PatternPart(name="Empty")
    result = add_seam_allowance(part, 10.0)
    assert result == []


# ---------------------------------------------------------------------------
# _add_sa_rect — Rect fast-path (lines 350-362, 469)
# ---------------------------------------------------------------------------


def test_add_seam_allowance_rect_outline_fast_path():
    """Rect outline uses the fast-path: returns one uniformly expanded Rect SA element."""
    part = PatternPart(name="RectPart")
    rect = Rect(origin=Point(0, 0), width=100.0, height=80.0)
    part.append(rect, is_outline=True)

    added = add_seam_allowance(part, 10.0)

    assert len(added) == 1
    assert isinstance(added[0].geometry, Rect)
    assert added[0].is_seam_allowance
    assert added[0].geometry.width == pytest.approx(120.0)
    assert added[0].geometry.height == pytest.approx(100.0)
    # Origin should be shifted by -distance
    assert added[0].geometry.origin.x == pytest.approx(-10.0)
    assert added[0].geometry.origin.y == pytest.approx(-10.0)


# ---------------------------------------------------------------------------
# _add_sa_mixed — zero-distance fold-line keep-in-place (line 402)
# ---------------------------------------------------------------------------


def test_add_sa_mixed_zero_distance_edge_kept_in_place():
    """seam_allowance=0.0 on one edge keeps it in-place in _add_sa_mixed (line 402)."""
    part = PatternPart(name="P")
    s0 = part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
    s1 = part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)

    # Setting seam_allowance forces the mixed path;
    # seam_allowance=0.0 on s0 triggers the fold-line keep-in-place branch.
    s0.style = StyleOptions(seam_allowance=0.0)
    s1.style = StyleOptions(seam_allowance=10.0)

    added = add_seam_allowance(part, 10.0)

    assert len(added) > 0
    assert all(e.is_seam_allowance for e in added)


# ---------------------------------------------------------------------------
# _stitch_corners — gap ≤ 0.01 + miter skip (line 269)
# ---------------------------------------------------------------------------


def test_stitch_corners_miter_skips_when_gap_near_zero():
    """Per-element SA on all edges forces mixed path; perfectly-joined miter skips (line 269)."""
    part = PatternPart(name="P")
    segs = [
        Segment(Point(0, 0), Point(100, 0)),
        Segment(Point(100, 0), Point(100, 100)),
        Segment(Point(100, 100), Point(0, 100)),
        Segment(Point(0, 100), Point(0, 0)),
    ]
    for seg in segs:
        e = part.append(seg, is_outline=True)
        e.style = StyleOptions(seam_allowance=10.0)

    added = add_seam_allowance(part, 10.0, corner_join="miter")
    assert len(added) > 0
    assert all(e.is_seam_allowance for e in added)


# ---------------------------------------------------------------------------
# _stitch_corners — round corner CubicBezier arc inserts (lines 278-280, 299)
# ---------------------------------------------------------------------------


def test_add_seam_allowance_round_corner_produces_bezier_arcs():
    """corner_join='round' via mixed path produces CubicBezier arc inserts (lines 278-280, 299).

    Uses a triangle outline: offsetting the three sides outward creates a gap > 0.01 mm
    at each corner, so _stitch_corners skips the gap-continue guard and calls round_corner,
    which returns a CubicBezier for each convex corner.
    The mixed path is forced by setting a per-element seam_allowance override.
    """
    part = PatternPart(name="P")
    # Equilateral-ish triangle — convex corners guarantee gaps after outward offset
    segs = [
        Segment(Point(0, 0), Point(100, 0)),
        Segment(Point(100, 0), Point(50, 87)),
        Segment(Point(50, 87), Point(0, 0)),
    ]
    elems = [part.append(seg, is_outline=True) for seg in segs]
    # Force the mixed path by setting per-element SA on all edges
    for e in elems:
        e.style = StyleOptions(seam_allowance=10.0)

    added = add_seam_allowance(part, 10.0, corner_join="round")

    assert len(added) > 0
    beziers = [e for e in added if isinstance(e.geometry, CubicBezier)]
    assert len(beziers) > 0, "Expected at least one CubicBezier arc from round corners"


# ---------------------------------------------------------------------------
# _project_dart_notches_to_sa — early-return guards (lines 505, 509)
# ---------------------------------------------------------------------------


def test_project_dart_notches_no_sa_geoms_returns_early():
    """No SA segments on part → _project_dart_notches_to_sa returns immediately (line 505)."""
    part = PatternPart(name="P")
    part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
    # No is_seam_allowance elements — function should not raise
    _project_dart_notches_to_sa(part)


def test_project_dart_notches_no_centroid_returns_early():
    """SA element present but centroid is None → returns early (line 509)."""
    part = PatternPart(name="P")
    # No is_outline elements → centroid will be None
    sa_elem = part.append(Segment(Point(0, 0), Point(100, 0)))
    sa_elem.is_seam_allowance = True
    _project_dart_notches_to_sa(part)


# ---------------------------------------------------------------------------
# _project_dart_notches_to_sa — sa_edge is None → continue (line 531, monkeypatched)
# ---------------------------------------------------------------------------


def test_project_dart_notches_sa_edge_none_skips_notch():
    """When _closest_sa_edge returns None the notch is silently skipped (line 531)."""
    part = PatternPart(name="P")
    # Build a proper square so centroid is valid
    for seg in [
        Segment(Point(0, 0), Point(100, 0)),
        Segment(Point(100, 0), Point(100, 100)),
        Segment(Point(100, 100), Point(0, 100)),
        Segment(Point(0, 100), Point(0, 0)),
    ]:
        part.append(seg, is_outline=True)

    # Add an SA segment so sa_geoms is non-empty (passes line 504 guard)
    sa_seg = part.append(Segment(Point(-10, -10), Point(110, -10)))
    sa_seg.is_seam_allowance = True

    # Add a dart_notch candidate
    notch = part.append(Triangle(Point(48, 95), Point(52, 95), Point(50, 100)))
    notch.role = "dart_notch"

    with patch.object(sa_module, "_closest_sa_edge", return_value=None):
        _project_dart_notches_to_sa(part)  # must not raise; notch is skipped


# ---------------------------------------------------------------------------
# _fold_line_sa_point — except clause (lines 597-601, monkeypatched)
# ---------------------------------------------------------------------------


def test_fold_line_sa_point_intersect_raises_falls_back():
    """TypeError from _intersect_geom is caught; falls back to projection (lines 597-601)."""
    dart = Dart(
        leg_a=Point(45, 0),
        leg_b=Point(55, 0),
        center=Point(50, 0),
        tip=Point(50, 30),
    )
    seam_elem = PatternElement(Triangle(Point(48, 0), Point(52, 0), Point(50, 5)))
    seam_elem._dart_ref = dart
    seam_elem.role = "dart_center_notch"

    fallback = Segment(Point(0, -10), Point(100, -10))
    base_c = Point(50, 0)
    inward = Point(50, 50)

    with patch.object(sa_module, "_intersect_geom", side_effect=TypeError("boom")):
        result = _fold_line_sa_point(seam_elem, [fallback], fallback, base_c, inward)

    assert isinstance(result, Point)


@pytest.mark.parametrize("exc_type", [TypeError, ValueError, AttributeError])
def test_fold_line_sa_point_all_except_types_handled(exc_type):
    """All three exception types in the except clause are caught without crashing."""
    dart = Dart(
        leg_a=Point(45, 0),
        leg_b=Point(55, 0),
        center=Point(50, 0),
        tip=Point(50, 30),
    )
    seam_elem = PatternElement(Triangle(Point(48, 0), Point(52, 0), Point(50, 5)))
    seam_elem._dart_ref = dart
    seam_elem.role = "dart_center_notch"

    fallback = Segment(Point(0, -10), Point(100, -10))

    with patch.object(sa_module, "_intersect_geom", side_effect=exc_type("test")):
        result = _fold_line_sa_point(seam_elem, [fallback], fallback, Point(50, 0), Point(50, 50))

    assert isinstance(result, Point)


# ---------------------------------------------------------------------------
# _fold_line_sa_point — no _dart_ref fallback (lines 610-611)
# ---------------------------------------------------------------------------


def test_fold_line_sa_point_no_dart_ref_uses_fallback_projection():
    """When _dart_ref is None the function falls straight to project_onto_edge (lines 610-611)."""
    seam_elem = PatternElement(Triangle(Point(48, 0), Point(52, 0), Point(50, 5)))
    seam_elem.role = "dart_center_notch"
    # _dart_ref intentionally NOT set → getattr returns None

    fallback = Segment(Point(0, -10), Point(100, -10))
    base_c = Point(50, 0)
    inward = Point(50, 50)

    result = _fold_line_sa_point(seam_elem, [fallback], fallback, base_c, inward)

    assert isinstance(result, Point)
    # Projected point should land on the fallback segment's y-line
    assert result.y == pytest.approx(-10.0, abs=1.0)


# ---------------------------------------------------------------------------
# _stitch_corners — gap ≤ 0.01, non-bevel → continue (line 269)
# ---------------------------------------------------------------------------


def test_stitch_corners_collinear_gap_zero_skips_corner():
    """Collinear adjacent offset edges produce gap≈0; non-bevel join hits line 269.

    Splitting the bottom edge into two collinear segments means their outward
    offsets are also collinear and share an endpoint exactly (gap≈0).  With
    corner_join='miter' (non-bevel), _stitch_corners hits the continue at line 269.
    """
    part = PatternPart(name="P")
    segs = [
        Segment(Point(0, 0), Point(50, 0)),  # bottom-left half
        Segment(Point(50, 0), Point(100, 0)),  # bottom-right half — collinear
        Segment(Point(100, 0), Point(100, 100)),
        Segment(Point(100, 100), Point(0, 100)),
        Segment(Point(0, 100), Point(0, 0)),
    ]
    elems = [part.append(seg, is_outline=True) for seg in segs]
    # Per-element SA forces the mixed path through _add_sa_mixed → _stitch_corners
    for e in elems:
        e.style = StyleOptions(seam_allowance=10.0)

    added = add_seam_allowance(part, 10.0, corner_join="miter")
    assert len(added) > 0
    assert all(e.is_seam_allowance for e in added)
