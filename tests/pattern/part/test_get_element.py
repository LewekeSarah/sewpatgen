"""Tests for PatternPart.get_element and NamedAccessMixin.__getattr__."""

import pytest

from sewpat.geometry import Point, Segment
from sewpat.pattern import PatternPart


def _part_with_named_elements() -> PatternPart:
    """Part with two named segments and one segment that has a role."""
    part = PatternPart(name="Body")
    seg_a = Segment(Point(0, 0), Point(10, 0))
    seg_a.set_name("Center Back")
    part.append(seg_a, role="back")

    seg_b = Segment(Point(10, 0), Point(20, 0))
    seg_b.set_name("Side Seam")
    part.append(seg_b, role="side")

    seg_dup = Segment(Point(20, 0), Point(30, 0))
    seg_dup.set_name("Side Seam")
    part.append(seg_dup, role="hem")

    return part


# ---------------------------------------------------------------------------
# get_element — basic name lookup
# ---------------------------------------------------------------------------


def test_get_element_by_name_returns_element():
    part = _part_with_named_elements()
    elem = part.get_element("Center Back")
    assert elem.get_name() == "Center Back"


def test_get_element_by_name_returns_first_match():
    # "Side Seam" appears twice; get_element should return the first one (role="side")
    part = _part_with_named_elements()
    elem = part.get_element("Side Seam")
    assert elem.role == "side"


def test_get_element_missing_name_raises_key_error():
    part = _part_with_named_elements()
    with pytest.raises(KeyError, match="No element named"):
        part.get_element("Nonexistent")


def test_get_element_key_error_message_contains_part_name():
    part = _part_with_named_elements()
    with pytest.raises(KeyError, match="Body"):
        part.get_element("Ghost")


# ---------------------------------------------------------------------------
# get_element — name + role lookup
# ---------------------------------------------------------------------------


def test_get_element_by_name_and_role():
    part = _part_with_named_elements()
    elem = part.get_element("Side Seam", role="hem")
    assert elem.role == "hem"


def test_get_element_role_mismatch_raises_key_error():
    part = _part_with_named_elements()
    with pytest.raises(KeyError, match="No element named"):
        part.get_element("Center Back", role="front")


def test_get_element_role_error_message_contains_role():
    part = _part_with_named_elements()
    with pytest.raises(KeyError, match="nonexistent_role"):
        part.get_element("Center Back", role="nonexistent_role")


# ---------------------------------------------------------------------------
# NamedAccessMixin — snake_case attribute access
# ---------------------------------------------------------------------------


def test_named_access_resolves_snake_case():
    part = _part_with_named_elements()
    elem = part.center_back
    assert elem.get_name() == "Center Back"


def test_named_access_missing_raises_attribute_error():
    part = _part_with_named_elements()
    with pytest.raises(AttributeError):
        _ = part.nonexistent_element


def test_named_access_private_name_raises_attribute_error():
    part = _part_with_named_elements()
    with pytest.raises(AttributeError):
        _ = part._private
