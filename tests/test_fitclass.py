"""Tests for fitclass.py — FitClass, EASE_FIELDS, range validation."""

import pytest

from sewpat.fitclass import EASE_FIELDS, FitClass
from sewpat.units import CM

# ---------------------------------------------------------------------------
# FitClass defaults (pk=4, no overrides)
# ---------------------------------------------------------------------------


def test_fitclass_pk_stored(standard_fitclass: FitClass):
    """pk is stored correctly."""
    assert standard_fitclass.pk == 4


@pytest.mark.parametrize("ease_field", EASE_FIELDS)
def test_fitclass_all_ease_fields_resolved(standard_fitclass: FitClass, ease_field: str):
    """All EASE_FIELDS return a positive float."""
    val = getattr(standard_fitclass, ease_field)
    assert isinstance(val, float), f"{ease_field} should be float"
    assert val > 0, f"{ease_field} should be positive"


def test_fitclass_bust_width_ease_derived(standard_fitclass: FitClass):
    """bust_width_ease = 2 × (back + armscye_width + chest)."""
    expected = 2.0 * (
        standard_fitclass.back_width_ease
        + standard_fitclass.armscye_width_ease
        + standard_fitclass.chest_width_ease
    )
    assert standard_fitclass.bust_width_ease == pytest.approx(expected)


def test_fitclass_range_returns_lo_hi(standard_fitclass: FitClass):
    """range() returns a NamedTuple with lo <= hi."""
    r = standard_fitclass.range("back_width_ease")
    assert r.lo <= r.hi


def test_fitclass_range_unknown_field_raises(standard_fitclass: FitClass):
    """range() raises KeyError for an unknown field name."""
    with pytest.raises(KeyError):
        standard_fitclass.range("nonexistent_field")


# ---------------------------------------------------------------------------
# FitClass overrides
# ---------------------------------------------------------------------------


def test_fitclass_override_within_range_accepted(standard_fitclass: FitClass):
    """Override within [lo, hi] is accepted and returned."""
    r = standard_fitclass.range("back_width_ease")
    mid = (r.lo + r.hi) / 2
    fc2 = FitClass(pk=4, back_width_ease=mid)
    assert fc2.back_width_ease == pytest.approx(mid)


def test_fitclass_override_below_range_raises(standard_fitclass: FitClass):
    """Override below lo raises ValueError."""
    r = standard_fitclass.range("back_width_ease")
    with pytest.raises(ValueError):
        FitClass(pk=4, back_width_ease=r.lo - 1.0 * CM)


def test_fitclass_override_above_range_raises(standard_fitclass: FitClass):
    """Override above hi raises ValueError."""
    r = standard_fitclass.range("back_width_ease")
    with pytest.raises(ValueError):
        FitClass(pk=4, back_width_ease=r.hi + 1.0 * CM)


def test_fitclass_all_fields_can_be_overridden(standard_fitclass: FitClass):
    """Every EASE_FIELD can be set to its hi value without error."""
    kwargs = {ef: standard_fitclass.range(ef).hi for ef in EASE_FIELDS}
    fc2 = FitClass(pk=4, **kwargs)
    for ef in EASE_FIELDS:
        assert getattr(fc2, ef) == pytest.approx(standard_fitclass.range(ef).hi)


# ---------------------------------------------------------------------------
# FitClass validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("invalid_pk", [13, -1])
def test_fitclass_pk_out_of_range_raises(invalid_pk: int):
    """pk outside 0–12 raises ValueError."""
    with pytest.raises(ValueError):
        FitClass(pk=invalid_pk)


def test_fitclass_unpopulated_pk_raises():
    """pk within 0–12 but not yet in table raises KeyError."""
    with pytest.raises(KeyError):
        FitClass(pk=0)


def test_fitclass_resolve_uses_table_hi_when_no_override(standard_fitclass: FitClass):
    """Without override the resolved value equals table hi."""
    r = standard_fitclass.range("waist_ease")
    assert standard_fitclass.waist_ease == pytest.approx(r.hi)


def test_fitclass_override_at_boundary_lo(standard_fitclass: FitClass):
    """Override exactly at lo is accepted."""
    r = standard_fitclass.range("hip_ease")
    fc2 = FitClass(pk=4, hip_ease=r.lo)
    assert fc2.hip_ease == pytest.approx(r.lo)


def test_fitclass_override_at_boundary_hi(standard_fitclass: FitClass):
    """Override exactly at hi is accepted."""
    r = standard_fitclass.range("hip_ease")
    fc2 = FitClass(pk=4, hip_ease=r.hi)
    assert fc2.hip_ease == pytest.approx(r.hi)
