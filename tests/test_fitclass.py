"""Tests for fitclass.py — FitClass, EASE_FIELDS, range validation."""

import unittest

import pytest

from sewpat.fitclass import EASE_FIELDS, FitClass
from sewpat.units import CM


class TestFitClassDefaults(unittest.TestCase):
    """FitClass with pk=4, no overrides — all upper-bound defaults."""

    def setUp(self):
        self.fc = FitClass(pk=4)

    def test_pk_stored(self):
        """pk is stored correctly."""
        self.assertEqual(self.fc.pk, 4)

    def test_all_ease_fields_resolved(self):
        """All EASE_FIELDS return a positive float."""
        for ef in EASE_FIELDS:
            val = getattr(self.fc, ef)
            self.assertIsInstance(val, float, f"{ef} should be float")
            self.assertGreater(val, 0, f"{ef} should be positive")

    def test_bust_width_ease_derived(self):
        """bust_width_ease = 2 × (back + armscye_width + chest)."""
        expected = 2.0 * (
            self.fc.back_width_ease
            + self.fc.armscye_width_ease
            + self.fc.chest_width_ease
        )
        self.assertAlmostEqual(self.fc.bust_width_ease, expected)

    def test_range_returns_lo_hi(self):
        """range() returns a NamedTuple with lo <= hi."""
        r = self.fc.range("back_width_ease")
        self.assertLessEqual(r.lo, r.hi)

    def test_range_unknown_field_raises(self):
        """range() raises KeyError for an unknown field name."""
        with self.assertRaises(KeyError):
            self.fc.range("nonexistent_field")


class TestFitClassOverrides(unittest.TestCase):
    """FitClass with individual ease field overrides."""

    def test_override_within_range_accepted(self):
        """Override within [lo, hi] is accepted and returned."""
        fc = FitClass(pk=4)
        r = fc.range("back_width_ease")
        mid = (r.lo + r.hi) / 2
        fc2 = FitClass(pk=4, back_width_ease=mid)
        self.assertAlmostEqual(fc2.back_width_ease, mid)

    def test_override_below_range_raises(self):
        """Override below lo raises ValueError."""
        fc = FitClass(pk=4)
        r = fc.range("back_width_ease")
        with self.assertRaises(ValueError):
            FitClass(pk=4, back_width_ease=r.lo - 1.0 * CM)

    def test_override_above_range_raises(self):
        """Override above hi raises ValueError."""
        fc = FitClass(pk=4)
        r = fc.range("back_width_ease")
        with self.assertRaises(ValueError):
            FitClass(pk=4, back_width_ease=r.hi + 1.0 * CM)

    def test_all_fields_can_be_overridden(self):
        """Every EASE_FIELD can be set to its hi value without error."""
        fc_ref = FitClass(pk=4)
        kwargs = {ef: fc_ref.range(ef).hi for ef in EASE_FIELDS}
        fc2 = FitClass(pk=4, **kwargs)
        for ef in EASE_FIELDS:
            self.assertAlmostEqual(getattr(fc2, ef), fc_ref.range(ef).hi)


class TestFitClassValidation(unittest.TestCase):
    """FitClass constructor validation."""

    def test_pk_out_of_range_raises(self):
        """pk outside 0–12 raises ValueError."""
        with self.assertRaises(ValueError):
            FitClass(pk=13)
        with self.assertRaises(ValueError):
            FitClass(pk=-1)

    def test_unpopulated_pk_raises(self):
        """pk within 0–12 but not yet in table raises KeyError."""
        with self.assertRaises(KeyError):
            FitClass(pk=0)

    def test_resolve_uses_table_hi_when_no_override(self):
        """Without override the resolved value equals table hi."""
        fc = FitClass(pk=4)
        r = fc.range("waist_ease")
        self.assertAlmostEqual(fc.waist_ease, r.hi)

    def test_override_at_boundary_lo(self):
        """Override exactly at lo is accepted."""
        fc = FitClass(pk=4)
        r = fc.range("hip_ease")
        fc2 = FitClass(pk=4, hip_ease=r.lo)
        self.assertAlmostEqual(fc2.hip_ease, r.lo)

    def test_override_at_boundary_hi(self):
        """Override exactly at hi is accepted."""
        fc = FitClass(pk=4)
        r = fc.range("hip_ease")
        fc2 = FitClass(pk=4, hip_ease=r.hi)
        self.assertAlmostEqual(fc2.hip_ease, r.hi)


if __name__ == "__main__":
    unittest.main()

