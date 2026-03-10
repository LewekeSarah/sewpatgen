"""Tests for PatternPart geometric properties and spatial queries.

Covers:
  - centroid
  - area_cm2
  - bounding_box
  - contains_point
  - add_grainline (basic + nudging)
  - seam_length (free function + PatternPart.seam_length())
"""

import math
from typing import cast

from sewpat.geometry import (
    Circle,
    CubicBezier,
    InfoBox,
    Point,
    Rect,
    Segment,
    Triangle,
    seam_length,
)
from sewpat.pattern import PatternPart
from sewpat.style import STYLE_GRAINLINE
from sewpat.units import CM

from .conftest import _rect_part, _square_part

# ---------------------------------------------------------------------------
# PatternPart -- centroid
# ---------------------------------------------------------------------------


def test_centroid_none_on_empty_part():
    assert PatternPart(name="Empty").centroid is None


def test_centroid_none_without_outline_elements():
    part = PatternPart(name="P")
    part.append(Point(0, 0))
    part.append(Segment(Point(0, 0), Point(10, 0)))
    assert part.centroid is None


def test_centroid_from_outline_polygon_square():
    """With is_outline Segments Shapely returns the true geometric centroid."""
    part = PatternPart(name="Square")
    part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
    part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
    part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
    c = part.centroid
    assert c is not None
    assert abs(c.x - 5.0) < 1e-3
    assert abs(c.y - 5.0) < 1e-3


def test_centroid_from_outline_polygon_rectangle():
    part = PatternPart(name="Rect")
    part.append(Segment(Point(0, 0), Point(20, 0)), is_outline=True)
    part.append(Segment(Point(20, 0), Point(20, 6)), is_outline=True)
    part.append(Segment(Point(20, 6), Point(0, 6)), is_outline=True)
    part.append(Segment(Point(0, 6), Point(0, 0)), is_outline=True)
    c = part.centroid
    assert c is not None
    assert abs(c.x - 10.0) < 1e-3
    assert abs(c.y - 3.0) < 1e-3


# ---------------------------------------------------------------------------
# PatternPart -- area_cm2
# ---------------------------------------------------------------------------


def test_area_none_without_outline():
    assert PatternPart(name="Empty").area_cm2 is None


def test_area_square_10mm():
    """10 mm x 10 mm square => area = 1 cm2."""
    part = PatternPart(name="Square")
    part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
    part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
    part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
    assert abs(part.area_cm2 - 1.0) < 1e-4


def test_area_rectangle():
    """40 mm x 30 mm rectangle => area = 12 cm2."""
    part = PatternPart(name="Rect")
    part.append(Segment(Point(0, 0), Point(40, 0)), is_outline=True)
    part.append(Segment(Point(40, 0), Point(40, 30)), is_outline=True)
    part.append(Segment(Point(40, 30), Point(0, 30)), is_outline=True)
    part.append(Segment(Point(0, 30), Point(0, 0)), is_outline=True)
    assert abs(part.area_cm2 - 12.0) < 1e-4


# ---------------------------------------------------------------------------
# PatternPart -- bounding_box
# ---------------------------------------------------------------------------


def test_bounding_box_returns_none_without_outline():
    assert PatternPart(name="Empty").bounding_box() is None


def test_bounding_box_returns_none_without_outline_flag():
    part = PatternPart(name="P")
    part.append(Segment(Point(0, 0), Point(10, 0)))  # is_outline=False
    assert part.bounding_box() is None


def test_bounding_box_axis_aligned_square():
    """10 x 10 mm square at origin => bbox (0,0)-(10,10)."""
    bb = _rect_part(0, 0, 10, 10).bounding_box()
    assert bb is not None
    mn, mx = bb
    assert abs(mn.x) < 1e-6 and abs(mn.y) < 1e-6
    assert abs(mx.x - 10.0) < 1e-6 and abs(mx.y - 10.0) < 1e-6


def test_bounding_box_offset_rectangle():
    bb = _rect_part(5, 15, 45, 70).bounding_box()
    assert bb is not None
    mn, mx = bb
    assert abs(mn.x - 5.0) < 1e-6 and abs(mn.y - 15.0) < 1e-6
    assert abs(mx.x - 45.0) < 1e-6 and abs(mx.y - 70.0) < 1e-6


def test_bounding_box_width_and_height():
    mn, mx = _rect_part(0, 0, 60, 40).bounding_box()
    assert abs(mx.x - mn.x - 60.0) < 1e-6
    assert abs(mx.y - mn.y - 40.0) < 1e-6


def test_bounding_box_non_outline_elements_ignored():
    part = _rect_part(0, 0, 20, 20)
    part.append(Segment(Point(100, 100), Point(200, 200)))  # not is_outline
    mn, mx = part.bounding_box()
    assert abs(mx.x - 20.0) < 1e-6 and abs(mx.y - 20.0) < 1e-6


