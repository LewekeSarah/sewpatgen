"""Shared pytest fixtures for the sewpat test suite.

This module provides reusable test data factories for common domain objects:
- Standard body measurements (`Person`)
- Ease-adjusted garment measurements (`BlouseMeasurements`)
- Fit classes (`FitClass`)
- Render helpers: ``simple_part``, ``simple_pattern``, ``svg_for_part`` fixtures

All fixtures use the 80–89 cm bust range (PK 4) as the reference size.
"""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

from sewpat.blocks import BlockConfig, CuffBlock, TopBlock, WideSleeveBlock
from sewpat.fitclass import FitClass
from sewpat.geometry import Point, Rect, Segment
from sewpat.grids import GridConfig, TopGrid, WideSleeveGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import Pattern, PatternPart
from sewpat.person import BalancedPerson, Person, PersonAnalyser
from sewpat.pleat import PleatConfig
from sewpat.render import _build_svg
from sewpat.sleeve import (
    ButtonConfig,
    CuffConfig,
    SleeveArmhole,
    SleeveBlockConfig,
    SleeveConfig,
    SleeveConstructionMeasures,
    SleeveMeasurements,
    SleeveType,
)
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def make_standard_person() -> Person:
    """Return a fully-specified Person in the 80–89 cm bust range (PK 4).

    Returns:
        Person with bust=86 cm, waist=70 cm, hip=96 cm, and all construction
        measurements populated according to Mueller & Sohn formulas.
    """
    bust = 86 * CM
    return Person(
        bust=bust,
        waist=70 * CM,
        hip=96 * CM,
        hip_depth=20 * CM,
        bust_depth=26 * CM,
        neck_size=7 * CM,
        bust_span=9 * CM,
        shoulder_width=13 * CM,
        back_length=41 * CM,
        front_length=43 * CM,
        body_rise=27 * CM,
        inseam=80 * CM,
        back_width=bust / 8 + 5.5 * CM,
        armscye_depth=bust / 10 + 11 * CM,
        armscye_width=bust / 8 - 1.5 * CM,
        chest_width=bust / 4 - 4.0 * CM,
        height=168 * CM,
    )


def make_standard_blouse_measurements(**overrides: Any) -> BlouseMeasurements:
    """Return ease-adjusted blouse measurements for the standard 86 cm bust.

    Args:
        **overrides: Any ``BlouseMeasurements`` field to override in the
            returned instance (e.g. ``hip_width=105 * CM``).  Uses
            :func:`dataclasses.replace` under the hood.

    Returns:
        BlouseMeasurements with ease already applied, suitable for constructing
        a women's top block in PK 4.  When *overrides* are given the
        ``bust_width`` consistency check is skipped for those fields — callers
        are responsible for passing a coherent value set.
    """
    bust = 86 * CM
    bw = bust / 8 + 5.5 * CM
    aw = bust / 8 - 1.5 * CM
    cw = bust / 4 - 4.0 * CM
    bust_width = 2 * (bw + aw + cw)
    base = BlouseMeasurements(
        bust=bust,
        waist=70 * CM,
        hip=96 * CM,
        hip_depth=20 * CM,
        bust_depth=26 * CM,
        neck_size=7 * CM,
        bust_span=9 * CM,
        shoulder_width=13 * CM,
        back_length=41 * CM,
        front_length=43 * CM,
        armscye_depth=bust / 10 + 11 * CM,
        bust_width=bust_width,
        waist_width=72 * CM,
        hip_width=98 * CM,
        back_width=bw,
        armscye_width=aw,
        chest_width=cw,
    )
    return replace(base, **overrides) if overrides else base


def make_standard_fitclass() -> FitClass:
    """Return FitClass for PK 4 (80–89 cm bust, normal fit).

    Returns:
        FitClass instance with all ease values from the Mueller & Sohn PK 4 table.
    """
    return FitClass(pk=4)


# ---------------------------------------------------------------------------
# Pytest fixtures (wrap factory functions)
# ---------------------------------------------------------------------------


@pytest.fixture
def standard_person() -> Person:
    """Pytest fixture for standard Person (PK 4, 86 cm bust)."""
    return make_standard_person()


def make_balanced_person() -> BalancedPerson:
    """Return a PersonAnalyser with the standard PK 4 person already balanced.

    Creates a Person with only the fields required for top-garment construction
    (no ``body_rise`` / ``inseam``) and runs
    :class:`~sewpat.person.PersonAnalyser` to produce a balanced
    :class:`~sewpat.person.BalancedPerson` — the form expected by
    :func:`~sewpat.measurements.make_top_measurements`.

    Returns:
        Balanced person ready for :func:`~sewpat.measurements.make_top_measurements`.
    """
    bust = 86 * CM
    p = Person(
        bust=bust,
        waist=70 * CM,
        hip=96 * CM,
        hip_depth=20 * CM,
        bust_depth=26 * CM,
        neck_size=7 * CM,
        bust_span=9 * CM,
        shoulder_width=13 * CM,
        back_length=41 * CM,
        front_length=43 * CM,
        back_width=bust / 8 + 5.5 * CM,
        armscye_depth=bust / 10 + 11 * CM,
        armscye_width=bust / 8 - 1.5 * CM,
        chest_width=bust / 4 - 4.0 * CM,
    )
    return PersonAnalyser(p).get_balanced_person()


