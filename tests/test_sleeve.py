"""Tests for sleeve.py — SleeveType, SleeveMode, SleeveBlockConfig, SleeveConfig,
SleeveMeasurements, SleeveArmhole, SleeveConstructionMeasures."""

import pytest

from sewpat.geometry import CubicBezier, Point
from sewpat.measurements import BlouseMeasurements
from sewpat.person import Person
from sewpat.sleeve import (
    SleeveArmhole,
    SleeveBlockConfig,
    SleeveConfig,
    SleeveConstructionMeasures,
    SleeveMeasurements,
    SleeveMode,
    SleeveType,
)
from sewpat.units import CM

# ---------------------------------------------------------------------------
# SleeveType
# ---------------------------------------------------------------------------


def test_sleeve_type_has_three_variants() -> None:
    """SleeveType enum exposes exactly three members: STRETCH, WIDE, NARROW."""
    assert SleeveType.STRETCH is not None
    assert SleeveType.WIDE is not None
    assert SleeveType.NARROW is not None
    assert len(SleeveType) == 3


def test_sleeve_type_values() -> None:
    """Each SleeveType variant stores the expected string value."""
    assert SleeveType.STRETCH.value == "stretch"
    assert SleeveType.WIDE.value == "wide"
    assert SleeveType.NARROW.value == "narrow"


# ---------------------------------------------------------------------------
# SleeveMode
# ---------------------------------------------------------------------------


def test_sleeve_mode_has_four_variants() -> None:
    """SleeveMode enum exposes exactly four members."""
    assert len(SleeveMode) == 4


def test_sleeve_mode_values() -> None:
    """Each SleeveMode variant stores the expected string value."""
    assert SleeveMode.STRETCH.value == "stretch"
    assert SleeveMode.WIDE.value == "wide"
    assert SleeveMode.NARROW_BLOUSE.value == "narrow_blouse"
    assert SleeveMode.NARROW_JACKET.value == "narrow_jacket"


# ---------------------------------------------------------------------------
# SleeveBlockConfig — derived properties (fixed by mode)
# ---------------------------------------------------------------------------


def test_sleeve_block_config_stretch_uses_circumference() -> None:
    """STRETCH: cap_uses_circumference is True (armscye circumference-based formula)."""
    assert SleeveBlockConfig.STRETCH.cap_uses_circumference is True


def test_sleeve_block_config_wide_uses_circumference() -> None:
    """WIDE: cap_uses_circumference is False (armscye height-based formula)."""
    assert SleeveBlockConfig.WIDE.cap_uses_circumference is False


def test_sleeve_block_config_narrow_blouse_uses_height() -> None:
    """NARROW_BLOUSE: cap_uses_circumference is False (armscye height-based formula)."""
    assert SleeveBlockConfig.NARROW_BLOUSE.cap_uses_circumference is False


def test_sleeve_block_config_narrow_jacket_uses_height() -> None:
    """NARROW_JACKET: cap_uses_circumference is False (armscye height-based formula)."""
    assert SleeveBlockConfig.NARROW_JACKET.cap_uses_circumference is False


def test_sleeve_block_config_stretch_cap_frac() -> None:
    """STRETCH cap_height_frac is 1/3."""
    assert SleeveBlockConfig.STRETCH.cap_height_frac == pytest.approx(1.0 / 3.0)


def test_sleeve_block_config_wide_cap_frac() -> None:
    """WIDE cap_height_frac is 1/3."""
    assert SleeveBlockConfig.WIDE.cap_height_frac == pytest.approx(1.0 / 3.0)


def test_sleeve_block_config_narrow_blouse_cap_frac() -> None:
    """NARROW_BLOUSE cap_height_frac is 1/2."""
    assert SleeveBlockConfig.NARROW_BLOUSE.cap_height_frac == pytest.approx(0.5)


def test_sleeve_block_config_narrow_jacket_cap_frac() -> None:
    """NARROW_JACKET cap_height_frac is 1/2."""
    assert SleeveBlockConfig.NARROW_JACKET.cap_height_frac == pytest.approx(0.5)


def test_sleeve_block_config_narrow_blouse_arm_diameter_frac() -> None:
    """NARROW_BLOUSE cap_arm_diameter_frac is 1/5 (arm_diameter/5 correction term)."""
    assert SleeveBlockConfig.NARROW_BLOUSE.cap_arm_diameter_frac == pytest.approx(1.0 / 5.0)


def test_sleeve_block_config_narrow_jacket_arm_diameter_frac() -> None:
    """NARROW_JACKET cap_arm_diameter_frac is 1/10 (arm_diameter/10 correction term)."""
    assert SleeveBlockConfig.NARROW_JACKET.cap_arm_diameter_frac == pytest.approx(1.0 / 10.0)


def test_sleeve_block_config_stretch_zero_arm_diameter_frac() -> None:
    """STRETCH cap_arm_diameter_frac is 0 (no arm diameter correction term)."""
    assert SleeveBlockConfig.STRETCH.cap_arm_diameter_frac == pytest.approx(0.0)