def test_bounding_box_bezier_outline_expands_bbox():
    """A CubicBezier whose control points bulge outside the chord expands the bbox."""
    b = CubicBezier(Point(0, 0), Point(10, 20), Point(30, 20), Point(40, 0))
    part = PatternPart(name="Curve")
    part.append(b, is_outline=True)
    part.append(Segment(Point(40, 0), Point(0, 0)), is_outline=True)
    bb = part.bounding_box()
    assert bb is not None
    mn, mx = bb
    assert abs(mn.x) < 1e-3 and abs(mx.x - 40.0) < 1e-3
    assert abs(mn.y) < 1e-3 and mx.y > 10.0


# ---------------------------------------------------------------------------
# PatternPart -- add_grainline (basic)
# ---------------------------------------------------------------------------


def test_grainline_added():
    """add_grainline appends a Segment with STYLE_GRAINLINE."""
    elem = PatternPart(name="Front").add_grainline(Point(0, 0), Point(0, 5 * CM))
    assert isinstance(elem.geometry, Segment)
    assert elem.style is STYLE_GRAINLINE


def test_grainline_default_name():
    elem = PatternPart(name="Front").add_grainline(Point(0, 0), Point(0, 10))
    assert "grainline" in elem.get_name().lower()


def test_grainline_custom_name():
    elem = PatternPart(name="Back").add_grainline(Point(0, 0), Point(0, 10), name="Grain")
    assert elem.get_name() == "Grain"


# ---------------------------------------------------------------------------
# PatternPart -- contains_point
# ---------------------------------------------------------------------------


def test_contains_point_returns_false_without_outline():
    assert not PatternPart(name="Empty").contains_point(Point(5, 5))


def test_contains_point_centre_is_inside():
    assert _square_part(100).contains_point(Point(50, 50))


def test_contains_point_corner_is_outside():
    assert not _square_part(100).contains_point(Point(0, 0))


def test_contains_point_outside_is_false():
    assert not _square_part(100).contains_point(Point(200, 200))


def test_contains_point_near_edge_inside():
    assert _square_part(100).contains_point(Point(1, 50))


def test_contains_point_near_edge_outside():
    assert not _square_part(100).contains_point(Point(-1, 50))


# ---------------------------------------------------------------------------
# PatternPart -- add_grainline nudging
# ---------------------------------------------------------------------------


def test_grainline_fully_inside_unchanged():
    seg = cast(Segment, _square_part(100).add_grainline(Point(20, 50), Point(80, 50)).geometry)
    assert abs(seg.p1.x - 20.0) < 1e-3 and abs(seg.p2.x - 80.0) < 1e-3


def test_grainline_start_outside_is_nudged_inward():
    seg = cast(Segment, _square_part(100).add_grainline(Point(-20, 50), Point(80, 50)).geometry)
    assert 0.0 <= seg.p1.x < 5.0
    assert abs(seg.p1.y - 50.0) < 1e-3
    assert abs(seg.p2.x - 80.0) < 1e-3


def test_grainline_end_outside_is_nudged_inward():
    seg = cast(Segment, _square_part(100).add_grainline(Point(20, 50), Point(150, 50)).geometry)
    assert abs(seg.p1.x - 20.0) < 1e-3
    assert 95.0 < seg.p2.x <= 100.0
    assert abs(seg.p2.y - 50.0) < 1e-3


def test_grainline_both_outside_nudged_inward():
    seg = cast(Segment, _square_part(100).add_grainline(Point(50, -20), Point(50, 120)).geometry)
    assert 0.0 <= seg.p1.y < 5.0
    assert 95.0 < seg.p2.y <= 100.0


def test_grainline_no_outline_no_crash():
    """add_grainline on a part without an outline leaves points unchanged."""
    part = PatternPart(name="NoOutline")
    seg = cast(Segment, part.add_grainline(Point(-10, -10), Point(200, 200)).geometry)
    assert abs(seg.p1.x - (-10.0)) < 1e-9 and abs(seg.p2.x - 200.0) < 1e-9


def test_grainline_endpoint_on_boundary_not_nudged():
    """Endpoint exactly on the outline boundary must NOT be nudged (regression)."""
    seg = cast(Segment, _square_part(100).add_grainline(Point(50, 20), Point(50, 100)).geometry)
    assert abs(seg.p1.x - 50.0) < 1e-6 and abs(seg.p2.x - 50.0) < 1e-6
    assert abs(seg.p2.y - 100.0) < 1e-6 and abs(seg.p1.y - 20.0) < 1e-6


