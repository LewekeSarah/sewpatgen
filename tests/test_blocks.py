"""Tests for blocks.py — TopBlock, TopBlockBack, TopBlockFront."""

import pytest

from sewpat.blocks import TopBlock, TopBlockBack, TopBlockFront
from sewpat.fitclass import FitClass
from sewpat.geometry import CubicBezier, Dart, Point, Segment
from sewpat.grids import TopGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import PatternConfig, PatternPart
from sewpat.person import PersonalAdjustments
from sewpat.units import CM


@pytest.fixture
def top_block(standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass):
    """Top block without seam allowance."""
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    return TopBlock.from_measurements(
        meas=standard_blouse_measurements, config=config, fit_class=standard_fitclass
    )


# ---------------------------------------------------------------------------
# TopBlock construction
# ---------------------------------------------------------------------------


def test_top_block_returns_top_block(top_block: TopBlock):
    """from_measurements returns a TopBlock."""
    assert isinstance(top_block, TopBlock)


def test_top_block_back_is_top_block_back(top_block: TopBlock):
    """block.back is a TopBlockBack."""
    assert isinstance(top_block.back, TopBlockBack)


def test_top_block_front_is_top_block_front(top_block: TopBlock):
    """block.front is a TopBlockFront."""
    assert isinstance(top_block.front, TopBlockFront)


def test_top_block_back_part_is_pattern_part(top_block: TopBlock):
    """block.back.part is a PatternPart."""
    assert isinstance(top_block.back.part, PatternPart)


def test_top_block_front_part_is_pattern_part(top_block: TopBlock):
    """block.front.part is a PatternPart."""
    assert isinstance(top_block.front.part, PatternPart)


def test_top_block_back_has_elements(top_block: TopBlock):
    """The back part contains at least one element."""
    assert len(top_block.back.part.elements) > 0


def test_top_block_front_has_elements(top_block: TopBlock):
    """The front part contains at least one element."""
    assert len(top_block.front.part.elements) > 0


# ---------------------------------------------------------------------------
# TopBlockBack typed attributes
# ---------------------------------------------------------------------------


def test_top_block_back_armscye_lower_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.back.armscye_lower, CubicBezier)


def test_top_block_back_armscye_upper_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.back.armscye_upper, CubicBezier)


def test_top_block_back_neckline_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.back.neckline, CubicBezier)


def test_top_block_back_shoulder_is_segment(top_block: TopBlock):
    assert isinstance(top_block.back.shoulder, Segment)


def test_top_block_back_side_chest_waist_is_segment(top_block: TopBlock):
    assert isinstance(top_block.back.side_chest_waist, Segment)


def test_top_block_back_side_waist_hip_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.back.side_waist_hip, CubicBezier)


def test_top_block_back_side_hip_hem_is_segment(top_block: TopBlock):
    assert isinstance(top_block.back.side_hip_hem, Segment)


def test_top_block_back_waist_dart_is_dart(top_block: TopBlock):
    assert isinstance(top_block.back.waist_dart, Dart)


def test_top_block_back_shoulder_dart_is_dart(top_block: TopBlock):
    assert isinstance(top_block.back.shoulder_dart, Dart)


def test_top_block_back_armscye_control_is_point(top_block: TopBlock):
    assert isinstance(top_block.back.armscye_control, Point)


def test_top_block_back_waist_indent_is_point(top_block: TopBlock):
    assert isinstance(top_block.back.waist_indent, Point)


def test_top_block_back_hip_outset_is_point(top_block: TopBlock):
    assert isinstance(top_block.back.hip_outset, Point)


# ---------------------------------------------------------------------------
# TopBlockFront typed attributes
# ---------------------------------------------------------------------------


def test_top_block_front_armscye_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.front.armscye, CubicBezier)


def test_top_block_front_neckline_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.front.neckline, CubicBezier)


def test_top_block_front_shoulder_armscye_is_segment(top_block: TopBlock):
    assert isinstance(top_block.front.shoulder_armscye, Segment)


def test_top_block_front_shoulder_neckline_is_segment(top_block: TopBlock):
    assert isinstance(top_block.front.shoulder_neckline, Segment)


def test_top_block_front_side_chest_waist_is_segment(top_block: TopBlock):
    assert isinstance(top_block.front.side_chest_waist, Segment)


def test_top_block_front_side_waist_hip_is_cubic_bezier(top_block: TopBlock):
    assert isinstance(top_block.front.side_waist_hip, CubicBezier)


def test_top_block_front_side_hip_hem_is_segment(top_block: TopBlock):
    assert isinstance(top_block.front.side_hip_hem, Segment)


def test_top_block_front_waist_dart_is_dart(top_block: TopBlock):
    assert isinstance(top_block.front.waist_dart, Dart)


def test_top_block_front_shoulder_dart_is_dart(top_block: TopBlock):
    assert isinstance(top_block.front.shoulder_dart, Dart)


def test_top_block_front_armscye_control_is_point(top_block: TopBlock):
    assert isinstance(top_block.front.armscye_control, Point)


def test_top_block_front_bust_point_is_point(top_block: TopBlock):
    assert isinstance(top_block.front.bust_point, Point)


# ---------------------------------------------------------------------------
# Optional parameters
# ---------------------------------------------------------------------------


def test_top_block_with_seam_allowance(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Building with seam_allowance > 0 does not raise."""
    config = GarmentConfig(length=70 * CM, seam_allowance=1.0 * CM)
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements, config=config, fit_class=standard_fitclass
    )
    assert isinstance(block, TopBlock)


def test_top_block_with_personal_adjustments(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """PersonalAdjustments are accepted without error."""
    config = GarmentConfig(length=70 * CM)
    adj = PersonalAdjustments(hip_offset=2.0 * CM, shoulder_drop=1.5 * CM)
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        fit_class=standard_fitclass,
        adjustments=adj,
    )
    assert isinstance(block, TopBlock)


def test_top_block_with_pre_built_grid(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """A pre-built TopGrid is reused instead of building a new one."""
    config = GarmentConfig(length=70 * CM)
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements, fit_class=standard_fitclass, config=config
    )
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements, config=config, fit_class=standard_fitclass, grid=grid
    )
    assert isinstance(block, TopBlock)


def test_top_block_custom_part_names(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Custom back_name and front_name are applied to the parts."""
    config = GarmentConfig(length=70 * CM)
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        fit_class=standard_fitclass,
        back_name="Rückenteil",
        front_name="Vorderteil",
    )
    assert block.back.part.name == "Rückenteil"
    assert block.front.part.name == "Vorderteil"


def test_top_block_custom_layout(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Custom PatternConfig layout is accepted."""
    config = GarmentConfig(length=70 * CM)
    layout = PatternConfig(anchor=Point(10 * CM, 10 * CM))
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements, config=config, fit_class=standard_fitclass, layout=layout
    )
    assert isinstance(block, TopBlock)
