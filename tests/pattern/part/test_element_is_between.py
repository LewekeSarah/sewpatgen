"""Tests for PatternPart._rep_point and PatternPart._element_is_between.

Geometry setup used throughout:
  pivot      = Point(0, 0)
  leg_dir    = (1, 0)   →  pointing right  (0°)
  cut_dir    = (0, 1)   →  pointing up     (90°)

This defines a CCW sector of 90° covering the first quadrant.

A second CW sector is used to verify the negative-sector branch:
  leg_dir    = (0, 1)   →  up  (90°)
  cut_dir    = (1, 0)   →  right (0°)
  sector     = -90°  (CW from up to right)
"""

import numpy as np

from sewpat.element import PatternElement
from sewpat.geometry import (
    Circle,
    CubicBezier,
    Dart,
    InfoBox,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
)
from sewpat.pattern import PatternPart

# Convenience aliases
_rep = PatternPart._rep_point
_between = PatternPart._element_is_between

# Fixed sector for most tests: CCW 90° in the first quadrant
PIVOT = Point(0, 0)
LEG_DIR = np.array([1.0, 0.0])  # →  0°
CUT_DIR = np.array([0.0, 1.0])  # ↑  90°


# ---------------------------------------------------------------------------
# _rep_point
# ---------------------------------------------------------------------------


def test_rep_point_returns_point_itself():
    p = Point(3.0, 4.0)
    assert _rep(p) is p


def test_rep_point_segment_returns_midpoint():
    seg = Segment(Point(0, 0), Point(4, 0))
    mid = _rep(seg)
    assert mid is not None
    assert abs(mid.x - 2.0) < 1e-9
    assert abs(mid.y - 0.0) < 1e-9


def test_rep_point_cubicbezier_returns_point_at_half():
    # straight Bézier from (0,0) to (10,0) — point_at_t(0.5) == (5, 0)
    bez = CubicBezier(Point(0, 0), Point(0, 0), Point(10, 0), Point(10, 0))
    mid = _rep(bez)
    assert mid is not None
    assert abs(mid.x - 5.0) < 1e-6
    assert abs(mid.y - 0.0) < 1e-6


def test_rep_point_circle_returns_center():
    c = Circle(center=Point(7.0, -3.0), radius=2.0)
    rep = _rep(c)
    assert rep is not None
    assert abs(rep.x - 7.0) < 1e-9 and abs(rep.y - (-3.0)) < 1e-9


def test_rep_point_dart_returns_center():
    d = Dart.from_tip_center_width(tip=Point(0, 50), center=Point(0, 0), width=20.0)
    rep = _rep(d)
    assert rep is not None
    assert abs(rep.x - d.center.x) < 1e-9 and abs(rep.y - d.center.y) < 1e-9


def test_rep_point_infobox_returns_position():
    box = InfoBox(position=Point(5.0, 8.0), header="Test")
    rep = _rep(box)
    assert rep is not None
    assert abs(rep.x - 5.0) < 1e-9 and abs(rep.y - 8.0) < 1e-9


def test_rep_point_rect_returns_center():
    r = Rect(origin=Point(0, 0), width=10.0, height=4.0)
    rep = _rep(r)
    assert rep is not None
    assert abs(rep.x - 5.0) < 1e-9 and abs(rep.y - 2.0) < 1e-9


def test_rep_point_triangle_returns_centroid():
    tri = Triangle(p1=Point(0, 0), p2=Point(6, 0), p3=Point(0, 6))
    rep = _rep(tri)
    assert rep is not None
    assert abs(rep.x - 2.0) < 1e-9 and abs(rep.y - 2.0) < 1e-9


def test_rep_point_ray_returns_none():
    r = Ray(Point(0, 0), np.array([1.0, 0.0]))
    assert _rep(r) is None


def test_rep_point_unknown_geometry_returns_none():
    class _Unknown:
        pass

    assert _rep(_Unknown()) is None


def test_rep_point_unwraps_pattern_element():
    seg = Segment(Point(0, 0), Point(10, 0))
    elem = PatternElement(seg)
    rep = _rep(elem)
    assert rep is not None
    assert abs(rep.x - 5.0) < 1e-9


# ---------------------------------------------------------------------------
# _element_is_between — CCW 90° sector (first quadrant)
# ---------------------------------------------------------------------------


def _seg_at(x: float, y: float) -> Segment:
    """Segment whose midpoint is (x, y)."""
    return Segment(Point(x - 0.5, y), Point(x + 0.5, y))


def test_inside_ccw_sector():
    # (1, 1) normalized is at 45°, clearly between 0° and 90°
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(5.0, 5.0)) is True


def test_outside_ccw_sector_below():
    # (1, -1) is at -45°, outside [0°, 90°]
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(5.0, -5.0)) is False


