"""Tests for Pattern.validate_seam_pairs — cross-part seam length validation.

Covers:
  - Basic unit-test cases using minimal hand-crafted PatternParts with known
    geometry (no external dependencies).
  - Integration test using a real TopBlock (shared conftest fixtures).
  - PatternPart objects and GarmentPart enum values both accepted as part refs.
  - Error paths, warning behaviour, SeamValidationResult.__str__.
"""

import warnings

import pytest

from sewpat.blocks import BlockConfig, TopBlock
from sewpat.fitclass import FitClass
from sewpat.geometry import Point, Segment
from sewpat.grids import GridConfig, TopGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import GarmentPart, Pattern, PatternPart, SeamPairResult, SeamValidationResult
from sewpat.units import CM

from .conftest import _make_side_part, _simple_pattern

# ---------------------------------------------------------------------------
# Local helpers — minimal parts with known, exact geometry
# ---------------------------------------------------------------------------
# _make_side_part and _simple_pattern live in conftest.py so they are
# available to any future test file in this package without duplication.


# ---------------------------------------------------------------------------
# Part references: PatternPart objects and GarmentPart enum values
# ---------------------------------------------------------------------------


def test_accepts_pattern_part_objects():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    result = pat.validate_seam_pairs([(back, "side", front, "side")])
    assert result.all_ok


def test_accepts_garment_part_enum_values():
    """GarmentPart enum values (strings) are resolved via get_part."""

    class Part(GarmentPart):
        BACK = "Back"
        FRONT = "Front"

    pat = _simple_pattern(100.0, 100.0)
    result = pat.validate_seam_pairs([(Part.BACK, "side", Part.FRONT, "side")])
    assert result.all_ok


def test_accepts_mixed_part_object_and_garment_part():
    """Mixing a PatternPart object with a GarmentPart string is fine."""

    class Part(GarmentPart):
        FRONT = "Front"

    pat = _simple_pattern(100.0, 100.0)
    back = pat.parts[0]
    result = pat.validate_seam_pairs([(back, "side", Part.FRONT, "side")])
    assert result.all_ok


def test_garment_part_string_not_in_pattern_raises_key_error():
    pat = _simple_pattern(100.0, 100.0)
    front = pat.parts[1]
    with pytest.raises(KeyError, match="NonExistent"):
        pat.validate_seam_pairs([("NonExistent", "side", front, "side")])


# ---------------------------------------------------------------------------
# Return-type shape
# ---------------------------------------------------------------------------


def test_returns_seam_validation_result():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    assert isinstance(
        pat.validate_seam_pairs([(back, "side", front, "side")]),
        SeamValidationResult,
    )


def test_result_has_one_entry_per_pair():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    result = pat.validate_seam_pairs(
        [
            (back, "side", front, "side"),
            (back, "hem", front, "hem"),
        ]
    )
    assert len(result.pairs) == 2


def test_each_entry_is_seam_pair_result():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    result = pat.validate_seam_pairs([(back, "side", front, "side")])
    assert isinstance(result.pairs[0], SeamPairResult)


# ---------------------------------------------------------------------------
# Length calculation and delta
# ---------------------------------------------------------------------------


def test_identical_seams_ok():
    pat = _simple_pattern(150.0, 150.0)
    back, front = pat.parts[0], pat.parts[1]
    result = pat.validate_seam_pairs([(back, "side", front, "side")])
    assert result.all_ok and result.pairs[0].ok


