"""Tests for person.py — Person, PersonalAdjustments, PersonAnalyser, BalancedPerson."""

import unittest

from sewpat.person import (
    BalanceAdjustments,
    BalancedPerson,
    Gender,
    Person,
    PersonalAdjustments,
    PersonAnalyser,
)
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------


class TestPerson(unittest.TestCase):
    """Tests for Person dataclass."""

    def test_defaults_are_none(self):
        """All measurement fields default to None."""
        p = Person()
        self.assertIsNone(p.bust)
        self.assertIsNone(p.waist)
        self.assertEqual(p.gender, Gender.female)

    def test_gender_values(self):
        """All Gender enum values can be used."""
        for g in (Gender.male, Gender.female, Gender.boy, Gender.girl, Gender.baby):
            p = Person(gender=g)
            self.assertEqual(p.gender, g)

    def test_person_with_measurements(self):
        """Person stores measurements in mm."""
        p = Person(bust=88 * CM, waist=70 * CM, hip=96 * CM)
        self.assertAlmostEqual(p.bust, 880.0)
        self.assertAlmostEqual(p.waist, 700.0)
        self.assertAlmostEqual(p.hip, 960.0)


# ---------------------------------------------------------------------------
# PersonalAdjustments
# ---------------------------------------------------------------------------


class TestPersonalAdjustments(unittest.TestCase):
    """Tests for PersonalAdjustments validation."""

    def test_defaults_are_valid(self):
        """Default values do not raise."""
        adj = PersonalAdjustments()
        self.assertAlmostEqual(adj.hip_offset, 2.0 * CM)
        self.assertAlmostEqual(adj.shoulder_drop, 1.5 * CM)

    def test_valid_extremes(self):
        """Boundary values at exactly lo and hi are accepted."""
        PersonalAdjustments(hip_offset=1.0 * CM, shoulder_drop=1.0 * CM)
        PersonalAdjustments(hip_offset=3.0 * CM, shoulder_drop=1.5 * CM)

    def test_hip_offset_too_low(self):
        """hip_offset below 1 cm raises ValueError."""
        with self.assertRaises(ValueError):
            PersonalAdjustments(hip_offset=0.5 * CM)

    def test_hip_offset_too_high(self):
        """hip_offset above 3 cm raises ValueError."""
        with self.assertRaises(ValueError):
            PersonalAdjustments(hip_offset=3.5 * CM)

    def test_shoulder_drop_too_low(self):
        """shoulder_drop below 1 cm raises ValueError."""
        with self.assertRaises(ValueError):
            PersonalAdjustments(shoulder_drop=0.5 * CM)

    def test_shoulder_drop_too_high(self):
        """shoulder_drop above 1.5 cm raises ValueError."""
        with self.assertRaises(ValueError):
            PersonalAdjustments(shoulder_drop=2.0 * CM)


# ---------------------------------------------------------------------------
# PersonAnalyser helper — a realistic Person fixture
# ---------------------------------------------------------------------------


def _make_person() -> Person:
    """Return a fully-specified Person in the 80–89 cm bust range."""
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
# PersonAnalyser
# ---------------------------------------------------------------------------


