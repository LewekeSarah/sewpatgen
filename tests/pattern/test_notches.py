"""Tests for src/sewpat/pattern/_notches.py coverage gaps.

Covers:
  - _ep_key (line 67)
  - _collect_candidates_by_role: exception branch in intersection (lines 250-256)
  - _place_grid_notches: same-geometry spacing guard (line 290)
"""

import pytest

from sewpat.geometry import Point, Segment, Triangle
from sewpat.pattern import PatternPart
from sewpat.pattern._notches import _ep_key

# =============================================================================
# _ep_key (line 67)
# =============================================================================


def test_ep_key_returns_rounded_tuple():
    """_ep_key rounds coordinates to 3 decimal places and returns a tuple."""
    pt = Point(1.23456, 7.89012)
    key = _ep_key(pt)
    assert key == (round(1.23456, 3), round(7.89012, 3))


def test_ep_key_integer_coordinates_unchanged():
    """_ep_key on exact integer coordinates returns (x, y) unchanged."""
    pt = Point(10.0, 20.0)
    assert _ep_key(pt) == (10.0, 20.0)


def test_ep_key_negative_coordinates():
    """_ep_key handles negative coordinates correctly."""
    pt = Point(-5.6789, -0.0001)
    key = _ep_key(pt)
    assert key == (round(-5.6789, 3), round(-0.0001, 3))


# =============================================================================
# Shared helpers
# =============================================================================


def _part_with_role_edge(role: str = "side") -> PatternPart:
    """100x100 mm square with the bottom edge tagged with *role*."""
    part = PatternPart(name="Body")
    seg = Segment(Point(0, 0), Point(100, 0))
    elem = part.append(seg, is_outline=True)
    elem.role = role
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)
    return part


def _grid_part_with_named_seg(name: str = "Waist") -> PatternPart:
    """Grid part containing one horizontal Segment accessible by *name*."""
    grid = PatternPart(name="Grid")
    seg = Segment(Point(-10, 50), Point(110, 50), name=name)
    grid.append(seg, is_outline=False)
    return grid


# =============================================================================
# add_grid_notches — missing grid element name → UserWarning (lines 234–239)
# =============================================================================


def test_add_grid_notches_missing_grid_name_emits_warning():
    """A role_map entry referencing a non-existent grid name emits a UserWarning."""
    part = _part_with_role_edge("side")
    grid = PatternPart(name="EmptyGrid")  # no elements at all

    with pytest.warns(UserWarning, match="not found"):
        result = part.add_grid_notches(
            grid_part=grid,
            role_map={"side": ["NonExistent"]},
        )
    assert isinstance(result, list)


# =============================================================================
# add_grid_notches — intersection exception → UserWarning (lines 250-256)
# =============================================================================


def test_add_grid_notches_intersection_exception_emits_warning(monkeypatch):
    """When the intersection call raises, a UserWarning is emitted and the
    candidate is skipped (covers lines 250-256)."""
    import sewpat.pattern._notches as _notches_mod

    def _boom(a, b):  # noqa: ANN001, ANN202
        raise RuntimeError("forced intersection error")

    monkeypatch.setattr(_notches_mod, "_intersect", _boom)

    part = _part_with_role_edge("side")
    grid = _grid_part_with_named_seg("Waist")

    with pytest.warns(UserWarning, match="intersection failed"):
        result = part.add_grid_notches(
            grid_part=grid,
            role_map={"side": ["Waist"]},
        )
    assert result == []


# =============================================================================
# _place_grid_notches — same-geometry spacing guard (line 290)
# =============================================================================


def test_place_grid_notches_same_geometry_spacing_skips_second(monkeypatch):
    """Per-geometry spacing guard (line 290) rejects a second candidate on the
    same seam edge when the global seen check passes but the per-geometry check
    fires.

    ``_too_close`` is monkeypatched so that:
    - calls 1 & 2 (global seen check for pt_a and pt_b) return False
    - call 3+ (per-geometry check for pt_b) delegates to the real _too_close
    This ensures line 290 — not line 287 — is what rejects pt_b.
    """
    import sewpat.pattern._notches as _notches_mod
    from sewpat.pattern._notches import _place_grid_notches
    from sewpat.pattern._notches import _too_close as _real_too_close

    part = PatternPart(name="Body")
    seam = Segment(Point(0, 0), Point(100, 0))
    part.append(seam, is_outline=True)
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)

    pt_a = Point(50, 0)
    pt_b = Point(51, 0)  # 1 mm from pt_a — within min_spacing=8

    call_count = [0]

    def _patched(pt, candidates, spacing):  # noqa: ANN001, ANN202
        call_count[0] += 1
        # 4 calls total for 2 candidates (2 guards × 2 pts):
        #   1 = pt_a global seen (line 287) → False (place pt_a)
        #   2 = pt_a per-geometry (line 289) → False (elem_placed empty)
        #   3 = pt_b global seen (line 287) → False (bypass; pt_a is in seen)
        #   4 = pt_b per-geometry (line 289) → real → True → line 290 fires
        if call_count[0] <= 3:
            return False  # bypass the first three calls
        return _real_too_close(pt, candidates, spacing)  # call 4: per-geometry → True

    monkeypatch.setattr(_notches_mod, "_too_close", _patched)

    candidates = [(seam, pt_a), (seam, pt_b)]
    seen: list[Point] = []
    created = _place_grid_notches(
        part, candidates, seen, min_spacing=8.0, length=8.0, width=4.0, is_back=False
    )

    # Only one notch placed — pt_b rejected by per-geometry guard (line 290)
    notch_triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(notch_triangles) == 1
