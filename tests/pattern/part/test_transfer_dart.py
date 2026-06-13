"""Tests for :func:`sewpat.pattern._dart_transform.transfer_dart` (Step 5 of
``docs/guides/dart_transformation_plan.md``).

Fixture geometry mirrors ``examples/darts/dart_toy_reference_point.py``,
anchored at the origin for simplicity:

    corners: A=(0,0)  B=(120,0)  C=(120,180)  D=(0,180)
    dart:    tip=(45,65)  leg_a=(120,79)  leg_b=(120,51)  on the right edge

The dart is transferred along ``cut_direction=(0, 1)`` (straight up from the
tip), which crosses the top edge — the same configuration used in the toy
example.
"""

import math

import numpy as np
import pytest
import shapely.geometry as sg

from sewpat.element import PatternElement
from sewpat.geometry import (
    CubicBezier,
    Dart,
    DartType,
    Point,
    Ray,
    Segment,
    Triangle,
    outline_polygon,
)
from sewpat.geometry._algorithms import _normalize_vector, _signed_angle
from sewpat.pattern import PatternPart
from sewpat.pattern._dart_transform import _cutline_outline_intersection


def _rect_with_dart() -> tuple[PatternPart, Dart]:
    """120x180mm rectangle with a triangle dart on the right edge."""
    part = PatternPart(name="Rectangle")
    a, b, c, d = Point(0, 0), Point(120, 0), Point(120, 180), Point(0, 180)
    part.append(Segment(a, d), is_outline=True)  # left
    part.append(Segment(d, c), is_outline=True)  # top
    right = part.append(Segment(c, b), is_outline=True)  # right
    part.append(Segment(b, a), is_outline=True)  # bottom

    bust_point = Point(45, 65)
    t_bust = (bust_point.y - c.y) / (b.y - c.y)
    dart = Dart.from_edge_free_tip(
        right,
        t=t_bust,
        width=28,
        reference_point=bust_point,
        tip_shortfall=0,
        dart_type=DartType.TRIANGLE,
        name="Test Dart",
    )
    part.add_dart(dart)
    return part, dart


@pytest.fixture
def rect_with_dart() -> tuple[PatternPart, Dart]:
    return _rect_with_dart()


@pytest.fixture
def rect_with_dart_and_sa() -> tuple[PatternPart, Dart]:
    part, dart = _rect_with_dart()
    part.add_seam_allowance(10)
    return part, dart


def _roof_area_mm2(dart: Dart) -> float:
    """Shoelace area of the quad (tip, leg_a, roof, leg_b) in mm²."""
    pts = [dart.tip, dart.leg_a, dart.roof, dart.leg_b]
    area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i].x, pts[i].y
        x2, y2 = pts[(i + 1) % len(pts)].x, pts[(i + 1) % len(pts)].y
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _sa_geoms(part: PatternPart) -> list[Segment | CubicBezier]:
    return [
        e.geometry
        for e in part.elements
        if e.is_seam_allowance and isinstance(e.geometry, (Segment, CubicBezier))
    ]


# ---------------------------------------------------------------------------
# Precondition: cut_line must pass through dart.tip
# ---------------------------------------------------------------------------


