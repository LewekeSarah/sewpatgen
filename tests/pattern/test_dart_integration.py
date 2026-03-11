"""Tests for pattern/_dart_integration.py — covering previously-untested branches.

Missing lines covered here:
  91–97   — _split_edge_at_dart_mouth: _edge_element not is_outline → UserWarning + no-op
  100–107 — _split_edge_at_dart_mouth: unsupported geometry type → UserWarning + no-op
  171–176 — _add_center_notch: tip == center (degenerate fold line) → UserWarning + no-op
  212–218 — _add_leg_notch: leg_pt == roof (degenerate direction) → UserWarning + no-op
"""

import pytest

from sewpat.element import PatternElement
from sewpat.geometry import Circle, Dart, Point, Segment
from sewpat.geometry._dart import dart_from_tip_center_width
from sewpat.pattern import PatternPart
from sewpat.pattern._dart_integration import (
    _add_center_notch,
    _add_leg_notch,
    _split_edge_at_dart_mouth,
)
from sewpat.units import MM

# ---------------------------------------------------------------------------
# _split_edge_at_dart_mouth — edge not marked is_outline (lines 91–97)
# ---------------------------------------------------------------------------


def test_split_edge_not_outline_emits_warning_and_leaves_part_unchanged() -> None:
    """_split_edge_at_dart_mouth warns and skips when edge is not is_outline."""
    part = PatternPart(name="Test")
    # Add the edge element directly with is_outline=False
    edge_geom = Segment(Point(0, 0), Point(0, 100 * MM))
    elem = PatternElement(edge_geom, is_outline=False)
    part.elements.append(elem)

    # Build a minimal dart and manually point _edge_element at the non-outline elem
    dart = Dart(
        leg_a=Point(0, 40 * MM),
        leg_b=Point(0, 60 * MM),
        center=Point(0, 50 * MM),
        tip=Point(30 * MM, 50 * MM),
        _edge_element=elem,
    )

    original_count = len(part.elements)
    with pytest.warns(UserWarning, match="is_outline"):
        _split_edge_at_dart_mouth(part, dart)

    # Part must be unchanged
    assert len(part.elements) == original_count


# ---------------------------------------------------------------------------
# _split_edge_at_dart_mouth — unsupported geometry type (lines 100–107)
# ---------------------------------------------------------------------------


def test_split_edge_unsupported_geometry_emits_warning_and_leaves_part_unchanged() -> None:
    """_split_edge_at_dart_mouth warns and skips for non-Segment/CubicBezier geometry."""
    part = PatternPart(name="Test")

    # Use a Circle as the geometry — not supported by the splitter
    circle = Circle(Point(0, 50 * MM), 10 * MM)
    elem = PatternElement(circle, is_outline=True)
    part.elements.append(elem)

    # Build a dart that references this element via _edge_element
    dart = Dart(
        leg_a=Point(0, 40 * MM),
        leg_b=Point(0, 60 * MM),
        center=Point(0, 50 * MM),
        tip=Point(30 * MM, 50 * MM),
        _edge_element=elem,
    )

    original_count = len(part.elements)
    with pytest.warns(UserWarning, match="expected Segment or CubicBezier"):
        _split_edge_at_dart_mouth(part, dart)

    assert len(part.elements) == original_count


# ---------------------------------------------------------------------------
# _add_center_notch — degenerate fold line: tip == center (lines 171–176)
# ---------------------------------------------------------------------------


def test_add_center_notch_degenerate_fold_line_emits_warning() -> None:
    """_add_center_notch warns when tip and center coincide."""
    part = PatternPart(name="Test")

    # Construct a dart where tip and center are the same point by using the
    # raw Dart constructor directly (dart_from_tip_center_width would raise ValueError)
    same_point = Point(50 * MM, 50 * MM)
    dart = Dart(
        leg_a=Point(40 * MM, 50 * MM),
        leg_b=Point(60 * MM, 50 * MM),
        center=same_point,
        tip=same_point,  # <-- tip == center → degenerate fold line
    )

    original_count = len(part.elements)
    with pytest.warns(UserWarning, match="tip and center coincide"):
        _add_center_notch(part, dart, length=8 * MM, width=4 * MM)

    # No elements should have been added
    assert len(part.elements) == original_count


# ---------------------------------------------------------------------------
# _add_leg_notch — degenerate direction: leg_pt == roof (lines 212–218)
# ---------------------------------------------------------------------------


def test_add_leg_notch_degenerate_direction_emits_warning() -> None:
    """_add_leg_notch warns when leg_pt coincides with dart.roof."""
    part = PatternPart(name="Test")

    dart = dart_from_tip_center_width(
        tip=Point(50 * MM, 20 * MM),
        center=Point(50 * MM, 60 * MM),
        width=20 * MM,
    )

    # Pass dart.roof as the leg_pt — that is the degenerate case
    original_count = len(part.elements)
    with pytest.warns(UserWarning, match="leg point coincides with roof peak"):
        _add_leg_notch(part, dart, dart.roof, length=8 * MM, width=4 * MM)

    assert len(part.elements) == original_count
