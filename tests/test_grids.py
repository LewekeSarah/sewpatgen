"""Tests for grids.py — TopGrid construction and validation."""

import pytest

from sewpat.fitclass import FitClass
from sewpat.geometry import Point, Segment
from sewpat.grids import GridConfig, TopGrid, _check_chest_width
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import PatternConfig
from sewpat.units import CM


@pytest.fixture
def top_grid_setup(standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass):
    """Setup for TopGrid tests."""
    config = GarmentConfig(length=70 * CM)
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
    )
    return {
        "meas": standard_blouse_measurements,
        "fc": standard_fitclass,
        "config": config,
        "grid": grid,
    }


def test_top_grid_returns_top_grid_instance(top_grid_setup):
    """from_measurements returns a TopGrid."""
    assert isinstance(top_grid_setup["grid"], TopGrid)


def test_top_grid_part_is_not_none(top_grid_setup):
    """The grid part is populated."""
    assert top_grid_setup["grid"].part is not None


@pytest.mark.parametrize(
    "attr",
    [
        "shoulder_front",
        "shoulder_back",
        "chest",
        "waist",
        "hip",
        "hem",
        "center_back",
        "hip_adj",
        "neck",
        "dart_back",
        "armscye_back",
        "side_back",
        "side_front",
        "armscye_front",
        "bust_point",
        "center_front",
    ],
)
def test_top_grid_all_segments_are_segments(top_grid_setup, attr: str):
    """Every named grid attribute is a Segment."""
    assert isinstance(getattr(top_grid_setup["grid"], attr), Segment)


def test_top_grid_chest_width_constraint_satisfied(top_grid_setup):
    """The chest-width check passes (would raise ValueError otherwise)."""
    # No assertion needed — construction already ran _check_chest_width.
    pass


def test_top_grid_hip_offset_shifts_verticals(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """A non-zero hip_offset shifts the hip_adj line position."""
    config = GarmentConfig(length=70 * CM)
    grid_default = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
    )
    grid_offset = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
        hip_offset=1.0 * CM,
    )
    # hip_adj.p1.x should differ by the scaled offset
    assert grid_default.hip_adj.p1.x != pytest.approx(grid_offset.hip_adj.p1.x)


def test_top_grid_custom_layout_anchor_applied(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Custom PatternConfig anchor shifts the grid origin."""
    config = GarmentConfig(length=70 * CM)
    layout = PatternConfig(anchor=Point(20 * CM, 20 * CM))
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
        layout=layout,
    )
    # shoulder_back (y=0 offset) should start at anchor y
    assert grid.shoulder_back.p1.y == pytest.approx(20 * CM, abs=1e-3)


def test_top_grid_chest_width_mismatch_raises(top_grid_setup):
    """_check_chest_width raises ValueError when the grid is inconsistent."""
    # Corrupt the grid by passing wrong expected width
    with pytest.raises(ValueError):
        _check_chest_width(top_grid_setup["grid"], 9999 * CM)


# ---------------------------------------------------------------------------
# GridConfig tests
# ---------------------------------------------------------------------------


def test_grid_config_waisted_dart_uses_fitclass_bust_point_ease(
    standard_fitclass: FitClass,
):
    """WAISTED_DART preset delegates bust_point_ease to the FitClass."""
    gc = GridConfig.WAISTED_DART
    assert gc.bust_point_ease is None
    assert gc.resolve_bust_point_ease(standard_fitclass) == pytest.approx(
        standard_fitclass.bust_point_ease
    )


def test_grid_config_casual_has_fixed_bust_point_ease(standard_fitclass: FitClass):
    """CASUAL preset uses a fixed 1 cm bust_point_ease, ignoring FitClass."""
    gc = GridConfig.CASUAL
    assert gc.bust_point_ease == pytest.approx(1 * CM)
    assert gc.resolve_bust_point_ease(standard_fitclass) == pytest.approx(1 * CM)


def test_grid_config_waisted_dart_hip_adj_denominator(
    standard_blouse_measurements: BlouseMeasurements,
):
    """WAISTED_DART uses back_length as hip-adj denominator."""
    gc = GridConfig.WAISTED_DART
    expected = standard_blouse_measurements.back_length
    assert gc.resolve_hip_adj_denominator(standard_blouse_measurements) == pytest.approx(expected)


def test_grid_config_casual_hip_adj_denominator(
    standard_blouse_measurements: BlouseMeasurements,
):
    """CASUAL uses back_length + hip_depth as hip-adj denominator."""
    gc = GridConfig.CASUAL
    meas = standard_blouse_measurements
    expected = meas.back_length + meas.hip_depth
    assert gc.resolve_hip_adj_denominator(meas) == pytest.approx(expected)


def test_grid_config_invalid_denominator_raises(
    standard_blouse_measurements: BlouseMeasurements,
):
    """Unknown hip_adj_denominator key raises AttributeError."""
    gc = GridConfig(hip_adj_denominator="nonexistent_field")
    with pytest.raises(AttributeError, match="nonexistent_field"):
        gc.resolve_hip_adj_denominator(standard_blouse_measurements)


def test_top_grid_casual_grid_config_changes_hip_adj(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Passing GridConfig.CASUAL produces a different hip_adj than WAISTED_DART."""
    config = GarmentConfig(length=70 * CM)
    hip_offset = 1.0 * CM
    grid_waisted = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        hip_offset=hip_offset,
        grid_config=GridConfig.WAISTED_DART,
    )
    grid_casual = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        hip_offset=hip_offset,
        grid_config=GridConfig.CASUAL,
    )
    # The two grids must differ in hip_adj when hip_depth > 0
    # (denominator is larger for CASUAL, so hip_adj is smaller)
    assert grid_waisted.hip_adj.p1.x != pytest.approx(grid_casual.hip_adj.p1.x)