def test_sleeve_block_config_wide_zero_arm_diameter_frac() -> None:
    """WIDE cap_arm_diameter_frac is 0 (no arm diameter correction term)."""
    assert SleeveBlockConfig.WIDE.cap_arm_diameter_frac == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# SleeveBlockConfig — preset constant values
# ---------------------------------------------------------------------------


def test_sleeve_block_config_stretch_cap_offset_is_zero() -> None:
    """STRETCH cap_offset is 0 (ÄkH = AlU / 3 with no additive constant)."""
    assert SleeveBlockConfig.STRETCH.cap_offset == pytest.approx(0.0)


def test_sleeve_block_config_wide_cap_offset_in_range() -> None:
    """WIDE cap_offset is within the allowed range [−2, 0] cm."""
    assert -2.0 * CM <= SleeveBlockConfig.WIDE.cap_offset <= 0.0


def test_sleeve_block_config_narrow_blouse_cap_offset_in_range() -> None:
    """NARROW_BLOUSE cap_offset is within [−0.5, −1.5] cm (const ∈ [0.5, 1.5] cm)."""
    assert -1.5 * CM <= SleeveBlockConfig.NARROW_BLOUSE.cap_offset <= -0.5 * CM


def test_sleeve_block_config_narrow_jacket_cap_offset_in_range() -> None:
    """NARROW_JACKET cap_offset is within [−1, −2] cm (const ∈ [1, 2] cm)."""
    assert -2.0 * CM <= SleeveBlockConfig.NARROW_JACKET.cap_offset <= -1.0 * CM


def test_sleeve_block_config_wide_oa_ease_is_none() -> None:
    """WIDE oa_ease is None (OaW not defined for this sleeve type)."""
    assert SleeveBlockConfig.WIDE.upper_arm_ease is None


def test_sleeve_block_config_wide_hem_ease_is_none() -> None:
    """WIDE hem_ease is None (sleeve hem width not defined for this sleeve type)."""
    assert SleeveBlockConfig.WIDE.hem_ease is None


def test_sleeve_block_config_stretch_oa_ease_in_range() -> None:
    """STRETCH oa_ease is within [−1, +2] cm."""
    assert -1.0 * CM <= SleeveBlockConfig.STRETCH.upper_arm_ease <= 2.0 * CM  # type: ignore[operator]


def test_sleeve_block_config_stretch_hem_ease_in_range() -> None:
    """STRETCH hem_ease is within [0, 5] cm."""
    assert 0.0 <= SleeveBlockConfig.STRETCH.hem_ease <= 5.0 * CM  # type: ignore[operator]


def test_sleeve_block_config_narrow_blouse_oa_ease_in_range() -> None:
    """NARROW_BLOUSE oa_ease is within [2, 4] cm."""
    assert 2.0 * CM <= SleeveBlockConfig.NARROW_BLOUSE.upper_arm_ease <= 4.0 * CM  # type: ignore[operator]


def test_sleeve_block_config_narrow_blouse_hem_ease_in_range() -> None:
    """NARROW_BLOUSE hem_ease is within [2, 10] cm."""
    assert 2.0 * CM <= SleeveBlockConfig.NARROW_BLOUSE.hem_ease <= 10.0 * CM  # type: ignore[operator]


def test_sleeve_block_config_narrow_jacket_oa_ease_in_range() -> None:
    """NARROW_JACKET oa_ease is within [4, 8] cm."""
    assert 4.0 * CM <= SleeveBlockConfig.NARROW_JACKET.upper_arm_ease <= 8.0 * CM  # type: ignore[operator]


def test_sleeve_block_config_narrow_jacket_hem_ease_in_range() -> None:
    """NARROW_JACKET hem_ease is within [8, 16] cm."""
    assert 8.0 * CM <= SleeveBlockConfig.NARROW_JACKET.hem_ease <= 16.0 * CM  # type: ignore[operator]


def test_sleeve_block_config_narrow_jacket_more_ease_than_blouse() -> None:
    """NARROW_JACKET oa_ease > NARROW_BLOUSE oa_ease (more ease for structured garments)."""
    assert (
        SleeveBlockConfig.NARROW_JACKET.upper_arm_ease
        > SleeveBlockConfig.NARROW_BLOUSE.upper_arm_ease
    )  # type: ignore[operator]


# ---------------------------------------------------------------------------
# SleeveBlockConfig — validation: STRETCH mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset_cm", [0.5, -0.5, 1.0])
def test_sleeve_block_config_stretch_rejects_nonzero_cap_offset(offset_cm: float) -> None:
    """STRETCH rejects cap_offset != 0 — formula is ÄkH = AlU/3 with no constant."""
    with pytest.raises(ValueError, match="cap_offset"):
        SleeveBlockConfig(
            mode=SleeveMode.STRETCH,
            cap_offset=offset_cm * CM,
            upper_arm_ease=0.5 * CM,
            hem_ease=2.5 * CM,
        )


