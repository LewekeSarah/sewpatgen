"""Tests for grids.py — TopGrid construction and validation."""

import pytest

from sewpat.fitclass import FitClass
from sewpat.geometry import Point, Segment
from sewpat.grids import TopGrid, _check_chest_width
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import PatternConfig
from sewpat.units import CM


@pytest.fixture
def top_grid_setup(standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass):
    """Setup for TopGrid tests."""
    config = GarmentConfig(length=70 * CM)
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements, fit_class=standard_fitclass, config=config
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
        meas=standard_blouse_measurements, fit_class=standard_fitclass, config=config
    )
    grid_offset = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
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
        layout=layout,
    )
    # shoulder_back (y=0 offset) should start at anchor y
    assert grid.shoulder_back.p1.y == pytest.approx(20 * CM, abs=1e-3)


def test_top_grid_chest_width_mismatch_raises(top_grid_setup):
    """_check_chest_width raises ValueError when the grid is inconsistent."""
    # Corrupt the grid by passing wrong expected width
    with pytest.raises(ValueError):
        _check_chest_width(top_grid_setup["grid"], 9999 * CM)