def test_outside_ccw_sector_behind():
    # (-1, 0) is at 180°, outside [0°, 90°]
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(-5.0, 0.0)) is False


def test_on_leg_boundary_included():
    # exactly on the leg direction (0°) — boundary counts as inside
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(5.0, 0.0)) is True


def test_on_cut_boundary_included():
    # exactly on the cut direction (90°) — boundary counts as inside
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(0.0, 5.0)) is True


def test_third_quadrant_outside():
    # (-1, -1) is at 225°, far outside the first-quadrant sector
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(-5.0, -5.0)) is False


# ---------------------------------------------------------------------------
# _element_is_between — CW sector (leg=up, cut=right → -90°)
# ---------------------------------------------------------------------------

CW_LEG_DIR = np.array([0.0, 1.0])  # ↑  90°
CW_CUT_DIR = np.array([1.0, 0.0])  # →  0°
# sector angle = atan2(-1, 0) = -π/2  →  CW 90° (first quadrant, going CW)


def test_inside_cw_sector():
    # (1, 1) at 45°: signed angle from (0,1) is -45° → inside [-90°, 0°]
    assert _between(PIVOT, CW_LEG_DIR, CW_CUT_DIR, _seg_at(5.0, 5.0)) is True


def test_outside_cw_sector_left():
    # (-1, 1) at 135°: signed angle from (0,1) is +45° → outside [-90°, 0°]
    assert _between(PIVOT, CW_LEG_DIR, CW_CUT_DIR, _seg_at(-5.0, 5.0)) is False


def test_outside_cw_sector_below():
    # (0, -1) at 270° / -90°: signed angle from (0,1) is 180° → outside
    assert _between(PIVOT, CW_LEG_DIR, CW_CUT_DIR, _seg_at(0.0, -5.0)) is False


# ---------------------------------------------------------------------------
# _element_is_between — edge cases
# ---------------------------------------------------------------------------


def test_point_at_pivot_returns_false():
    # representative point coincides with pivot → distance = 0 → False
    assert _between(PIVOT, LEG_DIR, CUT_DIR, _seg_at(0.0, 0.0)) is False


def test_no_rep_point_returns_false():
    # Ray has no representative point → False
    r = Ray(Point(3, 3), np.array([1.0, 0.0]))
    assert _between(PIVOT, LEG_DIR, CUT_DIR, r) is False


def test_parallel_directions_returns_false():
    # leg and cut are identical → sector angle ≈ 0 → False regardless of elem
    assert _between(PIVOT, LEG_DIR, LEG_DIR, _seg_at(5.0, 5.0)) is False


def test_anti_parallel_directions_returns_false():
    # sector angle = π (half-plane) — too ambiguous to be useful, treated as degenerate
    anti_cut = np.array([-1.0, 0.0])
    assert _between(PIVOT, LEG_DIR, anti_cut, _seg_at(0.0, 5.0)) is False


def test_pattern_element_wrapping_segment_unwrapped():
    # PatternElement wrapper must be transparent
    seg = Segment(Point(3, 3), Point(7, 7))  # midpoint (5, 5) → 45° → inside
    elem = PatternElement(seg, is_outline=True)
    assert _between(PIVOT, LEG_DIR, CUT_DIR, elem) is True


def test_circle_inside_sector():
    c = Circle(center=Point(4.0, 2.0), radius=1.0)
    # angle ≈ atan2(2, 4) ≈ 27° → inside [0°, 90°]
    assert _between(PIVOT, LEG_DIR, CUT_DIR, c) is True


def test_circle_outside_sector():
    c = Circle(center=Point(4.0, -2.0), radius=1.0)
    # angle ≈ -27° → outside [0°, 90°]
    assert _between(PIVOT, LEG_DIR, CUT_DIR, c) is False


def test_cubicbezier_midpoint_used():
    # straight Bézier along y-axis: point_at_t(0.5) = (0, 5) → on cut boundary → True
    bez = CubicBezier(Point(0, 0), Point(0, 2), Point(0, 8), Point(0, 10))
    # midpoint at t=0.5: x=0, y≈5 → angle 90° → on boundary → True
    assert _between(PIVOT, LEG_DIR, CUT_DIR, bez) is True


def test_offset_pivot():
    # Same geometry but pivot shifted — verifies directions are relative to pivot
    pivot = Point(10.0, 10.0)
    leg_dir = np.array([1.0, 0.0])
    cut_dir = np.array([0.0, 1.0])
    # element at (15, 15): vector from pivot is (5, 5) → 45° → inside
    assert _between(pivot, leg_dir, cut_dir, _seg_at(15.0, 15.0)) is True
    # element at (5, 5): vector from pivot is (-5, -5) → 225° → outside
    assert _between(pivot, leg_dir, cut_dir, _seg_at(5.0, 5.0)) is False