@pytest.fixture
def balanced_person() -> BalancedPerson:
    """Pytest fixture for the balanced standard person (PK 4, 86 cm bust)."""
    return make_balanced_person()


@pytest.fixture
def standard_blouse_measurements() -> BlouseMeasurements:
    """Pytest fixture for standard BlouseMeasurements (PK 4, 86 cm bust)."""
    return make_standard_blouse_measurements()


@pytest.fixture
def standard_fitclass() -> FitClass:
    """Pytest fixture for standard FitClass (PK 4)."""
    return make_standard_fitclass()


@pytest.fixture
def top_grid(
    standard_blouse_measurements: BlouseMeasurements, standard_fitclass: FitClass
) -> TopGrid:
    """WAISTED_DART construction grid for the standard PK 4 measurements."""
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
) -> TopBlock:
    """Assembled WAISTED_DART block without seam allowance."""
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    return TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=top_grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
    )


@pytest.fixture
def sleeve_armhole(top_block: TopBlock, top_grid: TopGrid) -> SleeveArmhole:
    """SleeveArmhole extracted from the standard WAISTED_DART block."""
    return SleeveArmhole.from_block(top_block, top_grid)


@pytest.fixture
def sleeve_meas() -> SleeveMeasurements:
    """Standard sleeve body measurements: armscye_width=9 cm, upper_arm=28 cm, wrist=16 cm."""
    return SleeveMeasurements(armscye_width=9 * CM, upper_arm=28 * CM, wrist=16 * CM)


@pytest.fixture
def sleeve_config() -> SleeveConfig:
    """Standard sleeve garment config: 60 cm sleeve length."""
    return SleeveConfig(sleeve_length=60 * CM)


# ---------------------------------------------------------------------------
# Render factory functions
# ---------------------------------------------------------------------------


def make_simple_part(name: str = "body") -> PatternPart:
    """Return a minimal PatternPart with one Segment.

    Args:
        name: Part name (defaults to ``"body"``).

    Returns:
        PatternPart with a single horizontal segment from (0,0) to (10,0).
    """
    part = PatternPart(name=name)
    part.append(Segment(Point(0, 0), Point(10, 0)))
    return part


def make_simple_pattern(name: str = "My Pattern") -> Pattern:
    """Return a Pattern with a front (Segment) and back (Rect) part.

    Args:
        name: Pattern name.

    Returns:
        Pattern with two parts suitable for basic render tests.
    """
    pat = Pattern(name=name)
    p1 = PatternPart(name="front")
    p1.append(Segment(Point(0, 0), Point(10, 0)))
    pat.add_part(p1)
    p2 = PatternPart(name="back")
    p2.append(Rect(Point(20, 0), width=5, height=8))
    pat.add_part(p2)
    return pat


def build_svg_for_part(part: PatternPart, **extra: Any) -> str:
    """Build an SVG string for a single PatternPart with sensible defaults.

    Wraps :func:`~sewpat.render._build_svg` with a 200×200 mm canvas,
    5 mm margin, construction elements shown, and Bézier control points hidden.
    Any keyword argument accepted by ``_build_svg`` can be overridden via
    *extra*.

    Args:
        part: The part to render.
        **extra: Overrides for ``_build_svg`` keyword arguments.

    Returns:
        Complete SVG document string.
    """
    kw: dict[str, Any] = dict(
        title="t",
        element_groups=[part.elements],
        width_mm=200,
        height_mm=200,
        margin_mm=5,
        show_construction=True,
        show_bezier_control_points=False,
    )
    kw.update(extra)
    return _build_svg(**kw)


def build_svg_for_geometry(geometry: Any, **extra: Any) -> str:
    """Build an SVG string for a single geometry object with sensible defaults.

    Convenience wrapper that creates a throwaway :class:`~sewpat.pattern.PatternPart`,
    appends *geometry* to it, and delegates to :func:`build_svg_for_part`.

    Args:
        geometry: Any geometry object accepted by ``PatternPart.append``
            (e.g. :class:`~sewpat.geometry.Segment`, :class:`~sewpat.geometry.Circle`).
        **extra: Overrides forwarded to :func:`build_svg_for_part`.

    Returns:
        Complete SVG document string.
    """
    part = PatternPart(name="p")
    part.append(geometry)
    return build_svg_for_part(part, **extra)


