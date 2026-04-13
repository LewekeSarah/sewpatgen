"""Tests for WideSleeveGrid (in sewpat.grids) and the wide-sleeve fields of SleeveConfig.

Covers:
* SleeveConfig wide-sleeve field defaults, boundary validation, and error cases.
* WideSleeveGrid construction and derived-measure formulas.
* Horizontal- and vertical-line positions within the built ConstructionGridPart.
* Effect of cap_offset on cap_height (0 → highest/narrowest; 2 cm → lowest/widest).
* Effect of ease on sleeve_width (larger ease → narrower sleeve).
"""

from __future__ import annotations

import math

import pytest

from sewpat.geometry import Segment
from sewpat.grids import WideSleeveGrid
from sewpat.pattern import ConstructionGridPart, PatternConfig
from sewpat.sleeve import (
    SleeveArmhole,
    SleeveBlockConfig,
    SleeveConfig,
    SleeveConstructionMeasures,
    SleeveType,
)
from sewpat.units import CM


def _wide_cm(armhole: SleeveArmhole, cfg: SleeveConfig) -> SleeveConstructionMeasures:
    """Helper: build SleeveConstructionMeasures for WIDE via the single factory."""
    return SleeveConstructionMeasures.from_armhole(
        armhole, None, cfg, SleeveBlockConfig.WIDE, SleeveType.WIDE
    )


# ---------------------------------------------------------------------------
# SleeveConfig — wide-sleeve field defaults
# ---------------------------------------------------------------------------


def test_sleeve_config_wide_default_cap_offset_in_range() -> None:
    """Default cap_offset is within [0, 2] cm."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    assert 0.0 <= cfg.cap_offset <= 2.0 * CM


def test_sleeve_config_wide_default_ease_in_range() -> None:
    """Default ease is within [0, 1] cm."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    assert 0.0 <= cfg.ease <= 1.0 * CM


def test_sleeve_config_wide_custom_values() -> None:
    """SleeveConfig stores explicitly supplied cap_offset and ease."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=1.5 * CM, ease=0.8 * CM)
    assert cfg.cap_offset == pytest.approx(1.5 * CM)
    assert cfg.ease == pytest.approx(0.8 * CM)


# ---------------------------------------------------------------------------
# SleeveConfig — cap_offset validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset_cm", [0.0, 1.0, 2.0])
def test_sleeve_config_accepts_cap_offset_boundaries(offset_cm: float) -> None:
    """SleeveConfig accepts cap_offset at boundary values 0, 1, and 2 cm."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=offset_cm * CM)
    assert cfg.cap_offset == pytest.approx(offset_cm * CM)


@pytest.mark.parametrize("offset_cm", [-0.1, -1.0, 2.1, 3.0])
def test_sleeve_config_rejects_cap_offset_out_of_range(offset_cm: float) -> None:
    """SleeveConfig raises ValueError for cap_offset outside [0, 2] cm."""
    with pytest.raises(ValueError, match="cap_offset"):
        SleeveConfig(sleeve_length=60 * CM, cap_offset=offset_cm * CM)


# ---------------------------------------------------------------------------
# SleeveConfig — ease validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ease_cm", [0.0, 0.5, 1.0])
def test_sleeve_config_accepts_ease_boundaries(ease_cm: float) -> None:
    """SleeveConfig accepts ease at boundary values 0, 0.5, and 1 cm."""
    cfg = SleeveConfig(sleeve_length=60 * CM, ease=ease_cm * CM)
    assert cfg.ease == pytest.approx(ease_cm * CM)


@pytest.mark.parametrize("ease_cm", [-0.1, -1.0, 1.1, 2.0])
def test_sleeve_config_rejects_ease_out_of_range(ease_cm: float) -> None:
    """SleeveConfig raises ValueError for ease outside [0, 1] cm."""
    with pytest.raises(ValueError, match="ease"):
        SleeveConfig(sleeve_length=60 * CM, ease=ease_cm * CM)


# ---------------------------------------------------------------------------
# WideSleeveGrid — return type and part type
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_returns_correct_type(default_wide_grid: WideSleeveGrid) -> None:
    """from_armhole returns a WideSleeveGrid instance."""
    assert isinstance(default_wide_grid, WideSleeveGrid)


