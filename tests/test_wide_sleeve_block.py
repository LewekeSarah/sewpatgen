"""Tests for WideSleeveBlock and CuffBlock (blocks.py + sleeve/cuff geometry)."""

import dataclasses

import pytest

from sewpat.blocks import CuffBlock, WideSleeveBlock
from sewpat.geometry import CubicBezier, Point, Segment
from sewpat.grids import WideSleeveGrid
from sewpat.pleat import Pleat, PleatConfig
from sewpat.sleeve import (
    ButtonConfig,
    CuffConfig,
    SleeveArmhole,
    SleeveConfig,
    SleeveMeasurements,
)
from sewpat.units import CM

# ---------------------------------------------------------------------------
# WideSleeveBlock — type checks
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_is_instance(wide_sleeve_block: WideSleeveBlock) -> None:
    """from_armhole returns a WideSleeveBlock instance."""
    assert isinstance(wide_sleeve_block, WideSleeveBlock)


def test_wide_sleeve_block_has_pattern_part(wide_sleeve_block: WideSleeveBlock) -> None:
    """WideSleeveBlock exposes a non-empty PatternPart."""
    assert wide_sleeve_block.part is not None
    assert len(wide_sleeve_block.part.elements) > 0


def test_wide_sleeve_block_has_wide_sleeve_grid(wide_sleeve_block: WideSleeveBlock) -> None:
    """WideSleeveBlock.grid is a WideSleeveGrid instance."""
    assert isinstance(wide_sleeve_block.grid, WideSleeveGrid)