def test_identical_seams_delta_zero():
    pat = _simple_pattern(150.0, 150.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side")]).pairs[0]
    assert abs(r.delta_mm) < 1e-9


def test_lengths_recorded_correctly():
    pat = _simple_pattern(120.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side")], warn=False).pairs[0]
    assert abs(r.length_a - 120.0) < 1e-9
    assert abs(r.length_b - 100.0) < 1e-9


def test_delta_is_a_minus_b():
    pat = _simple_pattern(130.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side")], warn=False).pairs[0]
    assert abs(r.delta_mm - 30.0) < 1e-9


def test_negative_delta_when_b_longer():
    pat = _simple_pattern(80.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side")], warn=False).pairs[0]
    assert r.delta_mm < 0


# ---------------------------------------------------------------------------
# Tolerance
# ---------------------------------------------------------------------------


def test_within_default_tolerance_ok():
    pat = _simple_pattern(100.0, 101.9)
    back, front = pat.parts[0], pat.parts[1]
    assert pat.validate_seam_pairs([(back, "side", front, "side")]).all_ok


def test_at_exact_tolerance_ok():
    pat = _simple_pattern(100.0, 102.0)
    back, front = pat.parts[0], pat.parts[1]
    assert pat.validate_seam_pairs([(back, "side", front, "side")]).all_ok


def test_exceeds_default_tolerance_not_ok():
    pat = _simple_pattern(100.0, 102.1)
    back, front = pat.parts[0], pat.parts[1]
    result = pat.validate_seam_pairs([(back, "side", front, "side")], warn=False)
    assert not result.all_ok and not result.pairs[0].ok


def test_custom_tolerance_honoured():
    pat = _simple_pattern(100.0, 105.0)
    back, front = pat.parts[0], pat.parts[1]
    assert pat.validate_seam_pairs([(back, "side", front, "side")], tolerance_mm=6.0).all_ok


def test_tolerance_mm_stored_on_result():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    result = pat.validate_seam_pairs([(back, "side", front, "side")], tolerance_mm=5.0)
    assert result.tolerance_mm == 5.0


def test_per_pair_tolerance_overrides_global():
    """A 5th tuple element overrides the global tolerance_mm for that pair."""
    pat = _simple_pattern(100.0, 106.0)  # delta = 6 mm
    back, front = pat.parts[0], pat.parts[1]
    # Global 2 mm would fail; per-pair 8 mm should pass
    result = pat.validate_seam_pairs(
        [(back, "side", front, "side", 8.0)], tolerance_mm=2.0, warn=False
    )
    assert result.all_ok
    assert result.pairs[0].tolerance_mm == 8.0


def test_per_pair_tolerance_stored_on_pair_result():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side", 5.0)]).pairs[0]
    assert r.tolerance_mm == 5.0


def test_global_tolerance_used_when_no_per_pair_override():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side")], tolerance_mm=7.0).pairs[0]
    assert r.tolerance_mm == 7.0


def test_mixed_tolerances_in_one_call():
    """Side seams use global 2 mm; shoulder gets per-pair 12 mm."""
    back = _make_side_part("Back", side_len=100.0, hem_len=50.0)
    front = _make_side_part("Front", side_len=100.0, hem_len=61.0)  # hem delta = 11 mm
    pat = Pattern(name="P")
    pat.add_part(back)
    pat.add_part(front)
    result = pat.validate_seam_pairs(
        [
            (back, "side", front, "side"),  # delta 0, global 2 mm → ok
            (back, "hem", front, "hem", 12.0),  # delta 11 mm, per-pair 12 mm → ok
        ]
    )
    assert result.all_ok
    assert result.pairs[0].tolerance_mm == 2.0
    assert result.pairs[1].tolerance_mm == 12.0


# ---------------------------------------------------------------------------
# Multiple pairs — all_ok aggregation
# ---------------------------------------------------------------------------


def test_all_ok_true_when_all_pairs_pass():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    assert pat.validate_seam_pairs(
        [
            (back, "side", front, "side"),
            (back, "hem", front, "hem"),
        ]
    ).all_ok


def test_all_ok_false_when_any_pair_fails():
    back = _make_side_part("Back", side_len=100.0, hem_len=50.0)
    front = _make_side_part("Front", side_len=100.0, hem_len=70.0)
    pat = Pattern(name="P")
    pat.add_part(back)
    pat.add_part(front)
    result = pat.validate_seam_pairs(
        [
            (back, "side", front, "side"),
            (back, "hem", front, "hem"),
        ],
        tolerance_mm=2.0,
        warn=False,
    )
    assert not result.all_ok
    assert result.pairs[0].ok  # side seams match
    assert not result.pairs[1].ok  # hem seams don't


# ---------------------------------------------------------------------------
# Only is_outline elements with the requested role are measured
# ---------------------------------------------------------------------------


def test_construction_elements_excluded():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    # _make_side_part adds a 999 mm construction line with role="side" — must be ignored
    r = pat.validate_seam_pairs([(back, "side", front, "side")]).pairs[0]
    assert abs(r.length_a - 100.0) < 1e-9


def test_only_requested_role_counted():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    # hem segments are 50 mm; if accidentally summed, length would be 150 mm
    r = pat.validate_seam_pairs([(back, "side", front, "side")]).pairs[0]
    assert abs(r.length_a - 100.0) < 1e-9


# ---------------------------------------------------------------------------
# Warning behaviour
# ---------------------------------------------------------------------------


def test_warning_emitted_on_mismatch():
    pat = _simple_pattern(100.0, 110.0)
    back, front = pat.parts[0], pat.parts[1]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pat.validate_seam_pairs([(back, "side", front, "side")])
    assert len(caught) == 1
    assert issubclass(caught[0].category, UserWarning)
    assert "Δ" in str(caught[0].message)


def test_no_warning_within_tolerance():
    pat = _simple_pattern(100.0, 101.0)
    back, front = pat.parts[0], pat.parts[1]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pat.validate_seam_pairs([(back, "side", front, "side")])
    assert len(caught) == 0


def test_warn_false_suppresses_warning():
    pat = _simple_pattern(100.0, 150.0)
    back, front = pat.parts[0], pat.parts[1]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pat.validate_seam_pairs([(back, "side", front, "side")], warn=False)
    assert len(caught) == 0


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_unknown_role_raises_value_error():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    with pytest.raises(ValueError, match="no_such_role"):
        pat.validate_seam_pairs([(back, "no_such_role", front, "side")])


def test_role_with_no_outline_elements_raises_value_error():
    pat = Pattern(name="P")
    for name in ("Back", "Front"):
        part = PatternPart(name=name)
        part.append(Segment(Point(0, 0), Point(100, 0)), is_construction=True, role="side")
        pat.add_part(part)
    back, front = pat.parts[0], pat.parts[1]
    with pytest.raises(ValueError):
        pat.validate_seam_pairs([(back, "side", front, "side")])


# ---------------------------------------------------------------------------
# SeamValidationResult.__str__
# ---------------------------------------------------------------------------


def test_str_contains_part_names():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    s = str(pat.validate_seam_pairs([(back, "side", front, "side")]))
    assert "Back" in s and "Front" in s


def test_str_ok_marker_when_passing():
    pat = _simple_pattern(100.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    assert "✓" in str(pat.validate_seam_pairs([(back, "side", front, "side")]))


def test_str_fail_marker_when_mismatch():
    pat = _simple_pattern(100.0, 200.0)
    back, front = pat.parts[0], pat.parts[1]
    assert "✗" in str(pat.validate_seam_pairs([(back, "side", front, "side")], warn=False))


def test_str_contains_delta_value():
    pat = _simple_pattern(120.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    assert "20" in str(pat.validate_seam_pairs([(back, "side", front, "side")], warn=False))


# ---------------------------------------------------------------------------
# SeamPairResult attributes
# ---------------------------------------------------------------------------


def test_pair_result_attributes():
    pat = _simple_pattern(130.0, 100.0)
    back, front = pat.parts[0], pat.parts[1]
    r = pat.validate_seam_pairs([(back, "side", front, "side")], warn=False).pairs[0]
    assert r.part_a == "Back" and r.role_a == "side"
    assert r.part_b == "Front" and r.role_b == "side"
    assert abs(r.length_a - 130.0) < 1e-9
    assert abs(r.length_b - 100.0) < 1e-9
    assert r.tolerance_mm == 2.0


# ---------------------------------------------------------------------------
# Integration — TopBlock side seams
# Uses standard_blouse_measurements / standard_fitclass from tests/conftest.py
# ---------------------------------------------------------------------------


@pytest.fixture
def top_block(
    standard_blouse_measurements: BlouseMeasurements,
    standard_fitclass: FitClass,
) -> TopBlock:
    config = GarmentConfig(length=70 * CM, seam_allowance=0.0)
    grid = TopGrid.from_measurements(
        meas=standard_blouse_measurements,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
    )
    return TopBlock.from_measurements(
        meas=standard_blouse_measurements,
        config=config,
        grid=grid,
        block_config=BlockConfig.WAISTED_DART,  # type: ignore[attr-defined]
        fit_class=standard_fitclass,
    )


@pytest.fixture
def top_block_pattern(top_block: TopBlock) -> Pattern:
    pat = Pattern(name="TopBlock")
    pat.add_part(top_block.back.part)
    pat.add_part(top_block.front.part)
    return pat


def test_top_block_side_seams_match(top_block: TopBlock, top_block_pattern: Pattern):
    """Back and front side seams must be equal — they share the same geometry."""
    result = top_block_pattern.validate_seam_pairs(
        [
            (top_block.back.part, "side", top_block.front.part, "side"),
        ]
    )
    assert result.all_ok, str(result)


def test_top_block_side_seam_delta_near_zero(top_block: TopBlock, top_block_pattern: Pattern):
    r = top_block_pattern.validate_seam_pairs(
        [(top_block.back.part, "side", top_block.front.part, "side")]
    ).pairs[0]
    assert abs(r.delta_mm) < 0.01, f"Unexpected delta: {r.delta_mm:.3f} mm"


def test_top_block_side_seam_lengths_positive(top_block: TopBlock, top_block_pattern: Pattern):
    r = top_block_pattern.validate_seam_pairs(
        [(top_block.back.part, "side", top_block.front.part, "side")]
    ).pairs[0]
    assert r.length_a > 0 and r.length_b > 0


def test_top_block_multiple_pairs(top_block: TopBlock, top_block_pattern: Pattern):
    """Side seams use 2 mm; shoulder seams allow 12 mm (dart take-out)."""
    result = top_block_pattern.validate_seam_pairs(
        [
            (top_block.back.part, "side", top_block.front.part, "side"),
            (top_block.back.part, "shoulder", top_block.front.part, "shoulder", 12.0),
        ]
    )
    assert result.all_ok, str(result)
    assert len(result.pairs) == 2


def test_top_block_side_seams_via_garment_part_enum(
    top_block: TopBlock, top_block_pattern: Pattern
):
    """GarmentPart enum values resolve to the correct parts."""

    class Part(GarmentPart):
        BACK = top_block.back.part.name
        FRONT = top_block.front.part.name

    result = top_block_pattern.validate_seam_pairs(
        [
            (Part.BACK, "side", Part.FRONT, "side"),
        ]
    )
    assert result.all_ok, str(result)


def test_top_block_shoulder_back_longer_than_front(top_block: TopBlock, top_block_pattern: Pattern):
    """The back shoulder is intentionally longer than the front (~12 mm dart take-out).

    This pins the structural property so accidental changes are caught.
    """
    r = top_block_pattern.validate_seam_pairs(
        [(top_block.back.part, "shoulder", top_block.front.part, "shoulder")],
        warn=False,
    ).pairs[0]
    assert r.delta_mm > 5.0, f"Expected back shoulder longer by >5 mm, got {r.delta_mm:+.1f} mm"
