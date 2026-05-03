"""Tests for Pattern.validate_widths and PatternPart.width_at_y.

New API: validate_widths uses a 9- or 10-tuple spec
  (back_part, back_center_role, back_side_role,
   front_part, front_center_role, front_side_role,
   label, grid_segment, expected_mm[, tolerance_mm])

Width is computed by intersecting *grid_segment* (used as an infinite line)
with the role-tagged center and side seam edges on each pattern piece.  This
approach does not assume any particular coordinate orientation.

Covers:
  - PatternPart.width_at_y basic geometry (utility method retained).
  - _intersect_grid_with_role error paths.
  - Pattern.validate_widths return-type shape.
  - Correctness: delta, ok flag, all_ok aggregation.
  - Per-level tolerance override (10th element).
  - PatternPart objects and name strings both accepted as part refs.
  - Warning behaviour (emitted / suppressed).
  - WidthValidationResult.__str__ output.
  - WidthCheckResult attribute values (roles stored).
  - Integration test using a real TopBlock.
"""

import warnings

import pytest

from sewpat.blocks import BlockConfig, TopBlock
from sewpat.fitclass import FitClass
from sewpat.geometry import Point, Segment
from sewpat.grids import GridConfig, TopGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import Pattern, PatternPart, WidthCheckResult, WidthValidationResult
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _rect_with_roles(
    name: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    center_role: str = "center",
    side_role: str = "side",
) -> PatternPart:
    """Rectangle whose left edge has *center_role* and right edge has *side_role*."""
    part = PatternPart(name=name)
    part.append(Segment(Point(x0, y0), Point(x0, y1)), is_outline=True, role=center_role)
    part.append(Segment(Point(x0, y1), Point(x1, y1)), is_outline=True)
    part.append(Segment(Point(x1, y1), Point(x1, y0)), is_outline=True, role=side_role)
    part.append(Segment(Point(x1, y0), Point(x0, y0)), is_outline=True)
    return part


def _grid_seg(y: float = 100.0) -> Segment:
    """Wide horizontal segment at height *y*, mimicking a TopGrid construction line."""
    return Segment(Point(-1500, y), Point(1500, y), name=f"Level y={y}")


def _simple_pattern(
    back_width: float = 50.0,
    front_width: float = 50.0,
    height: float = 200.0,
) -> tuple[Pattern, PatternPart, PatternPart]:
    """Pattern with rectangular back and front pieces that carry center/side roles."""
    back = _rect_with_roles(
        "Back", 0, 0, back_width, height, center_role="center_back", side_role="side"
    )
    front_x0 = back_width + 10
    front = _rect_with_roles(
        "Front",
        front_x0,
        0,
        front_x0 + front_width,
        height,
        center_role="center_front",
        side_role="side",
    )
    pat = Pattern(name="P")
    pat.add_part(back)
    pat.add_part(front)
    return pat, back, front


def _spec(back, front, label="Bust", y=100.0, expected=100.0, tol=None):
    """Build a WidthLevelSpec tuple for the standard test parts."""
    gs = _grid_seg(y)
    base = (back, "center_back", "side", front, "center_front", "side", label, gs, expected)
    return base if tol is None else (*base, tol)


# ---------------------------------------------------------------------------
# PatternPart.width_at_y  (utility method — retained)
# ---------------------------------------------------------------------------


def test_width_at_y_simple_rectangle(_rect_part: PatternPart):
    part = _rect_part(0, 0, 50, 200)
    part.name = "Back"
    min_x, max_x = part.width_at_y(100)
    assert abs(min_x - 0) < 1e-6
    assert abs(max_x - 50) < 1e-6


def test_width_at_y_returns_correct_width(_rect_part: PatternPart):
    part = _rect_part(0, 0, 70, 300)
    part.name = "Back"
    min_x, max_x = part.width_at_y(150)
    assert abs(max_x - min_x - 70) < 1e-6


def test_width_at_y_no_outline_raises_value_error():
    part = PatternPart(name="Empty")
    with pytest.raises(ValueError, match="no outline polygon"):
        part.width_at_y(100)


def test_width_at_y_outside_polygon_raises_value_error(_rect_part: PatternPart):
    part = _rect_part(0, 0, 50, 200)
    part.name = "Back"
    with pytest.raises(ValueError, match="does not intersect"):
        part.width_at_y(500)


# ---------------------------------------------------------------------------
# Pattern.validate_widths — return type and basic shape
# ---------------------------------------------------------------------------