def test_sleeve_block_config_stretch_rejects_none_oa_ease() -> None:
    """STRETCH rejects upper_arm_ease=None — OaW formula is always required."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.STRETCH, cap_offset=0.0, upper_arm_ease=None, hem_ease=2.5 * CM
        )


@pytest.mark.parametrize("ease_cm", [-1.1, -2.0, 2.1, 3.0])
def test_sleeve_block_config_stretch_rejects_oa_ease_out_of_range(ease_cm: float) -> None:
    """STRETCH rejects oa_ease outside [−1, +2] cm."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.STRETCH, cap_offset=0.0, upper_arm_ease=ease_cm * CM, hem_ease=2.5 * CM
        )


@pytest.mark.parametrize("ease_cm", [-0.1, 5.1])
def test_sleeve_block_config_stretch_rejects_hem_ease_out_of_range(ease_cm: float) -> None:
    """STRETCH rejects hem_ease outside [0, 5] cm."""
    with pytest.raises(ValueError, match="hem_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.STRETCH, cap_offset=0.0, upper_arm_ease=0.5 * CM, hem_ease=ease_cm * CM
        )


@pytest.mark.parametrize("upper_arm_ease_cm,hem_cm", [(-1.0, 0.0), (0.0, 2.5), (2.0, 5.0)])
def test_sleeve_block_config_stretch_accepts_boundary_values(
    upper_arm_ease_cm: float, hem_cm: float
) -> None:
    """STRETCH accepts oa_ease and hem_ease at their boundary values."""
    cfg = SleeveBlockConfig(
        mode=SleeveMode.STRETCH,
        cap_offset=0.0,
        upper_arm_ease=upper_arm_ease_cm * CM,
        hem_ease=hem_cm * CM,
    )
    assert cfg.upper_arm_ease == pytest.approx(upper_arm_ease_cm * CM)
    assert cfg.hem_ease == pytest.approx(hem_cm * CM)


# ---------------------------------------------------------------------------
# SleeveBlockConfig — validation: WIDE mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset_cm", [0.1, 1.0, -2.1, -3.0])
def test_sleeve_block_config_wide_rejects_cap_offset_out_of_range(offset_cm: float) -> None:
    """WIDE rejects cap_offset outside [−2, 0] cm."""
    with pytest.raises(ValueError, match="cap_offset"):
        SleeveBlockConfig(
            mode=SleeveMode.WIDE, cap_offset=offset_cm * CM, upper_arm_ease=None, hem_ease=None
        )


def test_sleeve_block_config_wide_rejects_nonnone_oa_ease() -> None:
    """WIDE rejects oa_ease != None — sleeve width is not defined for this sleeve type."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.WIDE, cap_offset=-1.0 * CM, upper_arm_ease=3.0 * CM, hem_ease=None
        )


def test_sleeve_block_config_wide_rejects_nonnone_hem_ease() -> None:
    """WIDE rejects hem_ease != None — sleeve hem width is not defined for this sleeve type."""
    with pytest.raises(ValueError, match="hem_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.WIDE, cap_offset=-1.0 * CM, upper_arm_ease=None, hem_ease=5.0 * CM
        )


@pytest.mark.parametrize("offset_cm", [-2.0, -1.0, 0.0])
def test_sleeve_block_config_wide_accepts_boundary_cap_offset(offset_cm: float) -> None:
    """WIDE accepts cap_offset at each boundary value."""
    cfg = SleeveBlockConfig(
        mode=SleeveMode.WIDE, cap_offset=offset_cm * CM, upper_arm_ease=None, hem_ease=None
    )
    assert cfg.cap_offset == pytest.approx(offset_cm * CM)


# ---------------------------------------------------------------------------
# SleeveBlockConfig — validation: NARROW_BLOUSE mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset_cm", [0.0, -0.4, -1.6, -2.0])
def test_sleeve_block_config_narrow_blouse_rejects_cap_offset_out_of_range(
    offset_cm: float,
) -> None:
    """NARROW_BLOUSE rejects cap_offset outside [−0.5, −1.5] cm."""
    with pytest.raises(ValueError, match="cap_offset"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_BLOUSE,
            cap_offset=offset_cm * CM,
            upper_arm_ease=3.0 * CM,
            hem_ease=6.0 * CM,
        )


@pytest.mark.parametrize("ease_cm", [1.0, 1.9, 4.1, 5.0])
def test_sleeve_block_config_narrow_blouse_rejects_oa_ease_out_of_range(ease_cm: float) -> None:
    """NARROW_BLOUSE rejects oa_ease outside [2, 4] cm."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_BLOUSE,
            cap_offset=-1.0 * CM,
            upper_arm_ease=ease_cm * CM,
            hem_ease=6.0 * CM,
        )


