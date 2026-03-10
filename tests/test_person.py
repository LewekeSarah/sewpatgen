"""Tests for person.py — Person, PersonalAdjustments, PersonAnalyser, BalancedPerson."""

import pytest

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


def test_person_defaults_are_none():
    """All measurement fields default to None."""
    p = Person()
    assert p.bust is None
    assert p.waist is None
    assert p.gender == Gender.female


@pytest.mark.parametrize(
    "gender",
    [Gender.male, Gender.female, Gender.boy, Gender.girl, Gender.baby],
)
def test_person_gender_values(gender: Gender):
    """All Gender enum values can be used."""
    p = Person(gender=gender)
    assert p.gender == gender


def test_person_with_measurements():
    """Person stores measurements in mm."""
    p = Person(bust=88 * CM, waist=70 * CM, hip=96 * CM)
    assert p.bust == pytest.approx(880.0)
    assert p.waist == pytest.approx(700.0)
    assert p.hip == pytest.approx(960.0)


# ---------------------------------------------------------------------------
# PersonalAdjustments
# ---------------------------------------------------------------------------


def test_personal_adjustments_defaults_are_valid():
    """Default values do not raise."""
    adj = PersonalAdjustments()
    assert adj.hip_offset == pytest.approx(2.0 * CM)
    assert adj.shoulder_drop == pytest.approx(1.5 * CM)


def test_personal_adjustments_valid_extremes():
    """Boundary values at exactly lo and hi are accepted."""
    PersonalAdjustments(hip_offset=1.0 * CM, shoulder_drop=1.0 * CM)
    PersonalAdjustments(hip_offset=3.0 * CM, shoulder_drop=1.5 * CM)


def test_personal_adjustments_hip_offset_too_low():
    """hip_offset below 1 cm raises ValueError."""
    with pytest.raises(ValueError):
        PersonalAdjustments(hip_offset=0.5 * CM)


def test_personal_adjustments_hip_offset_too_high():
    """hip_offset above 3 cm raises ValueError."""
    with pytest.raises(ValueError):
        PersonalAdjustments(hip_offset=3.5 * CM)


def test_personal_adjustments_shoulder_drop_too_low():
    """shoulder_drop below 1 cm raises ValueError."""
    with pytest.raises(ValueError):
        PersonalAdjustments(shoulder_drop=0.5 * CM)


def test_personal_adjustments_shoulder_drop_too_high():
    """shoulder_drop above 1.5 cm raises ValueError."""
    with pytest.raises(ValueError):
        PersonalAdjustments(shoulder_drop=2.0 * CM)


# ---------------------------------------------------------------------------
# PersonAnalyser
# ---------------------------------------------------------------------------


def test_person_analyser_derives_armscye_depth(standard_person: Person):
    """armscye_depth is derived from bust if not provided."""
    standard_person.armscye_depth = None
    analyser = PersonAnalyser(standard_person)
    assert analyser.person.armscye_depth is not None
    assert analyser.person.armscye_depth == pytest.approx(86 * CM / 10 + 11 * CM)


def test_person_analyser_derives_armscye_width(standard_person: Person):
    """armscye_width is derived from bust if not provided."""
    standard_person.armscye_width = None
    analyser = PersonAnalyser(standard_person)
    assert analyser.person.armscye_width == pytest.approx(86 * CM / 8 - 1.5 * CM)


def test_person_analyser_derives_chest_width(standard_person: Person):
    """chest_width is derived from bust if not provided."""
    standard_person.chest_width = None
    analyser = PersonAnalyser(standard_person)
    assert analyser.person.chest_width == pytest.approx(86 * CM / 4 - 4.0 * CM)


def test_person_analyser_derives_back_width(standard_person: Person):
    """back_width is derived from bust if not provided."""
    standard_person.back_width = None
    analyser = PersonAnalyser(standard_person)
    assert analyser.person.back_width == pytest.approx(86 * CM / 8 + 5.5 * CM)


