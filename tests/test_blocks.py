"""Tests for blocks.py — TopBlock, TopBlockBack, TopBlockFront."""

import pytest

from sewpat.blocks import BlockConfig, TopBlock, TopBlockBack, TopBlockFront
from sewpat.fitclass import FitClass
from sewpat.geometry import CubicBezier, Dart, Point, Segment
from sewpat.grids import GridConfig, TopGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import PatternConfig, PatternPart
from sewpat.person import PersonalAdjustments
from sewpat.units import CM


@pytest.fixture
def top_grid(standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass):
    """Shared WAISTED_DART grid for block tests."""
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    return TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
    )


@pytest.fixture
def top_block(
    standard_blouse_measurements: BlouseMeasurements,
    standard_fitclass: FitClass,
    top_grid: TopGrid,
):
    """Top block without seam allowance."""
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    return TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=top_grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
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
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
    )
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
    )
    assert isinstance(block, TopBlock)


def test_top_block_with_personal_adjustments(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """PersonalAdjustments are accepted without error."""
    config = GarmentConfig(length=70 * CM)
    adj = PersonalAdjustments(hip_offset=2.0 * CM, shoulder_drop=1.5 * CM)
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
        hip_offset=adj.hip_offset,
    )
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
        adjustments=adj,
    )
    assert isinstance(block, TopBlock)


def test_top_block_custom_part_names(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass, top_grid: TopGrid
):
    """Custom back_name and front_name are applied to the parts."""
    config = GarmentConfig(length=70 * CM)
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=top_grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
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
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
        layout=layout,
    )
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
        layout=layout,
    )
    assert isinstance(block, TopBlock)