@pytest.mark.parametrize("ease_cm", [1.0, 1.9, 10.1, 12.0])
def test_sleeve_block_config_narrow_blouse_rejects_hem_ease_out_of_range(ease_cm: float) -> None:
    """NARROW_BLOUSE rejects hem_ease outside [2, 10] cm."""
    with pytest.raises(ValueError, match="hem_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_BLOUSE,
            cap_offset=-1.0 * CM,
            upper_arm_ease=3.0 * CM,
            hem_ease=ease_cm * CM,
        )


@pytest.mark.parametrize(
    "offset_cm,upper_arm_ease_cm,hem_cm", [(-0.5, 2.0, 2.0), (-1.0, 3.0, 6.0), (-1.5, 4.0, 10.0)]
)
def test_sleeve_block_config_narrow_blouse_accepts_boundary_values(
    offset_cm: float, upper_arm_ease_cm: float, hem_cm: float
) -> None:
    """NARROW_BLOUSE accepts all constants at their boundary values."""
    cfg = SleeveBlockConfig(
        mode=SleeveMode.NARROW_BLOUSE,
        cap_offset=offset_cm * CM,
        upper_arm_ease=upper_arm_ease_cm * CM,
        hem_ease=hem_cm * CM,
    )
    assert cfg.cap_offset == pytest.approx(offset_cm * CM)


# ---------------------------------------------------------------------------
# SleeveBlockConfig — validation: NARROW_JACKET mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset_cm", [0.0, -0.9, -2.1, -3.0])
def test_sleeve_block_config_narrow_jacket_rejects_cap_offset_out_of_range(
    offset_cm: float,
) -> None:
    """NARROW_JACKET rejects cap_offset outside [−1, −2] cm."""
    with pytest.raises(ValueError, match="cap_offset"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_JACKET,
            cap_offset=offset_cm * CM,
            upper_arm_ease=6.0 * CM,
            hem_ease=12.0 * CM,
        )


@pytest.mark.parametrize("ease_cm", [1.0, 3.9, 8.1, 10.0])
def test_sleeve_block_config_narrow_jacket_rejects_oa_ease_out_of_range(ease_cm: float) -> None:
    """NARROW_JACKET rejects oa_ease outside [4, 8] cm."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_JACKET,
            cap_offset=-1.5 * CM,
            upper_arm_ease=ease_cm * CM,
            hem_ease=12.0 * CM,
        )


@pytest.mark.parametrize("ease_cm", [1.0, 7.9, 16.1, 18.0])
def test_sleeve_block_config_narrow_jacket_rejects_hem_ease_out_of_range(ease_cm: float) -> None:
    """NARROW_JACKET rejects hem_ease outside [8, 16] cm."""
    with pytest.raises(ValueError, match="hem_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_JACKET,
            cap_offset=-1.5 * CM,
            upper_arm_ease=6.0 * CM,
            hem_ease=ease_cm * CM,
        )


@pytest.mark.parametrize(
    "offset_cm,upper_arm_ease_cm,hem_cm", [(-1.0, 4.0, 8.0), (-1.5, 6.0, 12.0), (-2.0, 8.0, 16.0)]
)
def test_sleeve_block_config_narrow_jacket_accepts_boundary_values(
    offset_cm: float, upper_arm_ease_cm: float, hem_cm: float
) -> None:
    """NARROW_JACKET accepts all constants at their boundary values."""
    cfg = SleeveBlockConfig(
        mode=SleeveMode.NARROW_JACKET,
        cap_offset=offset_cm * CM,
        upper_arm_ease=upper_arm_ease_cm * CM,
        hem_ease=hem_cm * CM,
    )
    assert cfg.cap_offset == pytest.approx(offset_cm * CM)


# NARROW_BLOUSE and NARROW_JACKET reject each other's ranges
def test_sleeve_block_config_narrow_jacket_rejects_blouse_oa_ease() -> None:
    """NARROW_JACKET rejects oa_ease in the NARROW_BLOUSE range [2, 4) cm."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_JACKET,
            cap_offset=-1.5 * CM,
            upper_arm_ease=3.0 * CM,
            hem_ease=12.0 * CM,
        )


def test_sleeve_block_config_narrow_blouse_rejects_jacket_oa_ease() -> None:
    """NARROW_BLOUSE rejects oa_ease in the NARROW_JACKET range (4, 8] cm."""
    with pytest.raises(ValueError, match="upper_arm_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_BLOUSE,
            cap_offset=-1.0 * CM,
            upper_arm_ease=6.0 * CM,
            hem_ease=6.0 * CM,
        )


def test_sleeve_block_config_narrow_jacket_rejects_blouse_hem_ease() -> None:
    """NARROW_JACKET rejects hem_ease in the NARROW_BLOUSE range [2, 8) cm."""
    with pytest.raises(ValueError, match="hem_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_JACKET,
            cap_offset=-1.5 * CM,
            upper_arm_ease=6.0 * CM,
            hem_ease=6.0 * CM,
        )


