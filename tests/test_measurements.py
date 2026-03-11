"""Tests for measurements.py — TrouserMeasurements, BlouseMeasurements, GarmentConfig,
make_measurements_trouser, make_top_measurements.
"""

import pytest

from sewpat.fitclass import FitClass
from sewpat.measurements import (
    BlouseMeasurements,
    GarmentConfig,
    TrouserMeasurements,
    make_measurements_trouser,
    make_top_measurements,
)
from sewpat.person import (
    BalanceAdjustments,
    Gender,
    Person,
)
from sewpat.units import CM

# ---------------------------------------------------------------------------
# TrouserMeasurements
# ---------------------------------------------------------------------------


def test_trouser_measurements_front_trouser_width_derived_female():
    """front_trouser_width defaults to 0.25 * hip_width (female with sTaH)."""
    meas = TrouserMeasurements(
        waist=70 * CM,
        hip=96 * CM,
        body_rise=27 * CM,
        waist_width=72 * CM,
        hip_width=98 * CM,
        sTaH=107 * CM,
        inseam=80 * CM,
    )
    assert meas.front_trouser_width == pytest.approx(0.25 * 98 * CM)


def test_trouser_measurements_front_trouser_width_explicit():
    """Explicit front_trouser_width is kept as-is."""
    meas = TrouserMeasurements(
        waist=70 * CM,
        hip=96 * CM,
        body_rise=27 * CM,
        waist_width=72 * CM,
        hip_width=98 * CM,
        sTaH=107 * CM,
        inseam=80 * CM,
        front_trouser_width=25 * CM,
    )
    assert meas.front_trouser_width == pytest.approx(25 * CM)


def test_trouser_measurements_knee_height_derived_for_boy():
    """knee_height is derived as 0.5 * inseam for boy."""
    meas = TrouserMeasurements(
        waist=60 * CM,
        hip=80 * CM,
        body_rise=22 * CM,
        waist_width=62 * CM,
        hip_width=82 * CM,
        inseam=60 * CM,
        gender=Gender.boy,
    )
    assert meas.knee_height == pytest.approx(0.5 * 60 * CM)


def test_trouser_measurements_knee_height_derived_for_girl():
    """knee_height is derived as 0.5 * inseam for girl."""
    meas = TrouserMeasurements(
        waist=60 * CM,
        hip=80 * CM,
        body_rise=22 * CM,
        waist_width=62 * CM,
        hip_width=82 * CM,
        inseam=60 * CM,
        gender=Gender.girl,
    )
    assert meas.knee_height == pytest.approx(0.5 * 60 * CM)


def test_trouser_measurements_knee_height_derived_for_female():
    """knee_height for female = 0.5 * inseam - inseam/10."""
    inseam = 80 * CM
    sTaH = 107 * CM
    meas = TrouserMeasurements(
        waist=70 * CM,
        hip=96 * CM,
        body_rise=27 * CM,
        waist_width=72 * CM,
        hip_width=98 * CM,
        sTaH=sTaH,
        inseam=inseam,
    )
    assert meas.knee_height == pytest.approx(0.5 * inseam - inseam / 10)


# ---------------------------------------------------------------------------
# BlouseMeasurements
# ---------------------------------------------------------------------------


def test_blouse_measurements_valid_construction(standard_blouse_measurements: BlouseMeasurements):
    """Valid measurements construct without error."""
    assert standard_blouse_measurements is not None


def test_blouse_measurements_invalid_bust_width_raises(
    standard_blouse_measurements: BlouseMeasurements,
):
    """bust_width inconsistent with components raises ValueError."""
    meas = standard_blouse_measurements
    with pytest.raises(ValueError):
        BlouseMeasurements(
            bust=meas.bust,
            waist=meas.waist,
            hip=meas.hip,
            hip_depth=meas.hip_depth,
            bust_depth=meas.bust_depth,
            neck_size=meas.neck_size,
            bust_span=meas.bust_span,
            shoulder_width=meas.shoulder_width,
            back_length=meas.back_length,
            front_length=meas.front_length,
            armscye_depth=meas.armscye_depth,
            bust_width=meas.bust_width + 5 * CM,  # deliberately wrong
            waist_width=meas.waist_width,
            hip_width=meas.hip_width,
            back_width=meas.back_width,
            armscye_width=meas.armscye_width,
            chest_width=meas.chest_width,
        )


# ---------------------------------------------------------------------------
# GarmentConfig
# ---------------------------------------------------------------------------