def test_returns_width_validation_result():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front, expected=100)], warn=False)
    assert isinstance(result, WidthValidationResult)


def test_result_has_one_check_per_level():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths(
        [
            _spec(back, front, "Bust", y=50, expected=100),
            _spec(back, front, "Waist", y=100, expected=100),
        ],
        warn=False,
    )
    assert len(result.checks) == 2


def test_each_entry_is_width_check_result():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front)], warn=False)
    assert isinstance(result.checks[0], WidthCheckResult)


# ---------------------------------------------------------------------------
# Correctness
# ---------------------------------------------------------------------------


def test_identical_widths_ok():
    """Back=50, Front=50, total=100, expected=100 → ok."""
    pat, back, front = _simple_pattern(50, 50)
    result = pat.validate_widths([_spec(back, front, expected=100)], warn=False)
    assert result.all_ok
    assert result.checks[0].ok


def test_delta_is_total_minus_expected():
    """Back=60, Front=50, total=110, expected=100 → delta=+10."""
    pat, back, front = _simple_pattern(60, 50)
    r = pat.validate_widths([_spec(back, front, expected=100, tol=20)], warn=False).checks[0]
    assert abs(r.delta_mm - 10.0) < 1e-6


def test_negative_delta_when_total_smaller():
    """Back=40, Front=50, total=90, expected=100 → delta=−10."""
    pat, back, front = _simple_pattern(40, 50)
    r = pat.validate_widths([_spec(back, front, expected=100, tol=20)], warn=False).checks[0]
    assert abs(r.delta_mm - (-10.0)) < 1e-6


def test_all_ok_false_when_mismatch():
    pat, back, front = _simple_pattern(60, 50)
    result = pat.validate_widths([_spec(back, front, expected=100, tol=5)], warn=False)
    assert not result.all_ok
    assert not result.checks[0].ok


def test_all_ok_true_when_within_tolerance():
    pat, back, front = _simple_pattern(52, 50)  # total=102, delta=+2 < tol=5
    result = pat.validate_widths([_spec(back, front, expected=100, tol=5)], warn=False)
    assert result.all_ok
    assert result.checks[0].ok


def test_all_ok_false_when_any_level_fails():
    pat, back, front = _simple_pattern(50, 50)
    result = pat.validate_widths(
        [
            _spec(back, front, "Bust", y=50, expected=100),  # delta=0  → ok
            _spec(back, front, "Waist", y=100, expected=80),  # delta=20 → fail
        ],
        tolerance_mm=5,
        warn=False,
    )
    assert not result.all_ok
    assert result.checks[0].ok
    assert not result.checks[1].ok


def test_back_front_widths_recorded():
    pat, back, front = _simple_pattern(55, 45)
    r = pat.validate_widths([_spec(back, front, expected=100, tol=20)], warn=False).checks[0]
    assert abs(r.back_width_mm - 55) < 1e-6
    assert abs(r.front_width_mm - 45) < 1e-6
    assert abs(r.total_width_mm - 100) < 1e-6


# ---------------------------------------------------------------------------
# Per-level tolerance override (10th element)
# ---------------------------------------------------------------------------


def test_per_level_tolerance_override_passes():
    """10th element overrides global tolerance: 10 mm Δ passes with tol=20."""
    pat, back, front = _simple_pattern(60, 50)
    result = pat.validate_widths(
        [_spec(back, front, expected=100, tol=20)],
        tolerance_mm=5,
        warn=False,
    )
    assert result.checks[0].ok
    assert result.checks[0].tolerance_mm == 20


def test_per_level_tolerance_override_fails():
    """Global tol=20, per-level tol=5: delta=10 fails."""
    pat, back, front = _simple_pattern(60, 50)
    result = pat.validate_widths(
        [_spec(back, front, expected=100, tol=5)],
        tolerance_mm=20,
        warn=False,
    )
    assert not result.checks[0].ok


# ---------------------------------------------------------------------------
# Part references: objects and name strings
# ---------------------------------------------------------------------------


def test_accepts_pattern_part_objects():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front)], warn=False)
    assert isinstance(result, WidthValidationResult)


def test_accepts_part_name_strings():
    pat, back, front = _simple_pattern()
    gs = _grid_seg()
    result = pat.validate_widths(
        [("Back", "center_back", "side", "Front", "center_front", "side", "Bust", gs, 100)],
        warn=False,
    )
    assert isinstance(result, WidthValidationResult)


