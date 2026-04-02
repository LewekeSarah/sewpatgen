"""Tests for pleat.py — PleatConfig, Pleat.

Covers:
* PleatConfig field defaults, boundary validation, and error cases.
* Pleat class-level rendering constants (_ROOF_FEET, _ROOF_H).
* Pleat.build_along_seam — pleat count, positions, fold directions, point geometry.
* Pleat.apply_to — element count, per-element styles, arrow direction, roof geometry.
"""

from __future__ import annotations

import pytest

from sewpat.geometry import Point, Segment
from sewpat.pattern import PatternPart
from sewpat.pleat import Pleat, PleatConfig
from sewpat.style import STYLE_FOLD, STYLE_PLEAT_ARROW, STYLE_PLEAT_FOLD
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _straight_seam() -> Segment:
    """Horizontal reference seam from (0, 100) to (300, 100), 300 mm long."""
    return Segment(Point(0.0, 100.0), Point(300.0, 100.0))


def _curved_seam_fn(proj: float) -> Point:
    """Flat curved seam — 5 mm below the straight seam."""
    return Point(proj, 105.0)


_D_UP = Point(0.0, -1.0)  # unit vector inward (upward, negative y)


def _make_pleat(fold_left: bool = False) -> Pleat:
    """Return a Pleat with a 50 mm tall, 10 mm wide fold area for rendering tests."""
    return Pleat(
        bottom_left=Point(0.0, 50.0),
        bottom_center=Point(5.0, 50.0),
        bottom_right=Point(10.0, 50.0),
        top_left=Point(0.0, 0.0),
        top_center=Point(5.0, 0.0),
        top_right=Point(10.0, 0.0),
        fold_left=fold_left,
    )


def _apply(fold_left: bool = False) -> list:
    """Apply a test pleat to a fresh PatternPart and return its elements."""
    part = PatternPart(name="test")
    _make_pleat(fold_left).apply_to(part)
    return part.elements


# ---------------------------------------------------------------------------
# PleatConfig — valid construction
# ---------------------------------------------------------------------------


def test_pleat_config_minimal_valid() -> None:
    """PleatConfig can be constructed with only required fields."""
    cfg = PleatConfig(depth=3.0 * CM, num_pleats=2)
    assert cfg.depth == pytest.approx(3.0 * CM)
    assert cfg.num_pleats == 2


def test_pleat_config_defaults() -> None:
    """PleatConfig default values match the documented spec."""
    cfg = PleatConfig(depth=2.0 * CM, num_pleats=1)
    assert cfg.slit_offset == pytest.approx(1.5 * CM)
    assert cfg.spacing == pytest.approx(0.0)
    assert cfg.height == pytest.approx(4.0 * CM)


def test_pleat_config_zero_depth_is_valid() -> None:
    """depth=0 is allowed (produces zero-width pleats — no-op rendering)."""
    PleatConfig(depth=0.0, num_pleats=2)


def test_pleat_config_zero_num_pleats_is_valid() -> None:
    """num_pleats=0 is allowed."""
    PleatConfig(depth=2.0 * CM, num_pleats=0)


def test_pleat_config_is_frozen() -> None:
    """PleatConfig is immutable (frozen dataclass)."""
    cfg = PleatConfig(depth=2.0 * CM, num_pleats=1)
    with pytest.raises((AttributeError, TypeError)):
        cfg.depth = 3.0 * CM  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PleatConfig — field validation errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"depth": -1.0}, "depth"),
        ({"num_pleats": -1}, "num_pleats"),
        ({"slit_offset": -1.0}, "slit_offset"),
        ({"spacing": -1.0}, "spacing"),
        ({"height": 0.0}, "height"),
        ({"height": -1.0}, "height"),
    ],
)
def test_pleat_config_invalid_field_raises(overrides: dict, match: str) -> None:
    """Each out-of-range field raises ValueError mentioning the field name."""
    base: dict = {"depth": 2.0 * CM, "num_pleats": 1}
    with pytest.raises(ValueError, match=match):
        PleatConfig(**{**base, **overrides})