def test_garment_config_defaults_valid():
    """Default GarmentConfig constructs without error."""
    cfg = GarmentConfig(length=70 * CM)
    assert cfg is not None


def test_garment_config_armscye_fit_out_of_range_raises():
    """armscye_fit outside [0, 1 cm] raises ValueError."""
    with pytest.raises(ValueError):
        GarmentConfig(length=70 * CM, armscye_fit=2.0 * CM)


def test_garment_config_waist_dart_back_tip_out_of_range_raises():
    """waist_dart_back_tip outside [13, 16 cm] raises ValueError."""
    with pytest.raises(ValueError):
        GarmentConfig(length=70 * CM, waist_dart_back_tip=17 * CM)


def test_garment_config_armscye_fit_at_boundary():
    """armscye_fit at exactly 0 and 1 cm are valid."""
    GarmentConfig(length=70 * CM, armscye_fit=0.0)
    GarmentConfig(length=70 * CM, armscye_fit=1.0 * CM)


# ---------------------------------------------------------------------------
# make_measurements_trouser
# ---------------------------------------------------------------------------


@pytest.fixture
def boy_person():
    """Boy person for trouser tests."""
    return Person(
        bust=60 * CM,
        waist=58 * CM,
        hip=70 * CM,
        hip_depth=16 * CM,
        body_rise=22 * CM,
        inseam=60 * CM,
        height=130 * CM,
        gender=Gender.boy,
    )


@pytest.fixture
def trouser_ease():
    """Default trouser ease."""
    from sewpat.measurements import TrouserEase

    return TrouserEase()


def test_make_measurements_trouser_returns_trouser_measurements(boy_person: Person, trouser_ease):
    """Returns a TrouserMeasurements instance."""
    meas = make_measurements_trouser(boy_person, trouser_ease)
    assert isinstance(meas, TrouserMeasurements)


def test_make_measurements_trouser_waist_width_includes_ease(boy_person: Person, trouser_ease):
    """waist_width = waist + waist_ease."""
    meas = make_measurements_trouser(boy_person, trouser_ease)
    assert meas.waist_width == pytest.approx(boy_person.waist + trouser_ease.waist_ease)


def test_make_measurements_trouser_hip_width_includes_ease(boy_person: Person, trouser_ease):
    """hip_width = hip + hip_ease."""
    meas = make_measurements_trouser(boy_person, trouser_ease)
    assert meas.hip_width == pytest.approx(boy_person.hip + trouser_ease.hip_ease)


def test_make_measurements_trouser_with_balance_adjustments(boy_person: Person, trouser_ease):
    """BalanceAdjustments are accepted without raising."""
    bal = BalanceAdjustments(back_length=1.0 * CM)
    meas = make_measurements_trouser(boy_person, trouser_ease, balance=bal)
    assert isinstance(meas, TrouserMeasurements)


# ---------------------------------------------------------------------------
# make_top_measurements
# ---------------------------------------------------------------------------


def test_make_top_measurements_returns_blouse_measurements(
    balanced_person, standard_fitclass: FitClass
):
    """Returns a BlouseMeasurements instance."""
    meas = make_top_measurements(balanced_person, standard_fitclass)
    assert isinstance(meas, BlouseMeasurements)


def test_make_top_measurements_bust_width_ease_applied(
    balanced_person, standard_fitclass: FitClass
):
    """bust_width is augmented by bust_width_ease."""
    meas = make_top_measurements(balanced_person, standard_fitclass)
    expected_bust_width = balanced_person.person.bust + standard_fitclass.bust_width_ease
    assert meas.bust_width == pytest.approx(expected_bust_width, abs=1e-4)


def test_make_top_measurements_waist_width_ease_applied(
    balanced_person, standard_fitclass: FitClass
):
    """waist_width = waist + waist_ease."""
    meas = make_top_measurements(balanced_person, standard_fitclass)
    assert meas.waist_width == pytest.approx(
        balanced_person.person.waist + standard_fitclass.waist_ease,
        abs=1e-4,
    )


def test_make_top_measurements_hip_width_ease_applied(balanced_person, standard_fitclass: FitClass):
    """hip_width = hip + hip_ease."""
    meas = make_top_measurements(balanced_person, standard_fitclass)
    assert meas.hip_width == pytest.approx(
        balanced_person.person.hip + standard_fitclass.hip_ease,
        abs=1e-4,
    )