def test_top_block_grid_is_mandatory(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Omitting grid raises TypeError — it is a mandatory parameter."""
    config = GarmentConfig(length=70 * CM)
    with pytest.raises(TypeError):
        TopBlock.from_measurements(  # type: ignore[call-arg]
            meas=standard_blouse_measurements,
            config=config,
            fit_class=standard_fitclass,
        )


# ---------------------------------------------------------------------------
# Center-back construction style
# ---------------------------------------------------------------------------


@pytest.fixture
def casual_grid(standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass):
    """CASUAL grid."""
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    return TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.CASUAL,
        hip_offset=2 * CM,
    )


def test_waisted_dart_center_back_has_two_segments(top_block: TopBlock):
    """WAISTED_DART block: center back is built from two segments (kinked at waist)."""
    center_back_elems = [
        e
        for e in top_block.back.part.elements
        if e.role == "center_back" and isinstance(e.geometry, Segment)
    ]
    assert len(center_back_elems) == 2, (
        f"Expected 2 center-back segments for WAISTED_DART, got {len(center_back_elems)}"
    )


@pytest.fixture
def casual_block(
    standard_blouse_measurements: BlouseMeasurements,
    standard_fitclass: FitClass,
    casual_grid: TopGrid,
) -> TopBlock:
    """Casual block without seam allowance."""
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    return TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=casual_grid,
        block_config=BlockConfig.CASUAL,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
    )


@pytest.fixture
def casual_block_with_sa(
    standard_blouse_measurements: BlouseMeasurements,
    standard_fitclass: FitClass,
    casual_grid: TopGrid,
) -> TopBlock:
    """Casual block with 1 cm seam allowance — exercises the SA miter path."""
    config = GarmentConfig(length=70 * CM, seam_allowance=1.0 * CM)
    return TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=casual_grid,
        block_config=BlockConfig.CASUAL,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
    )


# ---------------------------------------------------------------------------
# Casual block — basic construction
# ---------------------------------------------------------------------------


def test_casual_block_constructs(casual_block: TopBlock) -> None:
    """CASUAL block builds without error."""
    assert isinstance(casual_block, TopBlock)


def test_casual_block_with_sa_constructs(casual_block_with_sa: TopBlock) -> None:
    """CASUAL block with seam allowance builds without error."""
    assert isinstance(casual_block_with_sa, TopBlock)


def test_casual_center_back_has_one_segment(casual_block: TopBlock) -> None:
    """CASUAL block: center back is a single straight segment (no waist kink)."""
    center_back_elems = [
        e
        for e in casual_block.back.part.elements
        if e.role == "center_back" and isinstance(e.geometry, Segment)
    ]
    assert len(center_back_elems) == 1, (
        f"Expected 1 center-back segment for CASUAL, got {len(center_back_elems)}"
    )


def test_casual_back_no_waist_dart(casual_block: TopBlock) -> None:
    """CASUAL block back: no waist dart."""
    assert casual_block.back.waist_dart is None


def test_casual_front_no_waist_dart(casual_block: TopBlock) -> None:
    """CASUAL block front: no waist dart."""
    assert casual_block.front.waist_dart is None


def test_casual_front_no_shoulder_dart(casual_block: TopBlock) -> None:
    """CASUAL block front: no shoulder dart (single unbroken shoulder seam)."""
    assert casual_block.front.shoulder_dart is None


def test_casual_front_shoulder_neckline_is_none(casual_block: TopBlock) -> None:
    """CASUAL block front: shoulder_neckline is None (no dart split)."""
    assert casual_block.front.shoulder_neckline is None


# ---------------------------------------------------------------------------
# Casual block — back hem geometry
# ---------------------------------------------------------------------------


def test_casual_back_hem_is_segment(casual_block: TopBlock) -> None:
    """CASUAL back hem is a straight Segment, not a Bézier."""
    hem_elems = [e for e in casual_block.back.part.elements if e.name == "Hem Back"]
    assert any(isinstance(e.geometry, Segment) for e in hem_elems), (
        "Expected back hem to be a Segment for the CASUAL block"
    )


def test_casual_back_hem_orthogonal_to_center_back(casual_block: TopBlock) -> None:
    """CASUAL back hem must be orthogonal to the center-back segment (dot product ≈ 0)."""
    cb_elem = next(
        e
        for e in casual_block.back.part.elements
        if e.role == "center_back" and isinstance(e.geometry, Segment)
    )
    hem_elem = next(
        e
        for e in casual_block.back.part.elements
        if isinstance(e.geometry, Segment) and e.name == "Hem Back"
    )
    cb_dir = cb_elem.geometry.unit_direction
    hem_dir = hem_elem.geometry.unit_direction
    dot = abs(float(cb_dir @ hem_dir))
    assert dot < 1e-6, f"Hem not orthogonal to CB: |dot| = {dot:.2e}"


def test_casual_back_side_hem_parallel_to_center_back(casual_block: TopBlock) -> None:
    """CASUAL back side-hem must be parallel to the center-back segment (cross product ≈ 0)."""
    cb_elem = next(
        e
        for e in casual_block.back.part.elements
        if e.role == "center_back" and isinstance(e.geometry, Segment)
    )
    side_hem_elem = next(
        e
        for e in casual_block.back.part.elements
        if isinstance(e.geometry, Segment) and e.name == "Side Hem Back"
    )
    cb_dir = cb_elem.geometry.unit_direction
    side_dir = side_hem_elem.geometry.unit_direction
    cross = abs(float(cb_dir[0] * side_dir[1] - cb_dir[1] * side_dir[0]))
    assert cross < 1e-6, f"Side hem not parallel to CB: |cross| = {cross:.2e}"


def test_casual_back_hem_connects_cb_to_side_hem(casual_block: TopBlock) -> None:
    """Back hem start == end of CB, back hem end == end of side-hem."""
    cb_elem = next(
        e
        for e in casual_block.back.part.elements
        if e.role == "center_back" and isinstance(e.geometry, Segment)
    )
    hem_elem = next(
        e
        for e in casual_block.back.part.elements
        if isinstance(e.geometry, Segment) and e.name == "Hem Back"
    )
    side_hem_elem = next(
        e
        for e in casual_block.back.part.elements
        if isinstance(e.geometry, Segment) and e.name == "Side Hem Back"
    )
    assert hem_elem.geometry.start.distance_to(cb_elem.geometry.end) < 0.1
    assert hem_elem.geometry.end.distance_to(side_hem_elem.geometry.end) < 0.1


# ---------------------------------------------------------------------------
# Casual block — equal side lengths
# ---------------------------------------------------------------------------


def test_casual_side_lengths_are_equal(casual_block: TopBlock) -> None:
    """Total side length (hip curve + side-hem) must be equal on back and front."""
    from sewpat.geometry import seam_length

    back_total = seam_length([casual_block.back.side_waist_hip, casual_block.back.side_hip_hem])
    front_total = seam_length([casual_block.front.side_waist_hip, casual_block.front.side_hip_hem])
    assert back_total == pytest.approx(front_total, abs=0.1), (
        f"Back side total {back_total:.2f} ≠ front side total {front_total:.2f}"
    )


# ---------------------------------------------------------------------------
# Casual block — front hem geometry
# ---------------------------------------------------------------------------


def test_casual_front_hem_is_cubic_bezier(casual_block: TopBlock) -> None:
    """CASUAL front hem is a CubicBezier, not a Segment."""
    hem_elems = [
        e
        for e in casual_block.front.part.elements
        if isinstance(e.geometry, CubicBezier) and e.name == "Hem Front"
    ]
    assert len(hem_elems) == 1, "Expected exactly one CubicBezier front hem"


def test_casual_front_hem_departs_horizontally_from_cf(casual_block: TopBlock) -> None:
    """Front hem p1 control point must have the same y as p0 (horizontal departure from CF)."""
    hem_elem = next(
        e
        for e in casual_block.front.part.elements
        if isinstance(e.geometry, CubicBezier) and e.name == "Hem Front"
    )
    bez = hem_elem.geometry
    assert abs(bez.p0.y - bez.p1.y) < 0.1, (
        f"Front hem does not depart horizontally: p0.y={bez.p0.y:.2f}, p1.y={bez.p1.y:.2f}"
    )


# ---------------------------------------------------------------------------
# Casual block — seam allowance roundtrip (no degenerate gaps)
# ---------------------------------------------------------------------------


def test_casual_back_sa_outline_is_closed(
    casual_block: TopBlock, casual_block_with_sa: TopBlock
) -> None:
    """Adding SA must increase the element count — proving the SA path completed without error."""
    n_without = len(casual_block.back.part.elements)
    n_with = len(casual_block_with_sa.back.part.elements)
    assert n_with > n_without, f"SA did not add elements: without={n_without}, with={n_with}"


def test_casual_back_sa_does_not_raise(
    standard_blouse_measurements: BlouseMeasurements,
    standard_fitclass: FitClass,
    casual_grid: TopGrid,
) -> None:
    """Building the CASUAL block with seam allowance must not raise any exception."""
    config = GarmentConfig(length=70 * CM, seam_allowance=1.0 * CM)
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=casual_grid,
        block_config=BlockConfig.CASUAL,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
    )
    assert isinstance(block, TopBlock)


# ---------------------------------------------------------------------------
# TopBlock.from_measurements — fit_class=None fallback (blocks.py lines 229-231)
# ---------------------------------------------------------------------------


def test_top_block_fit_class_none_falls_back_to_pk4(
    standard_blouse_measurements: BlouseMeasurements,
    top_grid: TopGrid,
) -> None:
    """Omitting fit_class falls back to FitClass(pk=4) instead of raising."""
    config = GarmentConfig(length=70 * CM)
    block = TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=top_grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=None,
    )
    assert isinstance(block, TopBlock)
