"""Tests for measurements.py — TrouserMeasurements, BlouseMeasurements, GarmentConfig,
make_measurements_trouser, make_top_measurements.
"""

import unittest

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
    BalancedPerson,
    Gender,
    Person,
    PersonAnalyser,
    PersonalAdjustments,
)
from sewpat.units import CM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_blouse_meas() -> BlouseMeasurements:
    bust = 86 * CM
    bw = bust / 8 + 5.5 * CM
    aw = bust / 8 - 1.5 * CM
    cw = bust / 4 - 4.0 * CM
    bust_width = 2 * (bw + aw + cw)
    return BlouseMeasurements(
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


def _make_person() -> Person:
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


# ---------------------------------------------------------------------------
# TrouserMeasurements
# ---------------------------------------------------------------------------

class TestTrouserMeasurements(unittest.TestCase):
    """Tests for TrouserMeasurements.__post_init__ derivations."""

    def test_front_trouser_width_derived_female(self):
        """front_trouser_width defaults to 0.25 * hip_width (female with sTaH)."""
        meas = TrouserMeasurements(
            waist=70 * CM, hip=96 * CM, body_rise=27 * CM,
            waist_width=72 * CM, hip_width=98 * CM,
            sTaH=107 * CM, inseam=80 * CM,
        )
        self.assertAlmostEqual(meas.front_trouser_width, 0.25 * 98 * CM)

    def test_front_trouser_width_explicit(self):
        """Explicit front_trouser_width is kept as-is."""
        meas = TrouserMeasurements(
            waist=70 * CM, hip=96 * CM, body_rise=27 * CM,
            waist_width=72 * CM, hip_width=98 * CM,
            sTaH=107 * CM, inseam=80 * CM,
            front_trouser_width=25 * CM,
        )
        self.assertAlmostEqual(meas.front_trouser_width, 25 * CM)

    def test_knee_height_derived_for_boy(self):
        """knee_height is derived as 0.5 * inseam for boy."""
        meas = TrouserMeasurements(
            waist=60 * CM, hip=80 * CM, body_rise=22 * CM,
            waist_width=62 * CM, hip_width=82 * CM,
            inseam=60 * CM, gender=Gender.boy,
        )
        self.assertAlmostEqual(meas.knee_height, 0.5 * 60 * CM)

    def test_knee_height_derived_for_girl(self):
        """knee_height is derived as 0.5 * inseam for girl."""
        meas = TrouserMeasurements(
            waist=60 * CM, hip=80 * CM, body_rise=22 * CM,
            waist_width=62 * CM, hip_width=82 * CM,
            inseam=60 * CM, gender=Gender.girl,
        )
        self.assertAlmostEqual(meas.knee_height, 0.5 * 60 * CM)

    def test_knee_height_derived_for_female(self):
        """knee_height for female = 0.5 * inseam - inseam/10."""
        inseam = 80 * CM
        sTaH = 107 * CM
        meas = TrouserMeasurements(
            waist=70 * CM, hip=96 * CM, body_rise=27 * CM,
            waist_width=72 * CM, hip_width=98 * CM,
            sTaH=sTaH, inseam=inseam,
        )
        self.assertAlmostEqual(meas.knee_height, 0.5 * inseam - inseam / 10)


# ---------------------------------------------------------------------------
# BlouseMeasurements
# ---------------------------------------------------------------------------

class TestBlouseMeasurements(unittest.TestCase):
    """Tests for BlouseMeasurements validation."""

    def test_valid_construction(self):
        """Valid measurements construct without error."""
        meas = _make_blouse_meas()
        self.assertIsNotNone(meas)

    def test_invalid_bust_width_raises(self):
        """bust_width inconsistent with components raises ValueError."""
        meas = _make_blouse_meas()
        with self.assertRaises(ValueError):
            BlouseMeasurements(
                bust=meas.bust, waist=meas.waist, hip=meas.hip,
                hip_depth=meas.hip_depth, bust_depth=meas.bust_depth,
                neck_size=meas.neck_size, bust_span=meas.bust_span,
                shoulder_width=meas.shoulder_width, back_length=meas.back_length,
                front_length=meas.front_length, armscye_depth=meas.armscye_depth,
                bust_width=meas.bust_width + 5 * CM,  # deliberately wrong
                waist_width=meas.waist_width, hip_width=meas.hip_width,
                back_width=meas.back_width, armscye_width=meas.armscye_width,
                chest_width=meas.chest_width,
            )


# ---------------------------------------------------------------------------
# GarmentConfig
# ---------------------------------------------------------------------------

class TestGarmentConfig(unittest.TestCase):
    """Tests for GarmentConfig validation."""

    def test_defaults_valid(self):
        """Default GarmentConfig constructs without error."""
        cfg = GarmentConfig(length=70 * CM)
        self.assertIsNotNone(cfg)

    def test_armscye_fit_out_of_range_raises(self):
        """armscye_fit outside [0, 1 cm] raises ValueError."""
        with self.assertRaises(ValueError):
            GarmentConfig(length=70 * CM, armscye_fit=2.0 * CM)

    def test_waist_dart_back_tip_out_of_range_raises(self):
        """waist_dart_back_tip outside [13, 16 cm] raises ValueError."""
        with self.assertRaises(ValueError):
            GarmentConfig(length=70 * CM, waist_dart_back_tip=17 * CM)

    def test_armscye_fit_at_boundary(self):
        """armscye_fit at exactly 0 and 1 cm are valid."""
        GarmentConfig(length=70 * CM, armscye_fit=0.0)
        GarmentConfig(length=70 * CM, armscye_fit=1.0 * CM)


# ---------------------------------------------------------------------------
# make_measurements_trouser
# ---------------------------------------------------------------------------

class TestMakeMeasurementsTrouser(unittest.TestCase):
    """Tests for make_measurements_trouser factory."""

    def setUp(self):
        from sewpat.measurements import TrouserEase
        # Use boy gender: inseam is provided directly, no sTaH needed
        self.person = Person(
            bust=60 * CM, waist=58 * CM, hip=70 * CM, hip_depth=16 * CM,
            body_rise=22 * CM, inseam=60 * CM, height=130 * CM,
            gender=Gender.boy,
        )
        self.ease = TrouserEase()

    def test_returns_trouser_measurements(self):
        """Returns a TrouserMeasurements instance."""
        meas = make_measurements_trouser(self.person, self.ease)
        self.assertIsInstance(meas, TrouserMeasurements)

    def test_waist_width_includes_ease(self):
        """waist_width = waist + waist_ease."""
        meas = make_measurements_trouser(self.person, self.ease)
        self.assertAlmostEqual(
            meas.waist_width, self.person.waist + self.ease.waist_ease
        )

    def test_hip_width_includes_ease(self):
        """hip_width = hip + hip_ease."""
        meas = make_measurements_trouser(self.person, self.ease)
        self.assertAlmostEqual(
            meas.hip_width, self.person.hip + self.ease.hip_ease
        )

    def test_with_balance_adjustments(self):
        """BalanceAdjustments are accepted without raising."""
        bal = BalanceAdjustments(back_length=1.0 * CM)
        meas = make_measurements_trouser(self.person, self.ease, balance=bal)
        self.assertIsInstance(meas, TrouserMeasurements)


# ---------------------------------------------------------------------------
# make_top_measurements
# ---------------------------------------------------------------------------

class TestMakeTopMeasurements(unittest.TestCase):
    """Tests for make_top_measurements factory."""

    def setUp(self):
        # Person without trouser-specific fields (body_rise, inseam)
        # that BlouseMeasurements doesn't accept
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
        analyser = PersonAnalyser(p)
        self.balanced = analyser.get_balanced_person()
        self.fc = FitClass(pk=4)

    def test_returns_blouse_measurements(self):
        """Returns a BlouseMeasurements instance."""
        meas = make_top_measurements(self.balanced, self.fc)
        self.assertIsInstance(meas, BlouseMeasurements)

    def test_bust_width_ease_applied(self):
        """bust_width is augmented by bust_width_ease."""
        meas = make_top_measurements(self.balanced, self.fc)
        expected_bust_width = self.balanced.person.bust + self.fc.bust_width_ease
        self.assertAlmostEqual(meas.bust_width, expected_bust_width, places=4)

    def test_waist_width_ease_applied(self):
        """waist_width = waist + waist_ease."""
        meas = make_top_measurements(self.balanced, self.fc)
        self.assertAlmostEqual(
            meas.waist_width,
            self.balanced.person.waist + self.fc.waist_ease,
            places=4,
        )

    def test_hip_width_ease_applied(self):
        """hip_width = hip + hip_ease."""
        meas = make_top_measurements(self.balanced, self.fc)
        self.assertAlmostEqual(
            meas.hip_width,
            self.balanced.person.hip + self.fc.hip_ease,
            places=4,
        )


if __name__ == "__main__":
    unittest.main()