@pytest.mark.parametrize(
    ("num_pleats", "depth", "spacing", "raises"),
    [
        (3, 30.0, 14.0, True),  # below depth/2 → invalid
        (3, 30.0, 15.0, False),  # exactly depth/2 → boundary, valid
        (3, 30.0, 20.0, False),  # above depth/2 → valid
        (2, 30.0, 0.0, False),  # num_pleats ≤ 2 → constraint not applied
        (3, 0.0, 0.0, False),  # depth = 0 → constraint not applied
    ],
)
def test_pleat_config_spacing_constraint(
    num_pleats: int, depth: float, spacing: float, raises: bool
) -> None:
    """spacing < depth/2 with num_pleats > 2 raises ValueError; otherwise valid."""
    if raises:
        with pytest.raises(ValueError, match="spacing"):
            PleatConfig(depth=depth, num_pleats=num_pleats, spacing=spacing)
    else:
        PleatConfig(depth=depth, num_pleats=num_pleats, spacing=spacing)


# ---------------------------------------------------------------------------
# Pleat — class-level rendering constants
# ---------------------------------------------------------------------------


def test_pleat_roof_feet_values() -> None:
    """_ROOF_FEET is (6, 12, 18) mm — more spacing from seam edge."""
    assert Pleat._ROOF_FEET == (6.0, 12.0, 18.0)


def test_pleat_roof_h_value() -> None:
    """_ROOF_H is 5 mm — higher gradient for the ∧ markers."""
    assert Pleat._ROOF_H == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Pleat.build_along_seam — count and fold directions
# ---------------------------------------------------------------------------


def test_build_along_seam_returns_correct_count() -> None:
    """build_along_seam returns num_pleats Pleat objects."""
    cfg = PleatConfig(depth=30.0, num_pleats=2)
    pleats = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)
    assert len(pleats) == 2


def test_build_along_seam_zero_pleats_returns_empty() -> None:
    """num_pleats=0 produces an empty list — right pleat is guarded by num_pleats >= 1."""
    cfg = PleatConfig(depth=30.0, num_pleats=0)
    pleats = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)
    assert pleats == []


def test_build_along_seam_first_pleat_folds_right() -> None:
    """The first pleat (right of slit) always has fold_left=False."""
    cfg = PleatConfig(depth=30.0, num_pleats=2)
    pleats = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)
    assert pleats[0].fold_left is False


def test_build_along_seam_left_pleats_fold_left() -> None:
    """All pleats after the first have fold_left=True."""
    cfg = PleatConfig(depth=30.0, num_pleats=3, spacing=15.0)
    pleats = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)
    assert all(p.fold_left is True for p in pleats[1:])


# ---------------------------------------------------------------------------
# Pleat.build_along_seam — right-pleat geometry
# ---------------------------------------------------------------------------
# anchor=150, slit_offset=15 (default), depth=30, half=15
# Right-pleat centre = 150 + 15 + 15 = 180
# left_proj=165, centre_proj=180, right_proj=195


def test_build_right_pleat_bottom_center_on_curved_seam() -> None:
    """Right-pleat bottom_center is the curved_seam_fn evaluated at centre_proj."""
    cfg = PleatConfig(depth=30.0, num_pleats=2)
    p = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)[0]
    assert p.bottom_center.x == pytest.approx(180.0)
    assert p.bottom_center.y == pytest.approx(105.0)


def test_build_right_pleat_bottom_left_on_curved_seam() -> None:
    """Right-pleat bottom_left is the curved_seam_fn at centre − half."""
    cfg = PleatConfig(depth=30.0, num_pleats=2)
    p = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)[0]
    assert p.bottom_left.x == pytest.approx(165.0)
    assert p.bottom_left.y == pytest.approx(105.0)


def test_build_right_pleat_bottom_right_on_curved_seam() -> None:
    """Right-pleat bottom_right is the curved_seam_fn at centre + half."""
    cfg = PleatConfig(depth=30.0, num_pleats=2)
    p = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)[0]
    assert p.bottom_right.x == pytest.approx(195.0)
    assert p.bottom_right.y == pytest.approx(105.0)