def test_transfer_dart_raises_when_cut_line_misses_tip(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    # Vertical ray 10 mm to the right of the tip — well outside the 1 mm tolerance.
    bad_ray = Ray(dart.tip + Point(10, 0), (0.0, 1.0))

    with pytest.raises(ValueError, match="dart.tip"):
        part.transfer_dart(dart, bad_ray)


def test_transfer_dart_accepts_cut_line_within_tolerance(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    # 0.5 mm off — inside the 1 mm tolerance, must not raise.
    near_ray = Ray(dart.tip + Point(0.5, 0), (0.0, 1.0))

    part.transfer_dart(dart, near_ray)  # should not raise


# ---------------------------------------------------------------------------
# Returned Dart: tip, legs, intake angle
# ---------------------------------------------------------------------------


def test_transfer_dart_preserves_tip_name_and_intake_angle(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    new_dart = part.transfer_dart(dart, cut_ray)

    assert new_dart.tip == dart.tip
    assert new_dart.name == dart.name
    assert new_dart.dart_type == dart.dart_type
    assert new_dart.intake_angle == pytest.approx(dart.intake_angle, abs=1e-6)
    assert new_dart.width > 0
    assert new_dart.depth > 0


def test_transfer_dart_new_legs_lie_on_outline(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    new_dart = part.transfer_dart(dart, cut_ray)

    poly = part._outline_polygon()
    assert poly is not None
    boundary = poly.exterior
    for leg in (new_dart.leg_a, new_dart.leg_b):
        assert boundary.distance(sg.Point(leg.x, leg.y)) < 1e-6


# ---------------------------------------------------------------------------
# Dart count invariant + stale-element cleanup
# ---------------------------------------------------------------------------


def test_transfer_dart_preserves_dart_count(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    legs_before, tip_before = part.get_dart(dart.name)
    assert len(legs_before) == 2
    assert tip_before is not None

    new_dart = part.transfer_dart(dart, cut_ray)

    legs_after, tip_after = part.get_dart(new_dart.name)
    assert len(legs_after) == 2
    assert tip_after is not None
    assert tip_after == new_dart.tip


def test_transfer_dart_removes_cutline_element(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    part.transfer_dart(dart, cut_ray)

    assert not any(e.role == "cutline" for e in part.elements)


def test_transfer_dart_leaves_one_dart_worth_of_tip_markers(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    """The old dart's tip markers are removed and exactly one new set is added."""
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    tip_elems_before = [e for e in part.elements if e.role == "dart_tip"]
    assert tip_elems_before  # precision_tip=True by default -> circles + label

    part.transfer_dart(dart, cut_ray)

    tip_elems_after = [e for e in part.elements if e.role == "dart_tip"]
    assert len(tip_elems_after) == len(tip_elems_before)


# ---------------------------------------------------------------------------
# Outline validity after transfer
# ---------------------------------------------------------------------------


def test_transfer_dart_outline_is_single_valid_polygon(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    part.transfer_dart(dart, cut_ray)

    poly = part._outline_polygon()
    assert poly is not None
    assert poly.is_valid
    assert poly.exterior.is_simple


# ---------------------------------------------------------------------------
# Outline area accounting
# ---------------------------------------------------------------------------


def test_transfer_dart_area_accounting(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    area_before = part.area_cm2
    roof_before_cm2 = _roof_area_mm2(dart) / 100.0
    assert area_before is not None

    new_dart = part.transfer_dart(dart, cut_ray)

    area_after = part.area_cm2
    roof_after_cm2 = _roof_area_mm2(new_dart) / 100.0
    assert area_after is not None

    assert (area_after - area_before) == pytest.approx(roof_after_cm2 - roof_before_cm2, abs=1e-6)


# ---------------------------------------------------------------------------
# Old dart closes: rotating the inner leg by rotation_angle lands on the
# outer leg (within 1 mm) -- the "Old dart closed" check from the Step 4 table.
# ---------------------------------------------------------------------------


def test_old_dart_closes_under_rotation_angle(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    _part, dart = rect_with_dart
    tip = dart.tip
    cut_dir = np.array([0.0, 1.0])

    dir_a = _normalize_vector(np.array(dart.leg_a.coords - tip.coords, dtype=float))
    dir_b = _normalize_vector(np.array(dart.leg_b.coords - tip.coords, dtype=float))

    angle_a = _signed_angle(dir_a, cut_dir)
    angle_b = _signed_angle(dir_b, cut_dir)

    if abs(angle_a) <= abs(angle_b):
        inner, outer, inner_dir, outer_dir = dart.leg_a, dart.leg_b, dir_a, dir_b
    else:
        inner, outer, inner_dir, outer_dir = dart.leg_b, dart.leg_a, dir_b, dir_a

    rotation_angle = _signed_angle(inner_dir, outer_dir)

    # |rotation_angle| matches the dart's intake angle (3a invariant).
    assert abs(rotation_angle) == pytest.approx(dart.intake_angle, abs=1e-6)

    rotated_inner = inner.rotate(tip, rotation_angle)
    assert rotated_inner.distance_to(outer) < 1.0


# ---------------------------------------------------------------------------
# Stitch length preserved: add_cutline (step 3b) does not change total
# outline length -- it only adds a split vertex.
# ---------------------------------------------------------------------------


def test_add_cutline_preserves_total_outline_length(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    length_before = sum(g.length for g in part._outline_geoms())
    part.add_cutline(cut_ray)
    length_after = sum(g.length for g in part._outline_geoms())

    assert length_after == pytest.approx(length_before, abs=1e-9)


# ---------------------------------------------------------------------------
# Seam allowance regeneration
# ---------------------------------------------------------------------------


def test_transfer_dart_regenerates_seam_allowance(
    rect_with_dart_and_sa: tuple[PatternPart, Dart],
) -> None:
    part, dart = rect_with_dart_and_sa
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    sa_poly_before = outline_polygon(_sa_geoms(part))
    assert sa_poly_before is not None

    part.transfer_dart(dart, cut_ray, sa_distance=10)

    sa_geoms_after = _sa_geoms(part)
    assert sa_geoms_after

    sa_poly_after = outline_polygon(sa_geoms_after)
    assert sa_poly_after is not None
    assert sa_poly_after.is_valid

    # The new dart has a different depth, so the regenerated SA differs from
    # the stale one that was generated for the old dart position.
    assert sa_poly_after.area != pytest.approx(sa_poly_before.area, rel=1e-6)

    outline_poly_after = part._outline_polygon()
    assert outline_poly_after is not None
    assert sa_poly_after.area > outline_poly_after.area


def test_transfer_dart_without_sa_distance_leaves_stale_seam_allowance(
    rect_with_dart_and_sa: tuple[PatternPart, Dart],
) -> None:
    """Without ``sa_distance``, step 3g is skipped and the old SA is not rebuilt.

    The dart's mouth has moved, so the leftover SA (generated for the old
    outline) is no longer a valid offset of the new outline -- this is the
    motivating reason for the ``sa_distance`` kwarg and step 3g.
    """
    part, dart = rect_with_dart_and_sa
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    sa_before = _sa_geoms(part)
    assert sa_before

    part.transfer_dart(dart, cut_ray)  # sa_distance=None -> 3g skipped

    sa_poly_after = outline_polygon(_sa_geoms(part))
    assert sa_poly_after is not None
    assert not (sa_poly_after.is_valid and sa_poly_after.exterior.is_simple)


# ---------------------------------------------------------------------------
# 3a: leg_b selected as the inner leg when it is closer to cut_dir
# ---------------------------------------------------------------------------


def test_transfer_dart_leg_b_is_inner_leg_for_downward_cut(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    """When leg_b is closer to cut_dir than leg_a, leg_b is the inner leg."""
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, -1.0))

    new_dart = part.transfer_dart(dart, cut_ray)

    assert new_dart.tip == dart.tip
    assert new_dart.intake_angle == pytest.approx(dart.intake_angle, abs=1e-6)

    poly = part._outline_polygon()
    assert poly is not None
    assert poly.is_valid
    assert poly.exterior.is_simple

    boundary = poly.exterior
    for leg in (new_dart.leg_a, new_dart.leg_b):
        assert boundary.distance(sg.Point(leg.x, leg.y)) < 1e-6


# ---------------------------------------------------------------------------
# 3e: no outline intersection for the new dart leg -> ValueError
# ---------------------------------------------------------------------------


def test_transfer_dart_raises_when_no_outline_intersection(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    """A cut_line too short to reach the outline raises ValueError."""
    part, dart = rect_with_dart
    short_cut = Segment(dart.tip, dart.tip + Point(1, 0))

    with pytest.raises(ValueError, match="could not find outline intersection"):
        part.transfer_dart(dart, short_cut)


# ---------------------------------------------------------------------------
# 3d: attached reference points (_sa_center / _leg_pt) are rotated too
# ---------------------------------------------------------------------------


def test_transfer_dart_rotates_sa_center_and_leg_pt(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    """Elements carrying ``_sa_center``/``_leg_pt`` are rotated in step 3d."""
    part, dart = rect_with_dart
    tip = dart.tip
    cut_ray = Ray(tip, (0.0, 1.0))

    # rep_point at 45 degrees from tip falls inside the rotation sector
    # (between leg_a's direction ~10.57 deg and cut_dir at 90 deg).
    rep = tip + Point(50 * math.cos(math.radians(45)), 50 * math.sin(math.radians(45)))
    sa_center = Point(10, 20)
    leg_pt = Point(30, 40)
    synthetic = PatternElement(rep)
    synthetic._sa_center = sa_center
    synthetic._leg_pt = leg_pt
    part.elements.append(synthetic)

    dir_a = _normalize_vector(np.array(dart.leg_a.coords - tip.coords, dtype=float))
    dir_b = _normalize_vector(np.array(dart.leg_b.coords - tip.coords, dtype=float))
    angle_a = _signed_angle(dir_a, (0.0, 1.0))
    angle_b = _signed_angle(dir_b, (0.0, 1.0))
    inner_dir, outer_dir = (dir_a, dir_b) if abs(angle_a) <= abs(angle_b) else (dir_b, dir_a)
    rotation_angle = _signed_angle(inner_dir, outer_dir)

    part.transfer_dart(dart, cut_ray)

    assert synthetic._sa_center == sa_center.rotate(tip, rotation_angle)
    assert synthetic._leg_pt == leg_pt.rotate(tip, rotation_angle)


# ---------------------------------------------------------------------------
# 3f: notch_length / notch_width forwarded to add_dart
# ---------------------------------------------------------------------------


def test_transfer_dart_forwards_notch_length_and_width(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    """notch_length and notch_width kwargs are forwarded to add_dart."""
    part, dart = rect_with_dart
    cut_ray = Ray(dart.tip, (0.0, 1.0))

    part.transfer_dart(dart, cut_ray, notch_length=6.0, notch_width=2.5)

    notches = [e.geometry for e in part.elements if e.role == "dart_notch"]
    assert notches
    for tri in notches:
        assert isinstance(tri, Triangle)
        assert tri.p1.distance_to(tri.p2) == pytest.approx(2.5)
        assert tri.base_midpoint.distance_to(tri.p3) == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# _cutline_outline_intersection: skip Dart geometry, ignore unsupported pairs
# ---------------------------------------------------------------------------


def test_cutline_outline_intersection_skips_dart_and_intersect_errors(
    rect_with_dart: tuple[PatternPart, Dart],
) -> None:
    """Dart outline elements are skipped and unsupported intersect() pairs are ignored."""
    part, dart = rect_with_dart
    tip = dart.tip

    # A Dart-geometry outline element is skipped outright.
    part.elements.append(PatternElement(dart, is_outline=True))
    # intersect(Ray, Triangle) raises TypeError -- caught and skipped.
    part.elements.append(
        PatternElement(Triangle(Point(0, 0), Point(1, 0), Point(0, 1)), is_outline=True)
    )

    cut_ray = Ray(tip, (0.0, 1.0))
    result = _cutline_outline_intersection(cut_ray, part, tip)

    assert result is not None
    pt, elem = result
    assert isinstance(elem.geometry, Segment)
    assert pt.x == pytest.approx(45)
    assert pt.y == pytest.approx(180)