def test_wide_sleeve_grid_part_is_construction_grid_part(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """.part is a ConstructionGridPart."""
    assert isinstance(default_wide_grid.part, ConstructionGridPart)


# ---------------------------------------------------------------------------
# WideSleeveGrid — segment types
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_cap_line_is_segment(default_wide_grid: WideSleeveGrid) -> None:
    """cap_line is a Segment."""
    assert isinstance(default_wide_grid.cap_line, Segment)


def test_wide_sleeve_grid_sleeve_length_line_is_segment(default_wide_grid: WideSleeveGrid) -> None:
    """sleeve_length_line is a Segment."""
    assert isinstance(default_wide_grid.sleeve_length_line, Segment)


def test_wide_sleeve_grid_hem_line_is_segment(default_wide_grid: WideSleeveGrid) -> None:
    """hem_line is a Segment."""
    assert isinstance(default_wide_grid.hem_line, Segment)


def test_wide_sleeve_grid_left_sleeve_is_segment(default_wide_grid: WideSleeveGrid) -> None:
    """left_sleeve is a Segment."""
    assert isinstance(default_wide_grid.left_sleeve, Segment)


def test_wide_sleeve_grid_center_sleeve_is_segment(default_wide_grid: WideSleeveGrid) -> None:
    """center_sleeve is a Segment."""
    assert isinstance(default_wide_grid.center_sleeve, Segment)


def test_wide_sleeve_grid_right_sleeve_is_segment(default_wide_grid: WideSleeveGrid) -> None:
    """right_sleeve is a Segment."""
    assert isinstance(default_wide_grid.right_sleeve, Segment)


# ---------------------------------------------------------------------------
# WideSleeveGrid — cap_height formula
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_cap_height_zero_offset(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """cap_height = armscye_height / 3 when cap_offset = 0."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=0.0)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg)
    assert grid.cap_height == pytest.approx(sleeve_armhole.armscye_height / 3.0)


def test_wide_sleeve_grid_cap_height_with_1cm_offset(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """cap_height = armscye_height / 3 − 1 cm when cap_offset = 1 cm."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=1.0 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg)
    assert grid.cap_height == pytest.approx(sleeve_armhole.armscye_height / 3.0 - 1.0 * CM)


def test_wide_sleeve_grid_cap_height_with_2cm_offset(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """cap_height = armscye_height / 3 − 2 cm when cap_offset = 2 cm."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=2.0 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg)
    assert grid.cap_height == pytest.approx(sleeve_armhole.armscye_height / 3.0 - 2.0 * CM)


def test_wide_sleeve_grid_larger_cap_offset_gives_lower_cap(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """Larger cap_offset produces a lower (shorter) sleeve cap."""
    g_narrow = WideSleeveGrid.from_armhole(
        sleeve_armhole, SleeveConfig(sleeve_length=60 * CM, cap_offset=0.0)
    )
    g_wide = WideSleeveGrid.from_armhole(
        sleeve_armhole, SleeveConfig(sleeve_length=60 * CM, cap_offset=2.0 * CM)
    )
    assert g_wide.cap_height < g_narrow.cap_height


def test_wide_sleeve_grid_cap_height_is_positive(default_wide_grid: WideSleeveGrid) -> None:
    """cap_height is positive for a real bodice armhole."""
    assert default_wide_grid.cap_height > 0.0


# ---------------------------------------------------------------------------
# WideSleeveGrid — sleeve_width formula
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_sleeve_width_formula(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """sleeve_width (half-width) = sqrt((armscye_circumference/2 − ease)² − cap_height²)."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=1.0 * CM, ease=0.5 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg)
    expected = math.sqrt(
        (sleeve_armhole.armscye_circumference / 2 - cfg.ease) ** 2 - grid.cap_height**2
    )
    assert grid.sleeve_width == pytest.approx(expected)


def test_wide_sleeve_grid_larger_ease_gives_narrower_sleeve(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """Larger ease value produces a narrower sleeve width."""
    g_wide = WideSleeveGrid.from_armhole(
        sleeve_armhole, SleeveConfig(sleeve_length=60 * CM, ease=0.0)
    )
    g_narrow = WideSleeveGrid.from_armhole(
        sleeve_armhole, SleeveConfig(sleeve_length=60 * CM, ease=1.0 * CM)
    )
    assert g_narrow.sleeve_width < g_wide.sleeve_width


def test_wide_sleeve_grid_sleeve_width_is_positive(default_wide_grid: WideSleeveGrid) -> None:
    """sleeve_width is positive."""
    assert default_wide_grid.sleeve_width > 0.0


# ---------------------------------------------------------------------------
# WideSleeveGrid — horizontal line positions
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_cap_line_y_position(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """cap_line is at anchor.y + cap_height."""
    layout = PatternConfig()
    cfg = SleeveConfig(sleeve_length=60 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg, layout=layout)
    assert grid.cap_line.p1.y == pytest.approx(layout.anchor.y + grid.cap_height)


def test_wide_sleeve_grid_sleeve_length_line_y_position(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """sleeve_length_line is at anchor.y + sleeve_length."""
    layout = PatternConfig()
    cfg = SleeveConfig(sleeve_length=60 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg, layout=layout)
    assert grid.sleeve_length_line.p1.y == pytest.approx(layout.anchor.y + cfg.sleeve_length)


def test_wide_sleeve_grid_hem_line_1cm_above_sleeve_length(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """hem_line is exactly 1 cm above sleeve_length_line."""
    assert default_wide_grid.hem_line.p1.y == pytest.approx(
        default_wide_grid.sleeve_length_line.p1.y - 1.0 * CM
    )


def test_wide_sleeve_grid_cap_line_above_sleeve_length_line(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """cap_line is higher up (smaller y) than sleeve_length_line."""
    assert default_wide_grid.cap_line.p1.y < default_wide_grid.sleeve_length_line.p1.y


def test_wide_sleeve_grid_hem_line_above_sleeve_length_line(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """hem_line is higher up (smaller y) than sleeve_length_line."""
    assert default_wide_grid.hem_line.p1.y < default_wide_grid.sleeve_length_line.p1.y


# ---------------------------------------------------------------------------
# WideSleeveGrid — vertical line positions
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_left_sleeve_at_anchor_x(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """left_sleeve is at anchor.x (leftmost edge of the grid)."""
    layout = PatternConfig()
    cfg = SleeveConfig(sleeve_length=60 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg, layout=layout)
    assert grid.left_sleeve.p1.x == pytest.approx(layout.anchor.x)


def test_wide_sleeve_grid_right_sleeve_at_anchor_plus_width(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """right_sleeve is at anchor.x + 2 * sleeve_width (sleeve_width is the half-width)."""
    layout = PatternConfig()
    cfg = SleeveConfig(sleeve_length=60 * CM)
    grid = WideSleeveGrid.from_armhole(sleeve_armhole, cfg, layout=layout)
    assert grid.right_sleeve.p1.x == pytest.approx(layout.anchor.x + 2 * grid.sleeve_width)


def test_wide_sleeve_grid_center_sleeve_equidistant(default_wide_grid: WideSleeveGrid) -> None:
    """center_sleeve is equidistant from left_sleeve and right_sleeve."""
    left_x = default_wide_grid.left_sleeve.p1.x
    right_x = default_wide_grid.right_sleeve.p1.x
    center_x = default_wide_grid.center_sleeve.p1.x
    assert center_x == pytest.approx((left_x + right_x) / 2.0)


def test_wide_sleeve_grid_left_right_distance_equals_sleeve_width(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """Full sleeve width equals 2 * sleeve_width (sleeve_width is the half-width)."""
    left_x = default_wide_grid.left_sleeve.p1.x
    right_x = default_wide_grid.right_sleeve.p1.x
    assert right_x - left_x == pytest.approx(2 * default_wide_grid.sleeve_width)


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — WIDE path via the single from_armhole factory
# ---------------------------------------------------------------------------


def test_from_wide_armhole_returns_construction_measures(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """from_armhole(meas=None, WIDE) returns a SleeveConstructionMeasures instance."""
    cfg = SleeveConfig(sleeve_length=60 * CM)
    cm = _wide_cm(sleeve_armhole, cfg)
    assert isinstance(cm, SleeveConstructionMeasures)


def test_from_wide_armhole_sleeve_type_is_wide(sleeve_armhole: SleeveArmhole) -> None:
    """from_armhole with WIDE mode always produces sleeve_type=WIDE."""
    cm = _wide_cm(sleeve_armhole, SleeveConfig(sleeve_length=60 * CM))
    assert cm.sleeve_type is SleeveType.WIDE


def test_from_wide_armhole_body_measurements_are_none(sleeve_armhole: SleeveArmhole) -> None:
    """Body-measurement fields are None when meas=None."""
    cm = _wide_cm(sleeve_armhole, SleeveConfig(sleeve_length=60 * CM))
    assert cm.armscye_width is None
    assert cm.wrist_circumference is None
    assert cm.upper_arm_circumference is None


def test_from_wide_armhole_cap_height_formula(sleeve_armhole: SleeveArmhole) -> None:
    """cap_height = armscye_height / 3 + block_config.cap_offset.

    _wide_cm passes SleeveBlockConfig.WIDE directly (cap_offset = −1 cm preset).
    The sign conversion (sleeve_config.cap_offset → block_config.cap_offset) is
    done by WideSleeveGrid.from_armhole, not by from_armhole itself.
    """
    cfg = SleeveConfig(sleeve_length=60 * CM)
    cm = _wide_cm(sleeve_armhole, cfg)
    assert cm.cap_height == pytest.approx(
        sleeve_armhole.armscye_height / 3.0 + SleeveBlockConfig.WIDE.cap_offset
    )


def test_from_wide_armhole_sleeve_width_formula(sleeve_armhole: SleeveArmhole) -> None:
    """sleeve_width (half-width) = sqrt((armscye_circ/2 − ease)² − cap_height²)."""
    cfg = SleeveConfig(sleeve_length=60 * CM, cap_offset=1.0 * CM, ease=0.5 * CM)
    cm = _wide_cm(sleeve_armhole, cfg)
    expected = math.sqrt(
        (sleeve_armhole.armscye_circumference / 2 - cfg.ease) ** 2 - cm.cap_height**2
    )
    assert cm.sleeve_width == pytest.approx(expected)


def test_from_wide_armhole_sleeve_length_stored(sleeve_armhole: SleeveArmhole) -> None:
    """sleeve_length is taken from config."""
    cm = _wide_cm(sleeve_armhole, SleeveConfig(sleeve_length=62 * CM))
    assert cm.sleeve_length == pytest.approx(62 * CM)


def test_from_wide_armhole_armscye_measures_stored(sleeve_armhole: SleeveArmhole) -> None:
    """armscye_height and armscye_circumference come from the armhole."""
    cm = _wide_cm(sleeve_armhole, SleeveConfig(sleeve_length=60 * CM))
    assert cm.armscye_height == pytest.approx(sleeve_armhole.armscye_height)
    assert cm.armscye_circumference == pytest.approx(sleeve_armhole.armscye_circumference)


def test_from_wide_armhole_hem_and_ease_are_none(sleeve_armhole: SleeveArmhole) -> None:
    """sleeve_hem_width and upper_arm_ease are None — not defined for WIDE."""
    cm = _wide_cm(sleeve_armhole, SleeveConfig(sleeve_length=60 * CM))
    assert cm.sleeve_hem_width is None
    assert cm.upper_arm_ease is None


# ---------------------------------------------------------------------------
# WideSleeveGrid.construction_measures — delegation
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_exposes_construction_measures(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """WideSleeveGrid exposes construction_measures as a SleeveConstructionMeasures."""
    assert isinstance(default_wide_grid.construction_measures, SleeveConstructionMeasures)


def test_wide_sleeve_grid_cap_height_from_construction_measures(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """grid.cap_height equals construction_measures.cap_height."""
    assert default_wide_grid.cap_height == pytest.approx(
        default_wide_grid.construction_measures.cap_height
    )


def test_wide_sleeve_grid_sleeve_width_from_construction_measures(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """grid.sleeve_width equals construction_measures.sleeve_width."""
    assert default_wide_grid.sleeve_width == pytest.approx(
        default_wide_grid.construction_measures.sleeve_width
    )


def test_wide_sleeve_grid_construction_measures_sleeve_type(
    default_wide_grid: WideSleeveGrid,
) -> None:
    """construction_measures carries sleeve_type=WIDE."""
    assert default_wide_grid.construction_measures.sleeve_type is SleeveType.WIDE


# ---------------------------------------------------------------------------
# WideSleeveGrid — part name
# ---------------------------------------------------------------------------


def test_wide_sleeve_grid_part_name(default_wide_grid: WideSleeveGrid) -> None:
    """The ConstructionGridPart is named 'Wide Sleeve Grid'."""
    assert default_wide_grid.part.name == "Wide Sleeve Grid"