def test_build_right_pleat_top_center_at_correct_height() -> None:
    """Right-pleat top_center is on the straight seam raised by height (default 4 cm)."""
    cfg = PleatConfig(depth=30.0, num_pleats=2)
    p = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)[0]
    # straight seam y = 100, height = 4 cm = 40 mm, d_up = (0, -1)
    assert p.top_center.x == pytest.approx(180.0)
    assert p.top_center.y == pytest.approx(100.0 - 40.0)


# ---------------------------------------------------------------------------
# Pleat.build_along_seam — left-pleat positions
# ---------------------------------------------------------------------------
# anchor=150, slit_offset=15, depth=30, half=15, step=45 (depth+spacing=30+15)
# Left pleat 1: centre = 150 − 15 − 15 = 120
# Left pleat 2: centre = 150 − 15 − 15 − 45 = 75


def test_build_left_pleat1_center_projection() -> None:
    """First left pleat is centred at anchor − slit_offset − half."""
    cfg = PleatConfig(depth=30.0, num_pleats=3, spacing=15.0)
    pleats = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)
    assert pleats[1].bottom_center.x == pytest.approx(120.0)


def test_build_left_pleat2_center_projection() -> None:
    """Second left pleat steps one depth+spacing further left."""
    cfg = PleatConfig(depth=30.0, num_pleats=3, spacing=15.0)
    pleats = Pleat.build_along_seam(cfg, _straight_seam(), _curved_seam_fn, 150.0, _D_UP)
    assert pleats[2].bottom_center.x == pytest.approx(75.0)


# ---------------------------------------------------------------------------
# Pleat.apply_to — element count
# ---------------------------------------------------------------------------
# fold_h = 50 mm → all 3 roofs fit (apex at 11, 17, 23 mm — all < 50 mm)
# Expected: 3 fold lines + 1 arrow + 6 roof segments = 10 elements


def test_apply_to_total_element_count() -> None:
    """apply_to appends exactly 10 elements: 3 fold + 1 arrow + 6 roof."""
    assert len(_apply()) == 10


def test_apply_to_short_fold_no_roofs() -> None:
    """A fold line shorter than the first apex height produces no roof markers."""
    # fold_h = 10 mm < apex_h = 11 mm for first roof → no roofs
    pleat = Pleat(
        bottom_left=Point(0.0, 10.0),
        bottom_center=Point(5.0, 10.0),
        bottom_right=Point(10.0, 10.0),
        top_left=Point(0.0, 0.0),
        top_center=Point(5.0, 0.0),
        top_right=Point(10.0, 0.0),
        fold_left=False,
    )
    part = PatternPart(name="test")
    pleat.apply_to(part)
    # 3 fold lines + 1 arrow + 0 roof segments = 4
    assert len(part.elements) == 4


# ---------------------------------------------------------------------------
# Pleat.apply_to — fold-line style
# ---------------------------------------------------------------------------


def test_apply_to_fold_lines_use_style_fold() -> None:
    """The three fold lines use STYLE_FOLD (grey dashed)."""
    elements = _apply()
    for elem in elements[:3]:
        assert elem.style == STYLE_FOLD


# ---------------------------------------------------------------------------
# Pleat.apply_to — arrow style and direction
# ---------------------------------------------------------------------------


def test_apply_to_arrow_uses_style_pleat_arrow() -> None:
    """The direction arrow uses STYLE_PLEAT_ARROW."""
    assert _apply()[3].style == STYLE_PLEAT_ARROW


def test_apply_to_arrow_fold_right_start_is_top_left() -> None:
    """fold_left=False: arrow starts at top_left (outer-opposite edge)."""
    pleat = _make_pleat(fold_left=False)
    elem = _apply(fold_left=False)[3]
    assert elem.geometry.p1.x == pytest.approx(pleat.top_left.x)
    assert elem.geometry.p1.y == pytest.approx(pleat.top_left.y)


