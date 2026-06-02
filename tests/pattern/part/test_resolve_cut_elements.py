"""Tests for PatternPart._resolve_cut_elements."""

import pytest

from sewpat.geometry import Point, Ray, Segment
from sewpat.pattern import PatternPart


def _part_with_cutlines(*names: str) -> PatternPart:
    """Part with one cutline element per name, added via add_cutline."""
    part = PatternPart(name="Body")
    for name in names:
        ray = Ray(Point(0, 0), (1, 0)).set_name(name)
        part.add_cutline(ray)
    return part


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


def test_empty_list_returns_empty():
    part = _part_with_cutlines("Cut A")
    result = part._resolve_cut_elements([])
    assert result == []


def test_single_name_returns_one_element():
    part = _part_with_cutlines("Cut A")
    result = part._resolve_cut_elements(["Cut A"])
    assert len(result) == 1
    assert result[0].get_name() == "Cut A"
    assert result[0].role == "cutline"


def test_multiple_names_returned_in_order():
    part = _part_with_cutlines("Cut A", "Cut B", "Cut C")
    result = part._resolve_cut_elements(["Cut C", "Cut A"])
    assert [e.get_name() for e in result] == ["Cut C", "Cut A"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unknown_name_raises_key_error():
    part = _part_with_cutlines("Cut A")
    with pytest.raises(KeyError, match="Cut line named"):
        part._resolve_cut_elements(["Ghost"])


def test_error_message_contains_part_name():
    part = _part_with_cutlines("Cut A")
    with pytest.raises(KeyError, match="Body"):
        part._resolve_cut_elements(["Ghost"])


def test_error_message_contains_missing_cut_name():
    part = _part_with_cutlines("Cut A")
    with pytest.raises(KeyError, match="Missing Cut"):
        part._resolve_cut_elements(["Missing Cut"])


def test_element_with_wrong_role_not_resolved():
    # An element named "Side" but with role="side" must not satisfy the cutline lookup.
    part = PatternPart(name="Body")
    seg = Segment(Point(0, 0), Point(10, 0))
    seg.set_name("Side")
    part.append(seg, role="side")
    with pytest.raises(KeyError):
        part._resolve_cut_elements(["Side"])