def test_top_grid_grid_config_is_mandatory(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Omitting grid_config raises TypeError — it is a mandatory parameter."""
    config = GarmentConfig(length=70 * CM)
    with pytest.raises(TypeError):
        TopGrid.from_measurements(  # type: ignore[call-arg]
            meas=standard_blouse_measurements,
            fit_class=standard_fitclass,
            config=config,
        )


# ---------------------------------------------------------------------------
# Geometric invariant: CASUAL hip_adj formula
# ---------------------------------------------------------------------------


def test_casual_hip_adj_line_intersects_hip_at_hip_offset(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
):
    """Verify the CASUAL hip_adj construction invariant numerically.

    The straight line from ``(center_back, shoulder_back)`` through
    ``(hip_adj, chest)`` must intersect the hip level at a horizontal distance
    of exactly ``hip_offset`` from center back.

    Derivation
    ----------
    With anchor at origin, the two points on the line are::

        A = (0,          0)                 # center_back @ shoulder_back
        B = (hip_adj_x,  armscye_depth)     # hip_adj     @ chest

    where::

        hip_adj_x = hip_offset * armscye_depth / (back_length + hip_depth)

    The line x(y) = hip_adj_x * y / armscye_depth, so at y = back_length + hip_depth::

        x = hip_adj_x * (back_length + hip_depth) / armscye_depth
          = hip_offset * armscye_depth / (back_length + hip_depth)
            * (back_length + hip_depth) / armscye_depth
          = hip_offset   ✓

    This test confirms the formula both algebraically (via symbolic substitution)
    and numerically with the standard fixture measurements.
    """
    meas = standard_blouse_measurements
    hip_offset = 2 * CM
    config = GarmentConfig(length=70 * CM)

    grid = TopGrid.from_measurements(
        meas=meas,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.CASUAL,
        hip_offset=hip_offset,
    )

    # Coordinates from the built grid (anchor at default origin)
    x_cb = grid.center_back.p1.x  # should be 0 (or layout.anchor.x)
    y_sb = grid.shoulder_back.p1.y  # top of grid
    x_ha = grid.hip_adj.p1.x  # hip_adj vertical position
    y_ch = grid.chest.p1.y  # chest / armscye_depth level
    y_hip = grid.hip.p1.y  # hip level

    # The line through A=(x_cb, y_sb) and B=(x_ha, y_ch):
    # x(y) = x_cb + (x_ha - x_cb) * (y - y_sb) / (y_ch - y_sb)
    dy_total = y_ch - y_sb  # = armscye_depth
    dy_to_hip = y_hip - y_sb  # = back_length + hip_depth
    x_at_hip = x_cb + (x_ha - x_cb) * dy_to_hip / dy_total

    # Must equal x_cb + hip_offset (i.e. 2 cm from center back)
    assert x_at_hip == pytest.approx(x_cb + hip_offset, abs=1e-6), (
        f"Line from center_back@shoulder through hip_adj@chest "
        f"intersects hip at {(x_at_hip - x_cb) / CM:.4f} cm from center back, "
        f"expected {hip_offset / CM:.1f} cm"
    )
