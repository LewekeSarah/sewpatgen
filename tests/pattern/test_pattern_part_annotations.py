"""Tests for PatternPart annotation and seam-allowance methods.

Covers:
  - add_info_box
  - add_precision_points
  - add_notches (basic, dual SA-notch, dart-leg projection)
  - add_seam_allowance (SA reversal, corner_join modes)
"""

import math
from typing import cast

import pytest

from sewpat.geometry import Circle, CubicBezier, InfoBox, Point, Segment, Triangle
from sewpat.pattern import PatternPart
from sewpat.style import StyleOptions
from sewpat.units import CM, MM

from .conftest import _square_part, _square_part_with_dart, _square_part_with_sa

# ---------------------------------------------------------------------------
# PatternPart -- add_info_box
# ---------------------------------------------------------------------------


def test_add_info_box_returns_none_without_geometry():
    assert PatternPart(name="Empty").add_info_box() is None


def test_info_box_position_is_centroid():
    part = PatternPart(name="Sleeve")
    part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
    part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
    part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
    centroid = part.centroid
    ib: InfoBox = part.add_info_box().geometry
    assert abs(ib.position.x - centroid.x) < 1e-6
    assert abs(ib.position.y - centroid.translate(0, 3 * CM).y) < 1e-6


def test_info_box_default_header_is_part_name():
    part = PatternPart(name="Sleeve")
    part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
    part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
    part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
    assert part.add_info_box().geometry.header == "Sleeve"


def test_info_box_custom_header():
    part = PatternPart(name="Sleeve")
    part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
    part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
    part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
    assert part.add_info_box(header="Custom Header").geometry.header == "Custom Header"


def test_info_box_notes():
    part = PatternPart(name="Cuff")
    part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
    part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
    part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
    notes = ["1 cm seam allowance", "Cut 2x"]
    assert part.add_info_box(notes=notes).geometry.notes == notes


# ---------------------------------------------------------------------------
# PatternPart -- add_precision_points
# ---------------------------------------------------------------------------


def test_two_circles_per_point():
    part = PatternPart(name="Body")
    part.add_precision_points(Point(5, 5))
    assert len([e for e in part.elements if isinstance(e.geometry, Circle)]) == 2


def test_multiple_precision_points():
    part = PatternPart(name="Body")
    part.add_precision_points(Point(0, 0), Point(10, 10), Point(20, 20))
    assert len([e for e in part.elements if isinstance(e.geometry, Circle)]) == 6


def test_circle_radii():
    """Circles have the correct radii (5 mm outer, 0.5 mm inner)."""
    part = PatternPart(name="Body")
    part.add_precision_points(Point(0, 0))
    radii = sorted(e.geometry.radius for e in part.elements if isinstance(e.geometry, Circle))
    assert abs(radii[0] - 0.5 * MM) < 1e-9
    assert abs(radii[1] - 5.0 * MM) < 1e-9


# ---------------------------------------------------------------------------
# PatternPart -- add_notches (basic)
# ---------------------------------------------------------------------------


def test_notch_without_segment_adds_triangle():
    part = PatternPart(name="Body")
    part.add_notches(Point(5, 0))
    assert len([e for e in part.elements if isinstance(e.geometry, Triangle)]) == 1


def test_notch_without_segment_tip_above_base():
    part = PatternPart(name="Body")
    part.add_notches(Point(10, 10))
    tri = cast(Triangle, part.elements[-1].geometry)
    assert tri.p3.y < (tri.p1.y + tri.p2.y) / 2


def test_multiple_notches():
    part = PatternPart(name="Body")
    part.add_notches(Point(0, 0), Point(5, 0), Point(10, 0))
    assert len([e for e in part.elements if isinstance(e.geometry, Triangle)]) == 3


def test_notch_with_segment_adds_triangle():
    part = PatternPart(name="Body")
    part.append(Segment(Point(0, 0), Point(10 * CM, 0)), is_outline=True)
    part.append(Segment(Point(10 * CM, 0), Point(10 * CM, 10 * CM)), is_outline=True)
    part.append(Segment(Point(10 * CM, 10 * CM), Point(0, 10 * CM)), is_outline=True)
    part.append(Segment(Point(0, 10 * CM), Point(0, 0)), is_outline=True)
    part.add_notches(
        Point(5 * CM, 10 * CM), seam_edge=Segment(Point(0, 10 * CM), Point(10 * CM, 10 * CM))
    )
    assert len([e for e in part.elements if isinstance(e.geometry, Triangle)]) == 1