# ---------------------------------------------------------------------------
# WideSleeveBlock — key points
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_cap_crown_is_point(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_crown is a Point."""
    assert isinstance(wide_sleeve_block.cap_crown, Point)


def test_wide_sleeve_block_cap_left_is_point(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_left is a Point."""
    assert isinstance(wide_sleeve_block.cap_left, Point)


def test_wide_sleeve_block_cap_right_is_point(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_right is a Point."""
    assert isinstance(wide_sleeve_block.cap_right, Point)


def test_wide_sleeve_block_hem_left_is_point(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem_left is a Point."""
    assert isinstance(wide_sleeve_block.hem_left, Point)


def test_wide_sleeve_block_hem_right_is_point(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem_right is a Point."""
    assert isinstance(wide_sleeve_block.hem_right, Point)


def test_wide_sleeve_block_cap_crown_above_cap_points(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_crown y-coordinate is above (less than) cap_left and cap_right (SVG y-axis)."""
    assert wide_sleeve_block.cap_crown.y < wide_sleeve_block.cap_left.y
    assert wide_sleeve_block.cap_crown.y < wide_sleeve_block.cap_right.y


def test_wide_sleeve_block_hem_below_cap(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem_left is below cap_left (greater y value)."""
    assert wide_sleeve_block.hem_left.y > wide_sleeve_block.cap_left.y


# ---------------------------------------------------------------------------
# WideSleeveBlock — geometry types
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_cap_left_slope_is_segment(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_left_slope is a Segment (straight construction triangle leg)."""
    assert isinstance(wide_sleeve_block.cap_left_slope, Segment)


def test_wide_sleeve_block_cap_right_slope_is_segment(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_right_slope is a Segment (straight construction triangle leg)."""
    assert isinstance(wide_sleeve_block.cap_right_slope, Segment)


def test_wide_sleeve_block_cap_left_curve_is_bezier(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_left_curve is a CubicBezier (S-curve stitching line)."""
    assert isinstance(wide_sleeve_block.cap_left_curve, CubicBezier)


def test_wide_sleeve_block_cap_right_curve_is_bezier(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_right_curve is a CubicBezier (S-curve stitching line)."""
    assert isinstance(wide_sleeve_block.cap_right_curve, CubicBezier)


def test_wide_sleeve_block_left_side_is_bezier(wide_sleeve_block: WideSleeveBlock) -> None:
    """left_side is a CubicBezier (gently curved side seam)."""
    assert isinstance(wide_sleeve_block.left_side, CubicBezier)


def test_wide_sleeve_block_right_side_is_bezier(wide_sleeve_block: WideSleeveBlock) -> None:
    """right_side is a CubicBezier (gently curved side seam)."""
    assert isinstance(wide_sleeve_block.right_side, CubicBezier)


def test_wide_sleeve_block_hem_is_segment(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem is a Segment (straight construction reference)."""
    assert isinstance(wide_sleeve_block.hem, Segment)


def test_wide_sleeve_block_hem_left_curve_is_bezier(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem_left_curve is a CubicBezier (shaped hem stitch line, left half)."""
    assert isinstance(wide_sleeve_block.hem_left_curve, CubicBezier)


def test_wide_sleeve_block_hem_right_curve_is_bezier(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem_right_curve is a CubicBezier (shaped hem stitch line, right half)."""
    assert isinstance(wide_sleeve_block.hem_right_curve, CubicBezier)


# ---------------------------------------------------------------------------
# WideSleeveBlock — symmetry
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_cap_points_symmetric(wide_sleeve_block: WideSleeveBlock) -> None:
    """cap_left and cap_right are symmetric around the centre fold (equal y-coords)."""
    assert wide_sleeve_block.cap_left.y == pytest.approx(wide_sleeve_block.cap_right.y, abs=0.1)


def test_wide_sleeve_block_hem_points_symmetric(wide_sleeve_block: WideSleeveBlock) -> None:
    """hem_left and hem_right share the same y-coordinate (horizontal hem line)."""
    assert wide_sleeve_block.hem_left.y == pytest.approx(wide_sleeve_block.hem_right.y, abs=0.1)


def test_wide_sleeve_block_cap_width_equals_twice_sleeve_width(
    wide_sleeve_block: WideSleeveBlock,
) -> None:
    """Distance between cap_left and cap_right equals 2 × grid.sleeve_width."""
    cap_span = abs(wide_sleeve_block.cap_right.x - wide_sleeve_block.cap_left.x)
    assert cap_span == pytest.approx(2 * wide_sleeve_block.grid.sleeve_width, rel=1e-4)


# ---------------------------------------------------------------------------
# WideSleeveBlock — slit (config has slit_height=8 cm)
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_slit_is_segment(wide_sleeve_block: WideSleeveBlock) -> None:
    """slit is a Segment when slit_height is set in the config."""
    assert isinstance(wide_sleeve_block.slit, Segment)


def test_wide_sleeve_block_slit_height_matches_config(
    wide_sleeve_block: WideSleeveBlock,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """Slit segment length matches SleeveConfig.slit_height."""
    assert wide_sleeve_block.slit is not None
    assert sleeve_config_with_cuff.slit_height is not None
    slit_len = wide_sleeve_block.slit.p1.distance_to(wide_sleeve_block.slit.p2)
    assert slit_len == pytest.approx(sleeve_config_with_cuff.slit_height, rel=1e-4)


# ---------------------------------------------------------------------------
# WideSleeveBlock — no-slit path
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_no_slit_when_not_configured(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """slit is None when SleeveConfig has no slit_height."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    block = WideSleeveBlock.from_armhole(sleeve_armhole, cfg)
    assert block.slit is None


# ---------------------------------------------------------------------------
# WideSleeveBlock — pleats (config has 3 pleats)
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_pleats_count(
    wide_sleeve_block: WideSleeveBlock,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """Number of pleats matches PleatConfig.num_pleats."""
    assert sleeve_config_with_cuff.pleat_config is not None
    assert len(wide_sleeve_block.pleats) == sleeve_config_with_cuff.pleat_config.num_pleats


def test_wide_sleeve_block_pleats_are_pleat_instances(wide_sleeve_block: WideSleeveBlock) -> None:
    """Every entry in pleats is a Pleat instance."""
    for pleat in wide_sleeve_block.pleats:
        assert isinstance(pleat, Pleat)


def test_wide_sleeve_block_no_pleats_when_not_configured(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """pleats is empty when SleeveConfig has no pleat_config."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    block = WideSleeveBlock.from_armhole(sleeve_armhole, cfg)
    assert block.pleats == ()


# ---------------------------------------------------------------------------
# WideSleeveBlock — cuff present (config has cuff_config)
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_cuff_is_cuff_block(wide_sleeve_block: WideSleeveBlock) -> None:
    """cuff is a CuffBlock when cuff_config is set."""
    assert isinstance(wide_sleeve_block.cuff, CuffBlock)


def test_wide_sleeve_block_no_cuff_when_not_configured(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """cuff is None when SleeveConfig has no cuff_config."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    block = WideSleeveBlock.from_armhole(sleeve_armhole, cfg)
    assert block.cuff is None


# ---------------------------------------------------------------------------
# CuffBlock — type and geometry
# ---------------------------------------------------------------------------


def test_cuff_block_is_instance(cuff_block: CuffBlock) -> None:
    """CuffBlock.from_sleeve_config returns a CuffBlock instance."""
    assert isinstance(cuff_block, CuffBlock)


def test_cuff_block_has_pattern_part(cuff_block: CuffBlock) -> None:
    """CuffBlock.part is non-empty."""
    assert cuff_block.part is not None
    assert len(cuff_block.part.elements) > 0


def test_cuff_block_length_matches_config(
    cuff_block: CuffBlock,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """cuff_length matches CuffConfig.length."""
    assert sleeve_config_with_cuff.cuff_config is not None
    assert cuff_block.cuff_length == pytest.approx(sleeve_config_with_cuff.cuff_config.length)


def test_cuff_block_height_matches_config(
    cuff_block: CuffBlock,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """cuff_height matches CuffConfig.width (single folded height)."""
    assert sleeve_config_with_cuff.cuff_config is not None
    assert cuff_block.cuff_height == pytest.approx(sleeve_config_with_cuff.cuff_config.width)


def test_cuff_block_underlap_matches_config(
    cuff_block: CuffBlock,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """CuffBlock.underlap matches CuffConfig.underlap."""
    assert sleeve_config_with_cuff.cuff_config is not None
    assert cuff_block.underlap == pytest.approx(sleeve_config_with_cuff.cuff_config.underlap)


def test_cuff_block_overlap_matches_config(
    cuff_block: CuffBlock,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """CuffBlock.overlap matches CuffConfig.overlap."""
    assert sleeve_config_with_cuff.cuff_config is not None
    assert cuff_block.overlap == pytest.approx(sleeve_config_with_cuff.cuff_config.overlap)


def test_cuff_block_corner_geometry(cuff_block: CuffBlock) -> None:
    """top_left and bottom_right define the full cut rectangle."""
    full_width = cuff_block.cuff_length + cuff_block.underlap + cuff_block.overlap
    full_height = 2.0 * cuff_block.cuff_height
    actual_width = abs(cuff_block.top_right.x - cuff_block.top_left.x)
    actual_height = abs(cuff_block.bottom_left.y - cuff_block.top_left.y)
    assert actual_width == pytest.approx(full_width, rel=1e-4)
    assert actual_height == pytest.approx(full_height, rel=1e-4)


def test_cuff_block_fold_line_at_mid_height(cuff_block: CuffBlock) -> None:
    """fold_left.y is exactly at the midpoint between top_left.y and bottom_left.y."""
    mid_y = (cuff_block.top_left.y + cuff_block.bottom_left.y) / 2.0
    assert cuff_block.fold_left.y == pytest.approx(mid_y, abs=0.1)


def test_cuff_block_returns_none_without_cuff_config(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """CuffBlock.from_sleeve_config returns None when SleeveConfig has no cuff_config."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    assert CuffBlock.from_sleeve_config(cfg) is None


# ---------------------------------------------------------------------------
# ButtonConfig — validation
# ---------------------------------------------------------------------------


def test_button_config_valid_defaults() -> None:
    """ButtonConfig with default values constructs without error."""
    cfg = ButtonConfig()
    assert cfg.num_buttons == 1
    assert cfg.button_diameter == pytest.approx(10.0)
    assert cfg.margin == pytest.approx(10.0)
    assert cfg.buttonhole_ease == pytest.approx(2.0)


@pytest.mark.parametrize("n", [0, 1, 2])
def test_button_config_accepts_valid_num_buttons(n: int) -> None:
    """ButtonConfig accepts num_buttons 0, 1, or 2."""
    cfg = ButtonConfig(num_buttons=n)
    assert cfg.num_buttons == n


@pytest.mark.parametrize("n", [-1, 3, 10])
def test_button_config_rejects_invalid_num_buttons(n: int) -> None:
    """ButtonConfig rejects num_buttons outside {0, 1, 2}."""
    with pytest.raises(ValueError, match="num_buttons"):
        ButtonConfig(num_buttons=n)


def test_button_config_rejects_nonpositive_diameter() -> None:
    """ButtonConfig rejects button_diameter <= 0."""
    with pytest.raises(ValueError, match="button_diameter"):
        ButtonConfig(button_diameter=0.0)


def test_button_config_rejects_negative_margin() -> None:
    """ButtonConfig rejects margin < 10 mm."""
    with pytest.raises(ValueError, match="margin"):
        ButtonConfig(margin=9.9)


def test_button_config_rejects_negative_buttonhole_ease() -> None:
    """ButtonConfig rejects buttonhole_ease < 0."""
    with pytest.raises(ValueError, match="buttonhole_ease"):
        ButtonConfig(buttonhole_ease=-0.1)


def test_button_config_error_message_grammar() -> None:
    """ButtonConfig margin error message is grammatically correct (no 'grater then')."""
    with pytest.raises(ValueError) as exc_info:
        ButtonConfig(margin=5.0)
    msg = str(exc_info.value)
    assert "grater" not in msg
    assert "greater" in msg


# ---------------------------------------------------------------------------
# CuffConfig — validation
# ---------------------------------------------------------------------------


def test_cuff_config_valid() -> None:
    """CuffConfig with all valid fields constructs without error."""
    cfg = CuffConfig(length=20 * CM, width=4 * CM)
    assert cfg.length == pytest.approx(20 * CM)
    assert cfg.width == pytest.approx(4 * CM)


def test_cuff_config_rejects_zero_length() -> None:
    """CuffConfig rejects length <= 0."""
    with pytest.raises(ValueError, match="length"):
        CuffConfig(length=0.0, width=4 * CM)


def test_cuff_config_rejects_zero_width() -> None:
    """CuffConfig rejects width <= 0."""
    with pytest.raises(ValueError, match="width"):
        CuffConfig(length=20 * CM, width=0.0)


def test_cuff_config_rejects_negative_overlap() -> None:
    """CuffConfig rejects overlap < 0."""
    with pytest.raises(ValueError, match="overlap"):
        CuffConfig(length=20 * CM, width=4 * CM, overlap=-1.0)


def test_cuff_config_rejects_negative_underlap() -> None:
    """CuffConfig rejects underlap < 0."""
    with pytest.raises(ValueError, match="underlap"):
        CuffConfig(length=20 * CM, width=4 * CM, underlap=-1.0)


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — WIDE with cuff config
# ---------------------------------------------------------------------------


def test_sleeve_cm_wide_with_cuff_hem_width(sleeve_armhole: SleeveArmhole) -> None:
    """WIDE + cuff_config: sleeve_hem_width = cuff_length (no pleats)."""
    from sewpat.sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveType

    cuff = CuffConfig(length=20 * CM, width=4 * CM)
    cfg = SleeveConfig(sleeve_length=60 * CM, cuff_config=cuff)
    cm = SleeveConstructionMeasures.from_armhole(
        sleeve_armhole, None, cfg, SleeveBlockConfig.WIDE, SleeveType.WIDE
    )
    assert cm.sleeve_hem_width == pytest.approx(20 * CM)


def test_sleeve_cm_wide_with_cuff_and_pleats_hem_width(sleeve_armhole: SleeveArmhole) -> None:
    """WIDE + cuff_config + pleat_config: sleeve_hem_width = cuff_length + num_pleats × depth."""
    from sewpat.sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveType

    cuff = CuffConfig(length=20 * CM, width=4 * CM)
    pleats = PleatConfig(depth=3 * CM, num_pleats=3, spacing=1.5 * CM)
    cfg = SleeveConfig(sleeve_length=60 * CM, cuff_config=cuff, pleat_config=pleats)
    cm = SleeveConstructionMeasures.from_armhole(
        sleeve_armhole, None, cfg, SleeveBlockConfig.WIDE, SleeveType.WIDE
    )
    expected = 20 * CM + 3 * (3 * CM)
    assert cm.sleeve_hem_width == pytest.approx(expected)


def test_sleeve_cm_wide_without_cuff_hem_width_is_none(sleeve_armhole: SleeveArmhole) -> None:
    """WIDE without cuff_config: sleeve_hem_width is None."""
    from sewpat.sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveType

    cfg = SleeveConfig(sleeve_length=60 * CM)
    cm = SleeveConstructionMeasures.from_armhole(
        sleeve_armhole, None, cfg, SleeveBlockConfig.WIDE, SleeveType.WIDE
    )
    assert cm.sleeve_hem_width is None


# ---------------------------------------------------------------------------
# WideSleeveGrid — sleeve_width ValueError instead of assert
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_sleeve_width_raises_value_error(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """WideSleeveGrid.sleeve_width raises ValueError (not AssertionError) when None."""

    cfg = SleeveConfig(sleeve_length=60 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg)
    # Force sleeve_width to None via dataclasses.replace on the frozen measures object
    null_cm = dataclasses.replace(grid.construction_measures, sleeve_width=None)
    grid_null = dataclasses.replace(grid, construction_measures=null_cm)
    with pytest.raises(ValueError, match="sleeve_width"):
        _ = grid_null.sleeve_width


def test_wide_sleeve_grid_sleeve_width_is_positive(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """WideSleeveGrid.sleeve_width returns a positive value for valid geometry."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg)
    assert grid.sleeve_width > 0


# ---------------------------------------------------------------------------
# PleatConfig public API export
# ---------------------------------------------------------------------------


def test_pleat_config_importable_from_sewpat() -> None:
    """PleatConfig is accessible from the top-level sewpat package."""
    import sewpat

    assert sewpat.PleatConfig is PleatConfig


# ---------------------------------------------------------------------------
# SleeveConfig — validation gaps
# ---------------------------------------------------------------------------


def test_sleeve_config_rejects_negative_slit_height() -> None:
    """SleeveConfig rejects slit_height < 0."""
    with pytest.raises(ValueError, match="slit_height"):
        SleeveConfig(sleeve_length=60 * CM, slit_height=-1.0)


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — error paths
# ---------------------------------------------------------------------------


def test_sleeve_cm_raises_when_meas_none_for_narrow(sleeve_armhole: SleeveArmhole) -> None:
    """from_armhole raises ValueError when meas=None for a non-WIDE sleeve type."""
    from sewpat.sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveType

    cfg = SleeveConfig(sleeve_length=60 * CM)
    with pytest.raises(ValueError, match="meas"):
        SleeveConstructionMeasures.from_armhole(
            sleeve_armhole, None, cfg, SleeveBlockConfig.NARROW_BLOUSE, SleeveType.NARROW
        )


def test_sleeve_cm_raises_on_infeasible_wide_geometry(sleeve_armhole: SleeveArmhole) -> None:
    """from_armhole raises ValueError when the wide sleeve radicand is negative."""
    from unittest.mock import PropertyMock, patch

    from sewpat.sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveType

    # Patch armscye_circumference to a tiny value so cap_height > (armscye_circ/2 − ease)
    with patch.object(
        type(sleeve_armhole), "armscye_circumference", new_callable=PropertyMock, return_value=1.0
    ):
        cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=0.0 * CM, ease=0.0 * CM)
        with pytest.raises(ValueError, match="Infeasible"):
            SleeveConstructionMeasures.from_armhole(
                sleeve_armhole, None, cfg, SleeveBlockConfig.WIDE, SleeveType.WIDE
            )


def test_sleeve_cm_narrow_without_upper_arm_ease_gives_none_sleeve_width(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
) -> None:
    """NARROW with upper_arm_ease=None yields sleeve_width=None."""
    from sewpat.sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveMode, SleeveType

    no_oa_cfg = SleeveBlockConfig(
        mode=SleeveMode.NARROW_BLOUSE,
        cap_offset=-1.0 * CM,
        upper_arm_ease=None,  # optional; when absent sleeve_width is None
        hem_ease=6.0 * CM,
    )
    cfg = SleeveConfig(sleeve_length=60 * CM)
    cm = SleeveConstructionMeasures.from_armhole(
        sleeve_armhole, sleeve_meas, cfg, no_oa_cfg, SleeveType.NARROW
    )
    assert cm.sleeve_width is None


# ---------------------------------------------------------------------------
# CuffBlock — button row placement variations (covers _build_button_rows branches)
# ---------------------------------------------------------------------------


def _make_cuff_block(cuff_config: CuffConfig) -> CuffBlock:
    """Helper — build a CuffBlock from an explicit CuffConfig."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cuff_config=cuff_config)
    result = CuffBlock.from_sleeve_config(cfg)
    assert result is not None
    return result


def test_cuff_block_no_buttons_zero_button_config() -> None:
    """CuffBlock with num_buttons=0 produces a valid part (no button marks)."""
    block = _make_cuff_block(
        CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=2 * CM,
            overlap=3 * CM,
            button_config=ButtonConfig(num_buttons=0),
        )
    )
    assert isinstance(block, CuffBlock)


def test_cuff_block_no_button_config() -> None:
    """CuffBlock with button_config=None produces a valid part."""
    block = _make_cuff_block(
        CuffConfig(length=20 * CM, width=4 * CM, underlap=2 * CM, overlap=3 * CM)
    )
    assert isinstance(block, CuffBlock)


def test_cuff_block_only_underlap_button_placement() -> None:
    """CuffBlock with underlap only: button at closure line, hole inside cuff body."""
    block = _make_cuff_block(
        CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=2 * CM,
            overlap=0,
            button_config=ButtonConfig(num_buttons=1),
        )
    )
    assert isinstance(block, CuffBlock)


def test_cuff_block_only_overlap_button_placement() -> None:
    """CuffBlock with overlap only: button in overlap half, hole centred in overlap."""
    block = _make_cuff_block(
        CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=0,
            overlap=3 * CM,
            button_config=ButtonConfig(num_buttons=1),
        )
    )
    assert isinstance(block, CuffBlock)


def test_cuff_block_no_laps_button_config_skips_marks() -> None:
    """CuffBlock with no underlap/overlap skips button marks even when button_config is set."""
    block = _make_cuff_block(
        CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=0,
            overlap=0,
            button_config=ButtonConfig(num_buttons=1),
        )
    )
    assert isinstance(block, CuffBlock)


def test_cuff_block_margin_too_large_skips_marks() -> None:
    """CuffBlock skips button marks when cuff height band is smaller than 2×margin."""
    # cuff_height = 1 mm, margin = 10 mm → valid band is negative → no marks
    block = _make_cuff_block(
        CuffConfig(
            length=20 * CM,
            width=1.0,  # 1 mm — very thin cuff
            underlap=0,
            overlap=3 * CM,
            button_config=ButtonConfig(num_buttons=1, margin=10.0),
        )
    )
    assert isinstance(block, CuffBlock)


# ---------------------------------------------------------------------------
# seam_allowance > 0 — coverage for _assemble_sleeve_part and _assemble_cuff_part
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_with_seam_allowance_does_not_raise(
    sleeve_armhole: SleeveArmhole,
    sleeve_config_with_cuff: SleeveConfig,
) -> None:
    """WideSleeveBlock built with seam_allowance > 0 assembles without error."""
    block = WideSleeveBlock.from_armhole(
        sleeve_armhole, sleeve_config_with_cuff, seam_allowance=1.0 * CM
    )
    assert isinstance(block, WideSleeveBlock)
    assert block.part is not None


def test_cuff_block_with_seam_allowance_does_not_raise() -> None:
    """CuffBlock built with seam_allowance > 0 assembles without error."""
    cfg = SleeveConfig(
        sleeve_length=60 * CM,
        cuff_config=CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=2 * CM,
            overlap=3 * CM,
            button_config=ButtonConfig(num_buttons=2),
        ),
    )
    result = CuffBlock.from_sleeve_config(cfg, seam_allowance=1.0 * CM)
    assert result is not None
    assert isinstance(result, CuffBlock)