def test_accepts_mixed_object_and_string():
    pat, back, front = _simple_pattern()
    gs = _grid_seg()
    result = pat.validate_widths(
        [(back, "center_back", "side", "Front", "center_front", "side", "Bust", gs, 100)],
        warn=False,
    )
    assert isinstance(result, WidthValidationResult)


def test_unknown_part_name_raises_key_error():
    pat, back, front = _simple_pattern()
    gs = _grid_seg()
    with pytest.raises(KeyError):
        pat.validate_widths(
            [
                (
                    "NonExistent",
                    "center_back",
                    "side",
                    "Front",
                    "center_front",
                    "side",
                    "Bust",
                    gs,
                    100,
                )
            ],
            warn=False,
        )


def test_missing_role_raises_value_error():
    """A role that does not exist on a part raises ValueError."""
    pat, back, front = _simple_pattern()
    gs = _grid_seg()
    with pytest.raises(ValueError, match="No is_outline elements"):
        pat.validate_widths(
            [(back, "nonexistent_role", "side", front, "center_front", "side", "Bust", gs, 100)],
            warn=False,
        )


def test_no_intersection_raises_value_error():
    """Grid segment that does not intersect the seam edges raises ValueError."""
    pat, back, front = _simple_pattern()
    gs = Segment(Point(-1000, 500), Point(1000, 500), name="out-of-range")
    with pytest.raises(ValueError, match="does not intersect"):
        pat.validate_widths(
            [(back, "center_back", "side", front, "center_front", "side", "Bust", gs, 100)],
            warn=False,
        )


# ---------------------------------------------------------------------------
# Warning behaviour
# ---------------------------------------------------------------------------


def test_warning_emitted_on_mismatch():
    pat, back, front = _simple_pattern(60, 50)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pat.validate_widths([_spec(back, front, expected=100, tol=5)])
    assert any(issubclass(warning.category, UserWarning) for warning in w)


def test_warn_false_suppresses_warning():
    pat, back, front = _simple_pattern(60, 50)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pat.validate_widths([_spec(back, front, expected=100, tol=5)], warn=False)
    assert not any(issubclass(warning.category, UserWarning) for warning in w)


def test_no_warning_within_tolerance():
    pat, back, front = _simple_pattern(52, 50)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pat.validate_widths([_spec(back, front, expected=100, tol=5)])
    assert not any(issubclass(warning.category, UserWarning) for warning in w)


def test_warning_message_contains_label():
    pat, back, front = _simple_pattern(60, 50)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pat.validate_widths([_spec(back, front, label="HipLevel", expected=100, tol=5)])
    assert any("HipLevel" in str(warning.message) for warning in w)


# ---------------------------------------------------------------------------
# WidthValidationResult.__str__
# ---------------------------------------------------------------------------


def test_str_contains_level_label():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front, label="Hüfte")], warn=False)
    assert "Hüfte" in str(result)


def test_str_ok_marker_when_passing():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front)], warn=False)
    assert "✓" in str(result)


def test_str_fail_marker_when_mismatch():
    pat, back, front = _simple_pattern(60, 50)
    result = pat.validate_widths([_spec(back, front, expected=100, tol=5)], warn=False)
    assert "✗" in str(result)


def test_str_contains_delta_value():
    pat, back, front = _simple_pattern(60, 50)
    result = pat.validate_widths([_spec(back, front, expected=100, tol=20)], warn=False)
    assert "+10" in str(result)


def test_str_all_ok_header():
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front)], warn=False)
    assert "all OK" in str(result)


def test_str_mismatches_header_when_failed():
    pat, back, front = _simple_pattern(60, 50)
    result = pat.validate_widths([_spec(back, front, expected=100, tol=5)], warn=False)
    assert "mismatches" in str(result)


def test_str_contains_role_names():
    """The __str__ output should show the center and side roles."""
    pat, back, front = _simple_pattern()
    result = pat.validate_widths([_spec(back, front)], warn=False)
    s = str(result)
    assert "center_back" in s
    assert "center_front" in s


# ---------------------------------------------------------------------------
# WidthCheckResult attributes
# ---------------------------------------------------------------------------


def test_check_result_label():
    pat, back, front = _simple_pattern()
    r = pat.validate_widths([_spec(back, front, label="Taillenweite")], warn=False).checks[0]
    assert r.label == "Taillenweite"


def test_check_result_part_names():
    pat, back, front = _simple_pattern()
    r = pat.validate_widths([_spec(back, front)], warn=False).checks[0]
    assert r.back_part == "Back"
    assert r.front_part == "Front"