def test_sleeve_block_config_narrow_blouse_rejects_jacket_hem_ease() -> None:
    """NARROW_BLOUSE rejects hem_ease in the NARROW_JACKET range (10, 16] cm."""
    with pytest.raises(ValueError, match="hem_ease"):
        SleeveBlockConfig(
            mode=SleeveMode.NARROW_BLOUSE,
            cap_offset=-1.0 * CM,
            upper_arm_ease=3.0 * CM,
            hem_ease=12.0 * CM,
        )


# All built-in presets must survive their own validation
@pytest.mark.parametrize(
    "preset",
    [
        SleeveBlockConfig.STRETCH,
        SleeveBlockConfig.WIDE,
        SleeveBlockConfig.NARROW_BLOUSE,
        SleeveBlockConfig.NARROW_JACKET,
    ],
    ids=["STRETCH", "WIDE", "NARROW_BLOUSE", "NARROW_JACKET"],
)
def test_sleeve_block_config_all_presets_pass_validation(preset: SleeveBlockConfig) -> None:
    """Every built-in SleeveBlockConfig preset passes its own __post_init__ validation."""
    from dataclasses import asdict

    SleeveBlockConfig(**asdict(preset))  # must not raise


# ---------------------------------------------------------------------------
# SleeveConfig
# ---------------------------------------------------------------------------


def test_sleeve_config_stores_sleeve_length() -> None:
    """SleeveConfig stores the given sleeve length correctly."""
    cfg = SleeveConfig(sleeve_length=58 * CM)
    assert cfg.sleeve_length == pytest.approx(58 * CM)


# ---------------------------------------------------------------------------
# SleeveMeasurements
# ---------------------------------------------------------------------------


def test_sleeve_measurements_raises_without_upper_arm(
    standard_blouse_measurements: BlouseMeasurements,
) -> None:
    """from_blouse_and_person raises ValueError when person.upper_arm is None."""
    person = Person(wrist=16 * CM)
    with pytest.raises(ValueError, match="upper_arm"):
        SleeveMeasurements.from_blouse_and_person(standard_blouse_measurements, person)


def test_sleeve_measurements_raises_without_wrist(
    standard_blouse_measurements: BlouseMeasurements,
) -> None:
    """from_blouse_and_person raises ValueError when person.wrist is None."""
    person = Person(upper_arm=28 * CM)
    with pytest.raises(ValueError, match="wrist"):
        SleeveMeasurements.from_blouse_and_person(standard_blouse_measurements, person)


def test_sleeve_measurements_from_blouse_and_person(
    standard_blouse_measurements: BlouseMeasurements,
) -> None:
    """from_blouse_and_person correctly extracts all three fields."""
    person = Person(upper_arm=28 * CM, wrist=16 * CM)
    sm = SleeveMeasurements.from_blouse_and_person(standard_blouse_measurements, person)
    assert sm.armscye_width == pytest.approx(standard_blouse_measurements.armscye_width)
    assert sm.upper_arm == pytest.approx(28 * CM)
    assert sm.wrist == pytest.approx(16 * CM)


def test_sleeve_measurements_direct_construction() -> None:
    """SleeveMeasurements can be constructed directly with explicit values."""
    sm = SleeveMeasurements(armscye_width=9 * CM, upper_arm=28 * CM, wrist=16 * CM)
    assert sm.armscye_width == pytest.approx(9 * CM)
    assert sm.upper_arm == pytest.approx(28 * CM)
    assert sm.wrist == pytest.approx(16 * CM)


# ---------------------------------------------------------------------------
# SleeveArmhole — from_block
# ---------------------------------------------------------------------------


def test_sleeve_armhole_from_block_type(sleeve_armhole: SleeveArmhole) -> None:
    """from_block returns a SleeveArmhole instance."""
    assert isinstance(sleeve_armhole, SleeveArmhole)


def test_sleeve_armhole_back_lower_is_cubic_bezier(sleeve_armhole: SleeveArmhole) -> None:
    """back_armscye_lower is a CubicBezier."""
    assert isinstance(sleeve_armhole.back_armscye_lower, CubicBezier)


def test_sleeve_armhole_back_upper_is_cubic_bezier(sleeve_armhole: SleeveArmhole) -> None:
    """back_armscye_upper is a CubicBezier."""
    assert isinstance(sleeve_armhole.back_armscye_upper, CubicBezier)


def test_sleeve_armhole_front_is_cubic_bezier(sleeve_armhole: SleeveArmhole) -> None:
    """front_armscye is a CubicBezier."""
    assert isinstance(sleeve_armhole.front_armscye, CubicBezier)


def test_sleeve_armhole_back_armscye_notch_is_point(sleeve_armhole: SleeveArmhole) -> None:
    """back_armscye_notch (hÄP) is a Point."""
    assert isinstance(sleeve_armhole.back_armscye_notch, Point)


def test_sleeve_armhole_front_armscye_notch_is_point(sleeve_armhole: SleeveArmhole) -> None:
    """front_armscye_notch (vÄP) is a Point."""
    assert isinstance(sleeve_armhole.front_armscye_notch, Point)