# ---------------------------------------------------------------------------
# seam_length -- free function
# ---------------------------------------------------------------------------


def test_seam_length_single_horizontal_segment():
    assert abs(seam_length([Segment(Point(0, 0), Point(100, 0))]) - 100.0) < 1e-6


def test_seam_length_two_segments_sum():
    assert (
        abs(
            seam_length([Segment(Point(0, 0), Point(30, 0)), Segment(Point(0, 0), Point(0, 40))])
            - 70.0
        )
        < 1e-6
    )


def test_seam_length_diagonal_segment():
    assert abs(seam_length([Segment(Point(0, 0), Point(30, 40))]) - 50.0) < 1e-6


def test_seam_length_cubic_bezier_straight_line():
    b = CubicBezier(Point(0, 0), Point(25, 0), Point(75, 0), Point(100, 0))
    assert abs(seam_length([b]) - 100.0) < 1e-2


def test_seam_length_mixed_segment_and_bezier():
    seg = Segment(Point(0, 0), Point(50, 0))
    bez = CubicBezier(Point(0, 0), Point(0, 25), Point(0, 75), Point(0, 100))
    assert abs(seam_length([seg, bez]) - 150.0) < 1e-2


def test_seam_length_empty_list_returns_zero():
    assert seam_length([]) == 0.0


def test_seam_length_curved_bezier_longer_than_chord():
    b = CubicBezier(Point(0, 0), Point(0, 30), Point(40, 30), Point(40, 0))
    assert seam_length([b]) > 40.0


def test_seam_length_circle_circumference():
    c = Circle(Point(0, 0), radius=10)
    assert abs(seam_length([c]) - 2 * math.pi * 10) < 1e-6


def test_seam_length_rect_perimeter():
    assert abs(seam_length([Rect(Point(0, 0), width=30, height=20)]) - 100.0) < 1e-6


def test_seam_length_triangle_perimeter():
    assert abs(seam_length([Triangle(Point(0, 0), Point(30, 0), Point(0, 40))]) - 120.0) < 1e-6


# ---------------------------------------------------------------------------
# PatternPart.seam_length()
# ---------------------------------------------------------------------------


def test_part_seam_length_by_element():
    part = PatternPart(name="Front")
    elem = part.append(Segment(Point(0, 0), Point(80, 0)), is_outline=True)
    assert abs(part.seam_length([elem]) - 80.0) < 1e-6


def test_part_seam_length_by_name():
    part = PatternPart(name="Front")
    part.append(Segment(Point(0, 0), Point(60, 0), name="Side Seam"), is_outline=True)
    assert abs(part.seam_length(["Side Seam"]) - 60.0) < 1e-6


def test_part_seam_length_multiple_named():
    part = PatternPart(name="Front")
    part.append(Segment(Point(0, 0), Point(30, 0), name="A"), is_outline=True)
    part.append(Segment(Point(0, 0), Point(0, 40), name="B"), is_outline=True)
    assert abs(part.seam_length(["A", "B"]) - 70.0) < 1e-6


def test_part_seam_length_circle_element():
    part = PatternPart(name="Pocket")
    elem = part.append(Circle(Point(0, 0), radius=10), is_outline=True)
    assert abs(part.seam_length([elem]) - 2 * math.pi * 10) < 1e-6


def test_part_seam_length_rect_element():
    part = PatternPart(name="Patch")
    elem = part.append(Rect(Point(0, 0), width=30, height=20), is_outline=True)
    assert abs(part.seam_length([elem]) - 100.0) < 1e-6


def test_part_seam_length_unmeasurable_skipped():
    """Elements whose geometry has no length (InfoBox) are silently skipped."""
    part = PatternPart(name="Front")
    seg_elem = part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True)
    info_elem = part.append(InfoBox(Point(25, 0), header="label"))
    assert abs(part.seam_length([seg_elem, info_elem]) - 50.0) < 1e-6


def test_part_seam_length_unknown_name_raises():
    import pytest

    part = PatternPart(name="Front")
    with pytest.raises(KeyError):
        part.seam_length(["DoesNotExist"])


def test_part_seam_length_wrong_type_raises():
    import pytest

    part = PatternPart(name="Front")
    with pytest.raises(TypeError):
        part.seam_length([42])  # type: ignore[list-item]


def test_part_seam_length_front_vs_back_inseam_comparison():
    front = PatternPart(name="Front")
    back = PatternPart(name="Back")
    front.append(Segment(Point(0, 0), Point(0, 200), name="Inseam"), is_outline=True)
    back.append(Segment(Point(0, 0), Point(0, 205), name="Inseam"), is_outline=True)
    diff = back.seam_length(["Inseam"]) - front.seam_length(["Inseam"])
    assert abs(diff - 5.0) < 1e-6