def test_check_result_roles_stored():
    pat, back, front = _simple_pattern()
    r = pat.validate_widths([_spec(back, front)], warn=False).checks[0]
    assert r.back_center_role == "center_back"
    assert r.back_side_role == "side"
    assert r.front_center_role == "center_front"
    assert r.front_side_role == "side"


def test_check_result_widths_and_delta():
    pat, back, front = _simple_pattern(50, 60)
    r = pat.validate_widths([_spec(back, front, expected=110, tol=5)], warn=False).checks[0]
    assert abs(r.back_width_mm - 50) < 1e-6
    assert abs(r.front_width_mm - 60) < 1e-6
    assert abs(r.total_width_mm - 110) < 1e-6
    assert abs(r.expected_mm - 110) < 1e-6
    assert abs(r.delta_mm) < 1e-6
    assert r.ok


def test_check_result_tolerance_mm():
    pat, back, front = _simple_pattern()
    r = pat.validate_widths([_spec(back, front, tol=7.5)], warn=False).checks[0]
    assert abs(r.tolerance_mm - 7.5) < 1e-9


# ---------------------------------------------------------------------------
# Integration — TopBlock width at bust / waist / hip
# Uses standard_blouse_measurements / standard_fitclass from tests/conftest.py
# ---------------------------------------------------------------------------


@pytest.fixture
def top_block(
    standard_blouse_measurements: BlouseMeasurements,
    standard_fitclass: FitClass,
) -> tuple[Pattern, TopGrid, BlouseMeasurements]:
    """Build a real TopBlock and return (pattern, grid, meas)."""
    meas = standard_blouse_measurements
    config = GarmentConfig(length=70 * CM)
    from sewpat.pattern import PatternConfig

    layout = PatternConfig()
    pattern = Pattern(name="Test", anchor=layout.anchor)
    grid = TopGrid.from_measurements(
        meas=meas,
        fit_class=standard_fitclass,
        config=config,
        grid_config=GridConfig.WAISTED_DART,
    )
    pattern.add_part(grid.part)
    block = TopBlock.from_measurements(
        meas=meas,
        config=config,
        grid=grid,
        block_config=BlockConfig.WAISTED_DART,
        fit_class=standard_fitclass,
    )
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)
    return pattern, grid, meas


def _wspec(back_name, front_name, label, grid_seg, expected_mm, tol=5.0):
    return (
        back_name,
        "center_back",
        "side",
        front_name,
        "center_front",
        "side",
        label,
        grid_seg,
        expected_mm,
        tol,
    )


def test_integration_returns_width_validation_result(top_block):
    pattern, grid, meas = top_block
    result = pattern.validate_widths(
        [_wspec("Block Back", "Block Front", "Bust", grid.chest, meas.bust_width / 2)],
        warn=False,
    )
    assert isinstance(result, WidthValidationResult)


def test_integration_bust_width_matches_measurement(top_block):
    """Grid-segment intersection at chest level is close to meas.bust_width / 2.

    The default PersonalAdjustments(hip_offset=2 cm) tilts the center-back
    segment ~9.6 mm inward at chest level, so the measured width is slightly
    less than the raw half-width.  A tolerance of 12 mm covers this expected
    construction offset while still catching gross errors.
    """
    pattern, grid, meas = top_block
    result = pattern.validate_widths(
        [_wspec("Block Back", "Block Front", "Bust", grid.chest, meas.bust_width / 2, tol=12.0)],
        warn=False,
    )
    assert result.all_ok, str(result)


def test_integration_hip_width_matches_measurement(top_block):
    """Grid-segment intersection at hip level ≈ meas.hip_width / 2 (±5 mm)."""
    pattern, grid, meas = top_block
    result = pattern.validate_widths(
        [_wspec("Block Back", "Block Front", "Hip", grid.hip, meas.hip_width / 2)],
        warn=False,
    )
    assert result.all_ok, str(result)


def test_integration_all_three_levels(top_block):
    """All three levels can be checked in one call without raising."""
    pattern, grid, meas = top_block
    result = pattern.validate_widths(
        [
            _wspec("Block Back", "Block Front", "Bust", grid.chest, meas.bust_width / 2, 2.0),
            _wspec("Block Back", "Block Front", "Waist", grid.waist, meas.waist_width / 2, 20.0),
            _wspec("Block Back", "Block Front", "Hip", grid.hip, meas.hip_width / 2, 5.0),
        ],
        warn=False,
    )
    assert len(result.checks) == 3