def test_apply_to_arrow_fold_right_end_is_top_right() -> None:
    """fold_left=False: arrow ends at top_right (fold-direction edge)."""
    pleat = _make_pleat(fold_left=False)
    elem = _apply(fold_left=False)[3]
    assert elem.geometry.p2.x == pytest.approx(pleat.top_right.x)
    assert elem.geometry.p2.y == pytest.approx(pleat.top_right.y)


def test_apply_to_arrow_fold_left_start_is_top_right() -> None:
    """fold_left=True: arrow starts at top_right (outer-opposite edge)."""
    pleat = _make_pleat(fold_left=True)
    elem = _apply(fold_left=True)[3]
    assert elem.geometry.p1.x == pytest.approx(pleat.top_right.x)
    assert elem.geometry.p1.y == pytest.approx(pleat.top_right.y)


def test_apply_to_arrow_fold_left_end_is_top_left() -> None:
    """fold_left=True: arrow ends at top_left (fold-direction edge)."""
    pleat = _make_pleat(fold_left=True)
    elem = _apply(fold_left=True)[3]
    assert elem.geometry.p2.x == pytest.approx(pleat.top_left.x)
    assert elem.geometry.p2.y == pytest.approx(pleat.top_left.y)


# ---------------------------------------------------------------------------
# Pleat.apply_to — roof-marker style and geometry
# ---------------------------------------------------------------------------
# seg_l: (0,50)→(0,0), seg_c: (5,50)→(5,0), seg_r: (10,50)→(10,0), fold_h=50
#
# Roof 1 (foot_h=6, apex_h=11):  t_foot=0.12,  t_apex=0.22
#   foot_l=(0,44), apex=(5,39), foot_r=(10,44)
# Roof 2 (foot_h=12, apex_h=17): t_foot=0.24,  t_apex=0.34
#   foot_l=(0,38), apex=(5,33), foot_r=(10,38)
# Roof 3 (foot_h=18, apex_h=23): t_foot=0.36,  t_apex=0.46
#   foot_l=(0,32), apex=(5,27), foot_r=(10,32)


def test_apply_to_roof_markers_use_style_pleat_fold() -> None:
    """All six roof-marker segments use STYLE_PLEAT_FOLD (solid black)."""
    elements = _apply()
    for elem in elements[4:]:
        assert elem.style == STYLE_PLEAT_FOLD


def test_apply_to_roof1_foot_height() -> None:
    """First roof feet are _ROOF_FEET[0]=6 mm above the seam edge."""
    elements = _apply()
    # elem[4] = left half of roof 1: Segment(foot_l, apex)
    assert elements[4].geometry.p1.y == pytest.approx(50.0 - 6.0)  # foot_l y


def test_apply_to_roof1_apex_height() -> None:
    """First roof apex is _ROOF_FEET[0] + _ROOF_H = 11 mm above the seam edge."""
    elements = _apply()
    assert elements[4].geometry.p2.y == pytest.approx(50.0 - 11.0)  # apex y


def test_apply_to_roof2_foot_height() -> None:
    """Second roof feet are _ROOF_FEET[1]=12 mm above the seam edge."""
    elements = _apply()
    assert elements[6].geometry.p1.y == pytest.approx(50.0 - 12.0)


def test_apply_to_roof3_foot_height() -> None:
    """Third roof feet are _ROOF_FEET[2]=18 mm above the seam edge."""
    elements = _apply()
    assert elements[8].geometry.p1.y == pytest.approx(50.0 - 18.0)


def test_apply_to_roof1_foot_x_positions() -> None:
    """Roof 1 feet lie on the left and right fold lines (correct x)."""
    elements = _apply()
    foot_l_x = elements[4].geometry.p1.x  # left half p1 = foot_l
    foot_r_x = elements[5].geometry.p2.x  # right half p2 = foot_r
    assert foot_l_x == pytest.approx(0.0)
    assert foot_r_x == pytest.approx(10.0)


def test_apply_to_roof1_apex_on_center_fold_line() -> None:
    """Roof 1 apex lies on the centre fold line (x = 5)."""
    elements = _apply()
    apex_x = elements[4].geometry.p2.x  # left half p2 = apex
    assert apex_x == pytest.approx(5.0)