def test_sleeve_armhole_height_is_positive(sleeve_armhole: SleeveArmhole) -> None:
    """armscye_height (AlH) is a positive value."""
    assert sleeve_armhole.armscye_height > 0.0


def test_sleeve_armhole_height_reasonable(sleeve_armhole: SleeveArmhole) -> None:
    """armscye_height (AlH) is between 20 cm and 55 cm (back + front combined)."""
    assert 20 * CM <= sleeve_armhole.armscye_height <= 55 * CM


def test_sleeve_armhole_back_height_is_positive(sleeve_armhole: SleeveArmhole) -> None:
    """back_armscye_height is a positive value."""
    assert sleeve_armhole.back_armscye_height > 0.0


def test_sleeve_armhole_back_height_equals_orthogonal_distance(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """back_armscye_height equals p3.distance_to(bust_line.project_point(p3))."""
    pt = sleeve_armhole.back_armscye_upper.p3
    expected = pt.distance_to(sleeve_armhole.bust_line.project_point(pt))
    assert sleeve_armhole.back_armscye_height == pytest.approx(expected)


def test_sleeve_armhole_front_height_is_positive(sleeve_armhole: SleeveArmhole) -> None:
    """front_armscye_height is a positive value."""
    assert sleeve_armhole.front_armscye_height > 0.0


def test_sleeve_armhole_front_height_reasonable(sleeve_armhole: SleeveArmhole) -> None:
    """front_armscye_height is between 10 cm and 30 cm for a standard bodice."""
    assert 10 * CM <= sleeve_armhole.front_armscye_height <= 30 * CM


def test_sleeve_armhole_front_height_is_distance_to_bust_intersection(
    sleeve_armhole: SleeveArmhole,
) -> None:
    """front_armscye_height = distance from front_armscye.p0 to (armscye_front_line ∩ bust_line)."""
    from sewpat.geometry import intersect

    pt_shoulder = sleeve_armhole.front_armscye.p0
    pt_bottom = intersect(sleeve_armhole.armscye_front_line, sleeve_armhole.bust_line)[0]
    expected = pt_shoulder.distance_to(pt_bottom)
    assert sleeve_armhole.front_armscye_height == pytest.approx(expected)


def test_sleeve_armhole_height_is_sum_of_components(sleeve_armhole: SleeveArmhole) -> None:
    """armscye_height equals back_armscye_height + front_armscye_height."""
    assert sleeve_armhole.armscye_height == pytest.approx(
        sleeve_armhole.back_armscye_height + sleeve_armhole.front_armscye_height
    )


def test_sleeve_armhole_circumference_is_positive(sleeve_armhole: SleeveArmhole) -> None:
    """armscye_circumference (AlU) is a positive value."""
    assert sleeve_armhole.armscye_circumference > 0.0


def test_sleeve_armhole_circumference_reasonable(sleeve_armhole: SleeveArmhole) -> None:
    """armscye_circumference (AlU) is between 30 cm and 60 cm for a standard bodice."""
    assert 30 * CM <= sleeve_armhole.armscye_circumference <= 60 * CM


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — STRETCH
# ---------------------------------------------------------------------------


def test_sleeve_cm_stretch_type(cm_stretch: SleeveConstructionMeasures) -> None:
    """from_armhole returns a SleeveConstructionMeasures instance."""
    assert isinstance(cm_stretch, SleeveConstructionMeasures)


def test_sleeve_cm_stretch_armscye_height(
    sleeve_armhole: SleeveArmhole, cm_stretch: SleeveConstructionMeasures
) -> None:
    """STRETCH: armscye_height matches armhole.armscye_height."""
    assert cm_stretch.armscye_height == pytest.approx(sleeve_armhole.armscye_height)


def test_sleeve_cm_stretch_armscye_circumference(
    sleeve_armhole: SleeveArmhole, cm_stretch: SleeveConstructionMeasures
) -> None:
    """STRETCH: armscye_circumference matches armhole.armscye_circumference."""
    assert cm_stretch.armscye_circumference == pytest.approx(sleeve_armhole.armscye_circumference)


def test_sleeve_cm_stretch_cap_height_from_circumference(
    sleeve_armhole: SleeveArmhole, cm_stretch: SleeveConstructionMeasures
) -> None:
    """STRETCH: cap_height = armscye_circumference / 3."""
    assert cm_stretch.cap_height == pytest.approx(sleeve_armhole.armscye_circumference / 3.0)


def test_sleeve_cm_stretch_sleeve_width(cm_stretch: SleeveConstructionMeasures) -> None:
    """STRETCH: sleeve_width = upper_arm_circumference + oa_ease."""
    assert cm_stretch.sleeve_width == pytest.approx(
        28 * CM + SleeveBlockConfig.STRETCH.upper_arm_ease
    )


def test_sleeve_cm_stretch_sleeve_hem_width(cm_stretch: SleeveConstructionMeasures) -> None:
    """STRETCH: sleeve_hem_width = wrist_circumference + hem_ease."""
    assert cm_stretch.sleeve_hem_width == pytest.approx(
        16 * CM + SleeveBlockConfig.STRETCH.hem_ease
    )


def test_sleeve_cm_stretch_oa_ease_stored(cm_stretch: SleeveConstructionMeasures) -> None:
    """STRETCH: oa_ease equals the oa_ease constant from the block config."""
    assert cm_stretch.upper_arm_ease == pytest.approx(SleeveBlockConfig.STRETCH.upper_arm_ease)


def test_sleeve_cm_stretch_sleeve_type(cm_stretch: SleeveConstructionMeasures) -> None:
    """STRETCH: sleeve_type is stored correctly."""
    assert cm_stretch.sleeve_type is SleeveType.STRETCH


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — WIDE
# ---------------------------------------------------------------------------


def test_sleeve_cm_wide_cap_height_from_height_plus_offset(
    sleeve_armhole: SleeveArmhole, cm_wide: SleeveConstructionMeasures
) -> None:
    """WIDE: cap_height = armscye_height / 3 + block_config.cap_offset."""
    expected = sleeve_armhole.armscye_height / 3.0 + SleeveBlockConfig.WIDE.cap_offset
    assert cm_wide.cap_height == pytest.approx(expected)


def test_sleeve_cm_wide_sleeve_width_is_computed(
    sleeve_armhole: SleeveArmhole,
    cm_wide: SleeveConstructionMeasures,
    sleeve_config: SleeveConfig,
) -> None:
    """WIDE: sleeve_width is the half-width computed via the Pythagorean formula.

    sleeve_width = sqrt((armscye_circumference / 2 − ease)² − cap_height²)
    The full sleeve spans 2 × sleeve_width.
    """
    import math

    cap_height = sleeve_armhole.armscye_height / 3.0 + SleeveBlockConfig.WIDE.cap_offset
    expected = math.sqrt(
        (sleeve_armhole.armscye_circumference / 2 - sleeve_config.ease) ** 2 - cap_height**2
    )
    assert cm_wide.sleeve_width is not None
    assert cm_wide.sleeve_width == pytest.approx(expected)


def test_sleeve_cm_wide_sleeve_hem_width_is_none(cm_wide: SleeveConstructionMeasures) -> None:
    """WIDE: sleeve_hem_width is None (not applicable for this sleeve type)."""
    assert cm_wide.sleeve_hem_width is None


def test_sleeve_cm_wide_oa_ease_is_none(cm_wide: SleeveConstructionMeasures) -> None:
    """WIDE: oa_ease is None (no upper-arm ease formula)."""
    assert cm_wide.upper_arm_ease is None


def test_sleeve_cm_wide_cap_height_less_than_stretch(
    cm_stretch: SleeveConstructionMeasures,
    cm_wide: SleeveConstructionMeasures,
) -> None:
    """WIDE cap_height is lower than STRETCH cap_height due to negative cap_offset."""
    assert cm_wide.cap_height < cm_stretch.cap_height


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — NARROW_BLOUSE
# ---------------------------------------------------------------------------


def test_sleeve_cm_narrow_blouse_cap_height_formula(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
    cm_narrow_blouse: SleeveConstructionMeasures,
) -> None:
    """NARROW_BLOUSE: cap_height = armscye_height/2 − armscye_width/5 + cap_offset."""
    cfg = SleeveBlockConfig.NARROW_BLOUSE
    expected = (
        sleeve_armhole.armscye_height * 0.5 - sleeve_meas.armscye_width / 5.0 + cfg.cap_offset
    )
    assert cm_narrow_blouse.cap_height == pytest.approx(expected)


def test_sleeve_cm_narrow_blouse_sleeve_width(cm_narrow_blouse: SleeveConstructionMeasures) -> None:
    """NARROW_BLOUSE: sleeve_width = upper_arm_circumference + oa_ease."""
    assert cm_narrow_blouse.sleeve_width == pytest.approx(
        28 * CM + SleeveBlockConfig.NARROW_BLOUSE.upper_arm_ease
    )


def test_sleeve_cm_narrow_blouse_sleeve_hem_width(
    cm_narrow_blouse: SleeveConstructionMeasures,
) -> None:
    """NARROW_BLOUSE: sleeve_hem_width = wrist_circumference + hem_ease."""
    assert cm_narrow_blouse.sleeve_hem_width == pytest.approx(
        16 * CM + SleeveBlockConfig.NARROW_BLOUSE.hem_ease
    )


def test_sleeve_cm_narrow_blouse_sleeve_type(
    cm_narrow_blouse: SleeveConstructionMeasures,
) -> None:
    """NARROW_BLOUSE: sleeve_type is SleeveType.NARROW."""
    assert cm_narrow_blouse.sleeve_type is SleeveType.NARROW


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures — NARROW_JACKET
# ---------------------------------------------------------------------------


def test_sleeve_cm_narrow_jacket_cap_height_formula(
    sleeve_armhole: SleeveArmhole,
    sleeve_meas: SleeveMeasurements,
    cm_narrow_jacket: SleeveConstructionMeasures,
) -> None:
    """NARROW_JACKET: cap_height = armscye_height/2 − armscye_width/10 + cap_offset."""
    cfg = SleeveBlockConfig.NARROW_JACKET
    expected = (
        sleeve_armhole.armscye_height * 0.5 - sleeve_meas.armscye_width / 10.0 + cfg.cap_offset
    )
    assert cm_narrow_jacket.cap_height == pytest.approx(expected)


def test_sleeve_cm_narrow_jacket_cap_height_higher_than_blouse(
    cm_narrow_blouse: SleeveConstructionMeasures,
    cm_narrow_jacket: SleeveConstructionMeasures,
) -> None:
    """NARROW_JACKET cap_height is higher than NARROW_BLOUSE
    (smaller arm diameter divisor, smaller offset)."""
    assert cm_narrow_jacket.cap_height > cm_narrow_blouse.cap_height


def test_sleeve_cm_narrow_jacket_sleeve_width(cm_narrow_jacket: SleeveConstructionMeasures) -> None:
    """NARROW_JACKET: sleeve_width = upper_arm_circumference + oa_ease."""
    assert cm_narrow_jacket.sleeve_width == pytest.approx(
        28 * CM + SleeveBlockConfig.NARROW_JACKET.upper_arm_ease
    )


def test_sleeve_cm_narrow_jacket_wider_than_blouse(
    cm_narrow_blouse: SleeveConstructionMeasures,
    cm_narrow_jacket: SleeveConstructionMeasures,
) -> None:
    """NARROW_JACKET sleeve_width > NARROW_BLOUSE sleeve_width
    (more ease for structured outerwear)."""
    assert cm_narrow_jacket.sleeve_width > cm_narrow_blouse.sleeve_width  # type: ignore[operator]


def test_sleeve_cm_narrow_jacket_sleeve_hem_width(
    cm_narrow_jacket: SleeveConstructionMeasures,
) -> None:
    """NARROW_JACKET: sleeve_hem_width = wrist_circumference + hem_ease."""
    assert cm_narrow_jacket.sleeve_hem_width == pytest.approx(
        16 * CM + SleeveBlockConfig.NARROW_JACKET.hem_ease
    )


def test_sleeve_cm_narrow_blouse_sleeve_length_stored(
    cm_narrow_blouse: SleeveConstructionMeasures,
    sleeve_config: SleeveConfig,
) -> None:
    """sleeve_length is taken directly from SleeveConfig.sleeve_length."""
    assert cm_narrow_blouse.sleeve_length == pytest.approx(sleeve_config.sleeve_length)


def test_sleeve_cm_narrow_blouse_armscye_width_stored(
    cm_narrow_blouse: SleeveConstructionMeasures,
    sleeve_meas: SleeveMeasurements,
) -> None:
    """armscye_width is taken directly from SleeveMeasurements.armscye_width."""
    assert cm_narrow_blouse.armscye_width == pytest.approx(sleeve_meas.armscye_width)


# ---------------------------------------------------------------------------
# WideSleeveBlockConfig — validation
# ---------------------------------------------------------------------------


def test_wide_sleeve_block_config_valid_defaults() -> None:
    """WideSleeveBlockConfig with all defaults constructs without error."""
    from sewpat.sleeve import WideSleeveBlockConfig

    cfg = WideSleeveBlockConfig()
    assert len(cfg.cap_left_notch_params) == 3
    assert len(cfg.cap_right_notch_params) == 3
    assert len(cfg.hem_notch_params) == 5


def test_wide_sleeve_block_config_rejects_short_cap_left_notch_params() -> None:
    """WideSleeveBlockConfig rejects cap_left_notch_params with fewer than 3 entries."""
    from sewpat.sleeve import WideSleeveBlockConfig

    with pytest.raises(ValueError, match="cap_left_notch_params"):
        WideSleeveBlockConfig(cap_left_notch_params=((0.25, 1.0), (0.75, 2.0)))


def test_wide_sleeve_block_config_rejects_short_cap_right_notch_params() -> None:
    """WideSleeveBlockConfig rejects cap_right_notch_params with fewer than 3 entries."""
    from sewpat.sleeve import WideSleeveBlockConfig

    with pytest.raises(ValueError, match="cap_right_notch_params"):
        WideSleeveBlockConfig(cap_right_notch_params=((0.5, 0.0),))


def test_wide_sleeve_block_config_rejects_wrong_hem_notch_param_count() -> None:
    """WideSleeveBlockConfig rejects hem_notch_params that do not have exactly 5 entries."""
    from sewpat.sleeve import WideSleeveBlockConfig

    with pytest.raises(ValueError, match="hem_notch_params"):
        WideSleeveBlockConfig(
            hem_notch_params=tuple((i / 3, 0.0) for i in range(3))  # 3 entries, needs 5
        )