class TestPersonAnalyser(unittest.TestCase):
    """Tests for PersonAnalyser measurement derivation and balancing."""

    def test_derives_armscye_depth(self):
        """armscye_depth is derived from bust if not provided."""
        p = _make_person()
        p.armscye_depth = None
        analyser = PersonAnalyser(p)
        self.assertIsNotNone(analyser.person.armscye_depth)
        self.assertAlmostEqual(analyser.person.armscye_depth, 86 * CM / 10 + 11 * CM)

    def test_derives_armscye_width(self):
        """armscye_width is derived from bust if not provided."""
        p = _make_person()
        p.armscye_width = None
        analyser = PersonAnalyser(p)
        self.assertAlmostEqual(analyser.person.armscye_width, 86 * CM / 8 - 1.5 * CM)

    def test_derives_chest_width(self):
        """chest_width is derived from bust if not provided."""
        p = _make_person()
        p.chest_width = None
        analyser = PersonAnalyser(p)
        self.assertAlmostEqual(analyser.person.chest_width, 86 * CM / 4 - 4.0 * CM)

    def test_derives_back_width(self):
        """back_width is derived from bust if not provided."""
        p = _make_person()
        p.back_width = None
        analyser = PersonAnalyser(p)
        self.assertAlmostEqual(analyser.person.back_width, 86 * CM / 8 + 5.5 * CM)

    def test_keeps_explicit_measurements(self):
        """Explicitly provided measurements are not overwritten."""
        p = _make_person()
        custom_aw = 9.0 * CM
        p.armscye_width = custom_aw
        analyser = PersonAnalyser(p)
        self.assertAlmostEqual(analyser.person.armscye_width, custom_aw)

    def test_get_balanced_person_returns_balanced_person(self):
        """get_balanced_person() returns a BalancedPerson when balance is good."""
        p = _make_person()
        analyser = PersonAnalyser(p)
        bp = analyser.get_balanced_person()
        self.assertIsInstance(bp, BalancedPerson)

    def test_get_optimal_balance_outside_range(self):
        """NotImplementedError for bust outside supported range."""
        p = _make_person()
        p.bust = 100 * CM  # outside 80–89 cm range
        with self.assertRaises(NotImplementedError):
            PersonAnalyser(p)

    def test_balance_with_adjustments(self):
        """BalanceAdjustments are applied before balance check."""
        p = _make_person()
        adj = BalanceAdjustments(back_length=0.5 * CM)
        analyser = PersonAnalyser(p, balance_adjustments=adj)
        bp = analyser.get_balanced_person()
        self.assertIsInstance(bp, BalancedPerson)

    def test_imbalanced_person_raises(self):
        """ValueError when front_length - back_length > optimal_balance."""
        p = _make_person()
        p.front_length = p.back_length + 5.0 * CM  # way over 3.5 cm optimal
        with self.assertRaises(ValueError):
            PersonAnalyser(p)

    def test_armscye_depth_not_implemented_outside_range(self):
        """NotImplementedError for bust outside the 80–89 cm range for armscye_depth."""
        p = _make_person()
        p.bust = 100 * CM
        p.armscye_depth = None
        with self.assertRaises(NotImplementedError):
            PersonAnalyser(p)

    def test_armscye_width_not_implemented_outside_range(self):
        """NotImplementedError for armscye_width outside supported bust range."""
        p = _make_person()
        p.bust = 100 * CM
        p.armscye_depth = 21 * CM  # provide to get past armscye_depth check
        p.armscye_width = None
        with self.assertRaises(NotImplementedError):
            PersonAnalyser(p)

    def test_does_not_mutate_original_person(self):
        """PersonAnalyser works on a copy and does not mutate the original."""
        p = _make_person()
        # Remove derived measurements from original to force derivation
        p.armscye_depth = None
        p.armscye_width = None
        p.chest_width = None
        p.back_width = None

        # Run analyser
        analyser = PersonAnalyser(p)

        # Original person should still have None values
        self.assertIsNone(p.armscye_depth)
        self.assertIsNone(p.armscye_width)
        self.assertIsNone(p.chest_width)
        self.assertIsNone(p.back_width)

        # Analyser's copy should have derived values
        self.assertIsNotNone(analyser.person.armscye_depth)
        self.assertIsNotNone(analyser.person.armscye_width)
        self.assertIsNotNone(analyser.person.chest_width)
        self.assertIsNotNone(analyser.person.back_width)


# ---------------------------------------------------------------------------
# BalancedPerson
# ---------------------------------------------------------------------------


class TestBalancedPerson(unittest.TestCase):
    """Tests for BalancedPerson proxy."""

    def test_person_property(self):
        """The .person property returns the wrapped Person."""
        p = _make_person()
        bp = BalancedPerson(p)
        self.assertIs(bp.person, p)

    def test_repr(self):
        """repr() delegates to the wrapped person."""
        p = _make_person()
        bp = BalancedPerson(p)
        self.assertIn("BalancedPerson", repr(bp))

    def test_getattr_delegation(self):
        """Attribute access is delegated to the wrapped Person."""
        p = _make_person()
        bp = BalancedPerson(p)
        self.assertAlmostEqual(bp.bust, p.bust)  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