def test_notch_with_segment_tip_points_inward():
    part = PatternPart(name="Body")
    part.append(Segment(Point(0, 0), Point(10 * CM, 0)), is_outline=True)
    part.append(Segment(Point(10 * CM, 0), Point(10 * CM, 10 * CM)), is_outline=True)
    part.append(Segment(Point(10 * CM, 10 * CM), Point(0, 10 * CM)), is_outline=True)
    part.append(Segment(Point(0, 10 * CM), Point(0, 0)), is_outline=True)
    mid = Point(5 * CM, 10 * CM)
    part.add_notches(mid, seam_edge=Segment(Point(0, 10 * CM), Point(10 * CM, 10 * CM)))
    tri = cast(Triangle, part.elements[-1].geometry)
    assert tri.p3.y < mid.y


def test_notch_custom_length_and_width():
    part = PatternPart(name="Body")
    part.add_notches(Point(10, 0), length=1.5 * CM, width=0.6 * CM)
    tri = cast(Triangle, part.elements[-1].geometry)
    base_width = tri.p1.distance_to(tri.p2)
    tip_dist = math.sqrt(
        ((tri.p1.x + tri.p2.x) / 2 - tri.p3.x) ** 2 + ((tri.p1.y + tri.p2.y) / 2 - tri.p3.y) ** 2
    )
    assert abs(base_width - 0.6 * CM) < 1e-6
    assert abs(tip_dist - 1.5 * CM) < 1e-6


# ------------------------------------------------------------------
# Automatic dual-notch (seam-line + SA-line)
# ------------------------------------------------------------------


