"""Tests for the Pattern class (container, add_part, get_part, reference square).

Covers:
  - Pattern creation defaults and custom anchor
  - add_part / get_part
  - add_reference_square (size, style, auto-placement)
"""

from typing import cast

import pytest

from sewpat.geometry import Point, Rect, Segment
from sewpat.pattern import Pattern, PatternPart
from sewpat.style import StyleOptions
from sewpat.units import CM

from .conftest import _pattern_with_square_part

# ---------------------------------------------------------------------------
# Pattern -- creation and basic API
# ---------------------------------------------------------------------------


def test_pattern_creation_defaults():
    pat = Pattern(name="My Pattern")
    assert pat.name == "My Pattern"
    assert len(pat.parts) == 0
    assert pat.reference_square is None
    assert abs(pat.anchor.x - 1.5 * CM) < 1e-9
    assert abs(pat.anchor.y - 1.5 * CM) < 1e-9


def test_pattern_custom_anchor():
    anchor = Point(2 * CM, 3 * CM)
    assert Pattern(name="P", anchor=anchor).anchor is anchor


def test_pattern_add_part():
    pat = Pattern(name="P")
    part = PatternPart(name="Front")
    returned = pat.add_part(part)
    assert returned is part
    assert len(pat.parts) == 1 and pat.parts[0] is part


def test_pattern_get_part_found():
    pat = Pattern(name="P")
    front, back = PatternPart(name="Front"), PatternPart(name="Back")
    pat.add_part(front)
    pat.add_part(back)
    assert pat.get_part("Back") is back


def test_pattern_get_part_not_found():
    with pytest.raises(KeyError):
        Pattern(name="P").get_part("NonExistent")


def test_pattern_creation_with_parts():
    parts = [PatternPart(name="Front"), PatternPart(name="Back")]
    assert len(Pattern(name="P", parts=parts).parts) == 2


# ---------------------------------------------------------------------------
# Pattern -- add_reference_square
# ---------------------------------------------------------------------------


def test_pattern_add_reference_square_default():
    pat = Pattern(name="P")
    elem = pat.add_reference_square(Point(0, 0))
    assert pat.reference_square is elem
    rect = cast(Rect, elem.geometry)
    assert abs(rect.width - 3 * CM) < 1e-9
    assert abs(rect.height - 3 * CM) < 1e-9


def test_pattern_add_reference_square_custom_edge_length():
    rect = cast(
        Rect, Pattern(name="P").add_reference_square(Point(0, 0), edge_length=5 * CM).geometry
    )
    assert abs(rect.width - 5 * CM) < 1e-9 and abs(rect.height - 5 * CM) < 1e-9


def test_pattern_add_reference_square_custom_style():
    style = StyleOptions(stroke_color="red")
    assert Pattern(name="P").add_reference_square(Point(0, 0), style=style).style is style


# ---------------------------------------------------------------------------
# Pattern -- add_reference_square auto-placement
# ---------------------------------------------------------------------------


def test_reference_square_origin_inside_unchanged():
    """An origin already well inside the bbox is not moved."""
    pat, _ = _pattern_with_square_part(200)
    edge = 3 * CM
    rect = cast(Rect, pat.add_reference_square(Point(10, 10), edge_length=edge).geometry)
    assert abs(rect.origin.x - 10.0) < 1e-3 and abs(rect.origin.y - 10.0) < 1e-3


def test_reference_square_origin_outside_is_shifted_inside():
    pat, _ = _pattern_with_square_part(200)
    edge = 3 * CM
    rect = cast(Rect, pat.add_reference_square(Point(-500, -500), edge_length=edge).geometry)
    assert rect.origin.x >= 0.0 and rect.origin.y >= 0.0
    assert rect.origin.x + edge <= 200.0 and rect.origin.y + edge <= 200.0


def test_reference_square_explicit_part_used_over_auto():
    """When *part* is supplied explicitly it constrains placement to that part."""
    pat = Pattern(name="P")
    part_a, part_b = PatternPart(name="A"), PatternPart(name="B")
    for seg in [
        Segment(Point(0, 0), Point(50, 0)),
        Segment(Point(50, 0), Point(50, 50)),
        Segment(Point(50, 50), Point(0, 50)),
        Segment(Point(0, 50), Point(0, 0)),
    ]:
        part_a.append(seg, is_outline=True)
    for seg in [
        Segment(Point(0, 0), Point(400, 0)),
        Segment(Point(400, 0), Point(400, 400)),
        Segment(Point(400, 400), Point(0, 400)),
        Segment(Point(0, 400), Point(0, 0)),
    ]:
        part_b.append(seg, is_outline=True)
    pat.add_part(part_a)
    pat.add_part(part_b)
    edge = 3 * CM
    rect = cast(
        Rect, pat.add_reference_square(Point(-100, -100), edge_length=edge, part=part_a).geometry
    )
    assert rect.origin.x + edge <= 50.0 and rect.origin.y + edge <= 50.0


def test_reference_square_no_parts_origin_unchanged():
    rect = cast(
        Rect, Pattern(name="P").add_reference_square(Point(5, 5), edge_length=3 * CM).geometry
    )
    assert abs(rect.origin.x - 5.0) < 1e-9 and abs(rect.origin.y - 5.0) < 1e-9
