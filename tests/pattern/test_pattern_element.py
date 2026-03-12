"""Tests for PatternElement and PatternPart basic collection operations.

Covers:
  - PatternElement: creation, get_name (own name, geometry name, no name)
  - PatternPart: append, extend, creation with elements
"""

from sewpat.element import PatternElement
from sewpat.geometry import Point, Segment
from sewpat.pattern import PatternPart
from sewpat.style import StyleOptions

# ---------------------------------------------------------------------------
# PatternElement
# ---------------------------------------------------------------------------


def test_creation_default_style():
    """PatternElement with no style gets a default StyleOptions instance."""
    p = Point(0, 0)
    elem = PatternElement(geometry=p)
    assert isinstance(elem.style, StyleOptions)
    assert elem.geometry is p


def test_creation_with_style_and_named_geometry():
    """Style is stored correctly; name is read from geometry.name."""
    p = Point(1, 2)
    style = StyleOptions(stroke_color="red")
    elem = PatternElement(geometry=p, style=style)
    assert elem.style is style
    assert elem.get_name() is None  # Point has no name


def test_get_name_from_geometry():
    """get_name returns the name set on the geometry object."""
    seg = Segment(Point(0, 0), Point(1, 0), name="geo-name")
    elem = PatternElement(geometry=seg)
    assert elem.get_name() == "geo-name"


def test_get_name_via_named_fluent():
    """get_name works when name is set via the .set_name() fluent method."""
    seg = Segment(Point(0, 0), Point(1, 0)).set_name("fluent-name")
    elem = PatternElement(geometry=seg)
    assert elem.get_name() == "fluent-name"


def test_get_name_none_when_absent():
    """get_name returns None when geometry carries no name."""
    p = Point(0, 0)
    elem = PatternElement(geometry=p)
    assert elem.get_name() is None


# ---------------------------------------------------------------------------
# PatternPart -- basic collection operations
# ---------------------------------------------------------------------------


def test_creation_empty():
    """A freshly created PatternPart has no elements."""
    part = PatternPart(name="Bodice")
    assert part.name == "Bodice"
    assert len(part.elements) == 0


def test_append_returns_element():
    """append() returns the created PatternElement."""
    part = PatternPart(name="Body")
    p = Point(1, 2)
    elem = part.append(p)
    assert isinstance(elem, PatternElement)
    assert elem.geometry is p
    assert len(part.elements) == 1


def test_append_with_style_and_named_geometry():
    """append() passes style through; name comes from geometry.name."""
    part = PatternPart(name="Body")
    style = StyleOptions(stroke_color="blue")
    elem = part.append(Segment(Point(0, 0), Point(1, 0), name="centre"), style=style)
    assert elem.style is style
    assert elem.get_name() == "centre"


def test_extend():
    """extend() appends multiple PatternElements at once."""
    part = PatternPart(name="Body")
    elems = [
        PatternElement(Point(0, 0)),
        PatternElement(Point(1, 1)),
        PatternElement(Point(2, 2)),
    ]
    part.extend(elems)
    assert len(part.elements) == 3
    assert part.elements[2].geometry is elems[2].geometry


def test_creation_with_elements():
    """PatternPart can be initialised with a pre-existing list of elements."""
    elems = [PatternElement(Point(5, 5))]
    part = PatternPart(name="Collar", elements=elems)
    assert len(part.elements) == 1