def test_with_sa_produces_two_notch_triangles():
    """After add_seam_allowance, add_notches produces two triangles per point."""
    part = _square_part_with_sa(10.0)
    n_before = len(part.elements)
    part.add_notches(Point(50, 0), seam_edge=Segment(Point(0, 0), Point(100, 0)))
    triangles = [e for e in part.elements[n_before:] if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 2
    flags = [e.is_seam_allowance for e in triangles]
    assert False in flags and True in flags


def test_without_sa_produces_one_notch_triangle():
    part = PatternPart(name="NoSA")
    part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)
    n_before = len(part.elements)
    part.add_notches(Point(50, 0), seam_edge=Segment(Point(0, 0), Point(100, 0)))
    triangles = [e for e in part.elements[n_before:] if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 1 and not triangles[0].is_seam_allowance


def test_seam_line_notch_sits_on_seam():
    part = _square_part_with_sa(10.0)
    n_before = len(part.elements)
    part.add_notches(Point(50, 0), seam_edge=Segment(Point(0, 0), Point(100, 0)))
    seam_tri = next(
        e
        for e in part.elements[n_before:]
        if isinstance(e.geometry, Triangle) and not e.is_seam_allowance
    )
    assert abs((seam_tri.geometry.p1.y + seam_tri.geometry.p2.y) / 2) <= 0.5


def test_sa_notch_sits_on_sa_edge():
    sa_dist = 10.0
    part = _square_part_with_sa(sa_dist)
    n_before = len(part.elements)
    part.add_notches(Point(50, 0), seam_edge=Segment(Point(0, 0), Point(100, 0)))
    sa_tri = next(
        e
        for e in part.elements[n_before:]
        if isinstance(e.geometry, Triangle) and e.is_seam_allowance
    )
    assert abs((sa_tri.geometry.p1.y + sa_tri.geometry.p2.y) / 2 - (-sa_dist)) <= 0.5


def test_sa_notch_tip_points_inward():
    part = _square_part_with_sa(10.0)
    n_before = len(part.elements)
    part.add_notches(Point(50, 0), seam_edge=Segment(Point(0, 0), Point(100, 0)))
    sa_tri = next(
        e
        for e in part.elements[n_before:]
        if isinstance(e.geometry, Triangle) and e.is_seam_allowance
    )
    base_y = (sa_tri.geometry.p1.y + sa_tri.geometry.p2.y) / 2
    assert sa_tri.geometry.p3.y > base_y


def test_sa_notch_x_position_preserved():
    part = _square_part_with_sa(10.0)
    n_before = len(part.elements)
    part.add_notches(Point(50, 0), seam_edge=Segment(Point(0, 0), Point(100, 0)))
    sa_tri = next(
        e
        for e in part.elements[n_before:]
        if isinstance(e.geometry, Triangle) and e.is_seam_allowance
    )
    assert abs((sa_tri.geometry.p1.x + sa_tri.geometry.p2.x) / 2 - 50.0) <= 1.0


# ---------------------------------------------------------------------------
# PatternPart -- _project_dart_notches_to_sa
# ---------------------------------------------------------------------------


def test_dart_leg_notches_projected_after_sa():
    part = _square_part_with_dart()
    part.add_seam_allowance(10.0)
    sa_dart_notches = [
        e
        for e in part.elements
        if e.role == "dart_notch" and e.is_seam_allowance and isinstance(e.geometry, Triangle)
    ]
    assert len(sa_dart_notches) >= 2


def test_seam_line_notches_become_is_seam_notch():
    part = _square_part_with_dart()
    part.add_seam_allowance(10.0)
    seam_notches = [
        e
        for e in part.elements
        if e.role == "dart_notch" and not e.is_seam_allowance and isinstance(e.geometry, Triangle)
    ]
    for e in seam_notches:
        assert e.is_seam_notch


def test_dart_sa_notch_sits_on_sa_edge():
    part = _square_part_with_dart()
    sa_dist = 10.0
    part.add_seam_allowance(sa_dist)
    for e in [
        e
        for e in part.elements
        if e.role == "dart_notch" and e.is_seam_allowance and isinstance(e.geometry, Triangle)
    ]:
        assert abs((e.geometry.p1.y + e.geometry.p2.y) / 2 - (-sa_dist)) <= 1.5


def test_no_duplicate_projection_on_second_sa_call():
    part = _square_part_with_dart()
    part.add_seam_allowance(10.0)
    count_first = len([e for e in part.elements if e.role == "dart_notch" and e.is_seam_allowance])
    part.add_seam_allowance(10.0)
    count_second = len([e for e in part.elements if e.role == "dart_notch" and e.is_seam_allowance])
    assert count_first == count_second


# ---------------------------------------------------------------------------
# PatternPart -- get_dart (moved here from separate test file)
# ---------------------------------------------------------------------------


def test_get_dart_returns_legs_and_tip() -> None:
    part = PatternPart("TestPart")
    dart_name = "My Dart"

    # Two segments representing dart legs
    s1 = Segment(Point(0, 0), Point(1, 0)).set_name(dart_name)
    s2 = Segment(Point(0, 0), Point(0, 1)).set_name(dart_name)
    part.append(s1, role="dart_stitch")
    part.append(s2, role="dart_stitch")

    # A precision Circle representing the dart tip
    tip_center = Point(0.5, 0.5)
    c = Circle(tip_center, radius=1.0).set_name(dart_name)
    part.append(c, role="dart_tip")

    legs, tip = part.get_dart(dart_name)
    assert len(legs) == 2
    assert tip == tip_center


# ---------------------------------------------------------------------------
# add_seam_allowance -- SA distance survives build_chain reversal
# ---------------------------------------------------------------------------


def test_reversed_waistband_gets_correct_sa():
    """Waistband reversed by build_chain must keep its per-style SA (30 mm)."""
    from sewpat.style import STYLE_STITCH

    part = PatternPart(name="Test")
    part.append(
        Segment(Point(0, 100), Point(100, 100)),
        style=StyleOptions(seam_allowance=25.0),
        is_outline=True,
    )
    part.append(Segment(Point(100, 0), Point(100, 100)), style=STYLE_STITCH, is_outline=True)
    part.append(
        Segment(Point(0, 0), Point(100, 0)),
        style=StyleOptions(seam_allowance=30.0),
        is_outline=True,
    )
    part.append(Segment(Point(0, 0), Point(0, 100)), style=STYLE_STITCH, is_outline=True)
    part.add_seam_allowance(10.0)
    sa_segs = [
        e.geometry for e in part.elements if e.is_seam_allowance and isinstance(e.geometry, Segment)
    ]
    waistband_sa = [
        s for s in sa_segs if abs(s.p1.y - (-30.0)) < 5.0 or abs(s.p2.y - (-30.0)) < 5.0
    ]
    assert len(waistband_sa) > 0, "No SA segment found near y=-30"


# ---------------------------------------------------------------------------
# add_seam_allowance -- corner_join parameter
# ---------------------------------------------------------------------------


def test_sa_corner_join_default_is_miter():
    sa_elems = _square_part().add_seam_allowance(10.0)
    assert len(sa_elems) > 0 and all(e.is_seam_allowance for e in sa_elems)


def test_sa_corner_join_miter_explicit():
    assert len(_square_part().add_seam_allowance(10.0, corner_join="miter")) > 0


def test_sa_corner_join_round():
    sa_elems = _square_part().add_seam_allowance(10.0, corner_join="round")
    assert len(sa_elems) > 0 and all(e.is_seam_allowance for e in sa_elems)


def test_sa_corner_join_bevel():
    sa_elems = _square_part().add_seam_allowance(10.0, corner_join="bevel")
    assert len(sa_elems) > 0 and all(e.is_seam_allowance for e in sa_elems)


def test_sa_invalid_corner_join_raises():
    with pytest.raises(ValueError):
        _square_part().add_seam_allowance(10.0, corner_join="zigzag")


def test_sa_round_more_segments_than_bevel_on_square():
    n_round = len(_square_part().add_seam_allowance(10.0, corner_join="round"))
    n_bevel = len(_square_part().add_seam_allowance(10.0, corner_join="bevel"))
    assert n_round > n_bevel, f"Round ({n_round}) should exceed bevel ({n_bevel})"


def _bezier_part() -> PatternPart:
    part = PatternPart(name="Curved")
    part.append(
        CubicBezier(Point(0, 0), Point(33, -30), Point(67, -30), Point(100, 0)), is_outline=True
    )
    part.append(Segment(Point(100, 0), Point(100, 50)), is_outline=True)
    part.append(Segment(Point(100, 50), Point(0, 50)), is_outline=True)
    part.append(Segment(Point(0, 50), Point(0, 0)), is_outline=True)
    return part


def test_sa_miter_corner_join_on_bezier_path():
    assert len(_bezier_part().add_seam_allowance(10.0, corner_join="miter")) > 0


def test_sa_bevel_corner_join_on_bezier_path():
    assert len(_bezier_part().add_seam_allowance(10.0, corner_join="bevel")) > 0


def test_sa_round_on_bezier_path_inserts_arc_elements():
    """corner_join='round' inserts CubicBezier arc elements at corners."""
    sa_elems = _bezier_part().add_seam_allowance(10.0, corner_join="round")
    assert len([e for e in sa_elems if isinstance(e.geometry, CubicBezier)]) > 0
    assert all(e.is_seam_allowance for e in sa_elems)


def test_sa_per_element_corner_join_override():
    """StyleOptions.corner_join on an element overrides the part-level default."""
    part = PatternPart(name="MixedCorners")
    part.append(
        Segment(Point(0, 0), Point(100, 0)),
        style=StyleOptions(corner_join="bevel"),
        is_outline=True,
    )
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)
    sa_elems = part.add_seam_allowance(10.0, corner_join="miter")
    assert len(sa_elems) > 0 and all(e.is_seam_allowance for e in sa_elems)


def test_sa_per_element_corner_join_invalid_raises():
    """An invalid StyleOptions.corner_join value raises ValueError."""
    part = PatternPart(name="Bad")
    part.append(
        Segment(Point(0, 0), Point(100, 0)),
        style=StyleOptions(corner_join="zigzag"),
        is_outline=True,
    )
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)
    with pytest.raises(ValueError):
        part.add_seam_allowance(10.0)