# ---------------------------------------------------------------------------
# Render pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_part() -> PatternPart:
    """Minimal PatternPart with one Segment — ready for render tests."""
    return make_simple_part()


@pytest.fixture
def simple_pattern() -> Pattern:
    """Pattern with front (Segment) and back (Rect) parts."""
    return make_simple_pattern()


@pytest.fixture
def svg_for_part() -> Callable[[PatternPart], str]:
    """Fixture that returns the ``build_svg_for_part`` helper.

    Inject this when a test needs to render multiple parts with
    the same default canvas settings.

    Example::

        def test_something(svg_for_part):
            svg = svg_for_part(my_part)
            assert "<line " in svg
    """
    return build_svg_for_part


@pytest.fixture
def svg_for_geometry() -> Callable[[Any], str]:
    """Fixture that returns the ``build_svg_for_geometry`` helper.

    Inject this when a test needs to render a single geometry object
    without manually constructing a PatternPart.

    Example::

        def test_something(svg_for_geometry):
            svg = svg_for_geometry(Segment(Point(0, 0), Point(10, 0)))
            assert "<line " in svg
    """
    return build_svg_for_geometry


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cm_stretch(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
    sleeve_config: SleeveConfig,
) -> SleeveConstructionMeasures:
    """SleeveConstructionMeasures built with the STRETCH preset."""
    return SleeveConstructionMeasures.from_armhole(
        sleeve_armhole, sleeve_meas, sleeve_config, SleeveBlockConfig.STRETCH, SleeveType.STRETCH
    )


@pytest.fixture
def cm_wide(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
    sleeve_config: SleeveConfig,
) -> SleeveConstructionMeasures:
    """SleeveConstructionMeasures built with the WIDE preset."""
    return SleeveConstructionMeasures.from_armhole(
        sleeve_armhole, sleeve_meas, sleeve_config, SleeveBlockConfig.WIDE, SleeveType.WIDE
    )


@pytest.fixture
def cm_narrow_blouse(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
    sleeve_config: SleeveConfig,
) -> SleeveConstructionMeasures:
    """SleeveConstructionMeasures built with the NARROW_BLOUSE preset."""
    return SleeveConstructionMeasures.from_armhole(
        sleeve_armhole,
        sleeve_meas,
        sleeve_config,
        SleeveBlockConfig.NARROW_BLOUSE,
        SleeveType.NARROW,
    )


@pytest.fixture
def cm_narrow_jacket(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
    sleeve_config: SleeveConfig,
) -> SleeveConstructionMeasures:
    """SleeveConstructionMeasures built with the NARROW_JACKET preset."""
    return SleeveConstructionMeasures.from_armhole(
        sleeve_armhole,
        sleeve_meas,
        sleeve_config,
        SleeveBlockConfig.NARROW_JACKET,
        SleeveType.NARROW,
    )


# ---------------------------------------------------------------------------
# WideSleeveGrid fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def default_wide_grid(
    sleeve_armhole: SleeveArmhole,
    sleeve_config: SleeveConfig,
) -> WideSleeveGrid:
    """WideSleeveGrid built from the standard armhole with default SleeveConfig."""
    return WideSleeveGrid.from_armhole(sleeve_armhole, sleeve_config)


# ---------------------------------------------------------------------------
# Sleeve config with cuff + pleat
# ---------------------------------------------------------------------------


@pytest.fixture
def sleeve_config_with_cuff() -> SleeveConfig:
    """SleeveConfig with a CuffConfig, slit and pleats — exercises the full feature set."""
    return SleeveConfig(
        sleeve_length=62 * CM,
        cap_offset=1 * CM,
        ease=0.0 * CM,
        cuff_config=CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=2 * CM,
            overlap=3 * CM,
            button_config=ButtonConfig(num_buttons=2),
        ),
        slit_height=8 * CM,
        pleat_config=PleatConfig(depth=3 * CM, num_pleats=3, spacing=1.5 * CM),
    )


# ---------------------------------------------------------------------------
# WideSleeveBlock + CuffBlock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wide_sleeve_block(
    sleeve_armhole: SleeveArmhole,
    sleeve_config_with_cuff: SleeveConfig,
) -> WideSleeveBlock:
    """WideSleeveBlock assembled from the standard armhole with cuff + pleat config."""
    return WideSleeveBlock.from_armhole(sleeve_armhole, sleeve_config_with_cuff)


@pytest.fixture
def cuff_block(sleeve_config_with_cuff: SleeveConfig) -> CuffBlock:
    """CuffBlock built from the standard sleeve config with cuff dimensions."""
    result = CuffBlock.from_sleeve_config(sleeve_config_with_cuff)
    assert result is not None, "CuffBlock.from_sleeve_config returned None unexpectedly"
    return result