def test_person_analyser_keeps_explicit_measurements(standard_person: Person):
    """Explicitly provided measurements are not overwritten."""
    custom_aw = 9.0 * CM
    standard_person.armscye_width = custom_aw
    analyser = PersonAnalyser(standard_person)
    assert analyser.person.armscye_width == pytest.approx(custom_aw)


def test_person_analyser_get_balanced_person_returns_balanced_person(standard_person: Person):
    """get_balanced_person() returns a BalancedPerson when balance is good."""
    analyser = PersonAnalyser(standard_person)
    bp = analyser.get_balanced_person()
    assert isinstance(bp, BalancedPerson)


def test_person_analyser_get_optimal_balance_outside_range(standard_person: Person):
    """NotImplementedError for bust outside supported range."""
    standard_person.bust = 100 * CM  # outside 80–89 cm range
    with pytest.raises(NotImplementedError):
        PersonAnalyser(standard_person)


def test_person_analyser_balance_with_adjustments(standard_person: Person):
    """BalanceAdjustments are applied before balance check."""
    adj = BalanceAdjustments(back_length=0.5 * CM)
    analyser = PersonAnalyser(standard_person, balance_adjustments=adj)
    bp = analyser.get_balanced_person()
    assert isinstance(bp, BalancedPerson)


def test_person_analyser_imbalanced_person_raises(standard_person: Person):
    """ValueError when front_length - back_length > optimal_balance."""
    standard_person.front_length = standard_person.back_length + 5.0 * CM  # way over 3.5 cm optimal
    with pytest.raises(ValueError):
        PersonAnalyser(standard_person)


def test_person_analyser_armscye_depth_not_implemented_outside_range(standard_person: Person):
    """NotImplementedError for bust outside the 80–89 cm range for armscye_depth."""
    standard_person.bust = 100 * CM
    standard_person.armscye_depth = None
    with pytest.raises(NotImplementedError):
        PersonAnalyser(standard_person)


def test_person_analyser_armscye_width_not_implemented_outside_range(standard_person: Person):
    """NotImplementedError for armscye_width outside supported bust range."""
    standard_person.bust = 100 * CM
    standard_person.armscye_depth = 21 * CM  # provide to get past armscye_depth check
    standard_person.armscye_width = None
    with pytest.raises(NotImplementedError):
        PersonAnalyser(standard_person)


def test_person_analyser_does_not_mutate_original_person(standard_person: Person):
    """PersonAnalyser works on a copy and does not mutate the original."""
    # Remove derived measurements from original to force derivation
    standard_person.armscye_depth = None
    standard_person.armscye_width = None
    standard_person.chest_width = None
    standard_person.back_width = None

    # Run analyser
    analyser = PersonAnalyser(standard_person)

    # Original person should still have None values
    assert standard_person.armscye_depth is None
    assert standard_person.armscye_width is None
    assert standard_person.chest_width is None
    assert standard_person.back_width is None

    # Analyser's copy should have derived values
    assert analyser.person.armscye_depth is not None
    assert analyser.person.armscye_width is not None
    assert analyser.person.chest_width is not None
    assert analyser.person.back_width is not None


# ---------------------------------------------------------------------------
# BalancedPerson
# ---------------------------------------------------------------------------


def test_balanced_person_person_property(standard_person: Person):
    """The .person property returns the wrapped Person."""
    bp = BalancedPerson(standard_person)
    assert bp.person is standard_person


def test_balanced_person_repr(standard_person: Person):
    """repr() delegates to the wrapped person."""
    bp = BalancedPerson(standard_person)
    assert "BalancedPerson" in repr(bp)


def test_balanced_person_getattr_delegation(standard_person: Person):
    """Attribute access is delegated to the wrapped Person."""
    bp = BalancedPerson(standard_person)
    assert bp.bust == pytest.approx(standard_person.bust)  # type: ignore[attr-defined]
