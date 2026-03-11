"""Tests for __repr__, __str__, translate, set_name, and lightly-covered
methods in geometry primitives (Rect, Triangle, InfoBox, Circle, Ray, Line,
Point, Segment).
"""

import pytest

from sewpat.geometry import Circle, Line, Point, Ray, Segment
from sewpat.geometry._primitives import InfoBox, Rect, Triangle
from sewpat.units import CM, MM

# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------


def test_segment_str_with_name() -> None:
    """Segment.__str__ includes name when set."""
    seg = Segment(Point(0, 0), Point(10, 10), name="test_seg")
    result = str(seg)
    assert "test_seg" in result
    assert "Segment" in result


def test_segment_str_without_name() -> None:
    """Segment.__str__ works without name."""
    seg = Segment(Point(0, 0), Point(10, 10))
    result = str(seg)
    assert "Segment" in result
    assert "Point" in result


def test_segment_repr() -> None:
    """Segment.__repr__ returns same as __str__."""
    seg = Segment(Point(5, 5), Point(15, 15), name="repr_test")
    assert repr(seg) == str(seg)


# ---------------------------------------------------------------------------
# Ray
# ---------------------------------------------------------------------------


def test_ray_str_with_name() -> None:
    """Ray.__str__ includes name when set."""
    ray = Ray(Point(0, 0), (1, 0), name="test_ray")
    result = str(ray)
    assert "test_ray" in result
    assert "Ray" in result


def test_ray_str_without_name() -> None:
    """Ray.__str__ works without name."""
    ray = Ray(Point(0, 0), (1, 0))
    result = str(ray)
    assert "Ray" in result


def test_ray_translate() -> None:
    """Ray.translate moves the origin."""
    r = Ray(Point(0, 0), (1.0, 0.0))
    r2 = r.translate(5 * CM, 3 * CM)
    assert r2.origin.x == pytest.approx(5 * CM)
    assert r2.origin.y == pytest.approx(3 * CM)


# ---------------------------------------------------------------------------
# Line
# ---------------------------------------------------------------------------


def test_line_str_with_name() -> None:
    """Line.__str__ includes name when set."""
    line = Line(Point(0, 0), (1, 1), name="test_line")
    result = str(line)
    assert "test_line" in result
    assert "Line" in result


def test_line_str_without_name() -> None:
    """Line.__str__ works without name."""
    line = Line(Point(0, 0), (1, 1))
    result = str(line)
    assert "Line" in result


def test_line_contains_point() -> None:
    """Line.contains_point returns True for a point on the infinite line."""
    ln = Line(Point(0, 0), (1.0, 0.0))
    assert ln.contains_point(Point(5 * CM, 0))


def test_line_translate() -> None:
    """Line.translate moves the reference point."""
    ln = Line(Point(0, 0), (1.0, 0.0))
    ln2 = ln.translate(0, 10 * CM)
    assert ln2.point.y == pytest.approx(10 * CM)


# ---------------------------------------------------------------------------
# Circle
# ---------------------------------------------------------------------------


def test_circle_str_with_name() -> None:
    """Circle.__str__ includes name when set."""
    circle = Circle(Point(0, 0), 5.0, name="test_circle")
    result = str(circle)
    assert "test_circle" in result
    assert "Circle" in result


def test_circle_str_without_name() -> None:
    """Circle.__str__ works without name."""
    circle = Circle(Point(0, 0), 5.0)
    result = str(circle)
    assert "Circle" in result


def test_circle_diameter() -> None:
    """Circle.diameter equals 2 * radius."""
    c = Circle(Point(0, 0), 5 * MM)
    assert c.diameter == pytest.approx(10 * MM)


def test_circle_translate() -> None:
    """Circle.translate moves the center and preserves radius."""
    c = Circle(Point(0, 0), 5 * MM)
    c2 = c.translate(3 * CM, 4 * CM)
    assert c2.center.x == pytest.approx(3 * CM)
    assert c2.center.y == pytest.approx(4 * CM)
    assert c2.radius == pytest.approx(5 * MM)


def test_circle_set_name() -> None:
    """Circle.set_name returns self with updated name."""
    c = Circle(Point(0, 0), 5 * MM)
    result = c.set_name("bust_point")
    assert result is c
    assert c.name == "bust_point"


# ---------------------------------------------------------------------------
# Rect
# ---------------------------------------------------------------------------


def test_rect_str_without_name() -> None:
    """Rect.__str__ without name contains origin and width."""
    r = Rect(Point(0, 0), 10 * CM, 5 * CM)
    s = str(r)
    assert "Rect(origin=" in s
    assert "width=" in s


def test_rect_str_with_name() -> None:
    """Rect.__str__ with name includes the name."""
    r = Rect(Point(0, 0), 10 * CM, 5 * CM, name="pocket")
    assert "pocket" in str(r)


def test_rect_repr() -> None:
    """Rect.__repr__ starts with 'Rect(origin='."""
    r = Rect(Point(0, 0), 10 * CM, 5 * CM)
    assert repr(r).startswith("Rect(origin=")


def test_rect_translate() -> None:
    """Rect.translate moves the origin and preserves dimensions."""
    r = Rect(Point(0, 0), 10 * CM, 5 * CM)
    r2 = r.translate(2 * CM, 3 * CM)
    assert r2.origin.x == pytest.approx(2 * CM)
    assert r2.origin.y == pytest.approx(3 * CM)
    assert r2.width == pytest.approx(10 * CM)
    assert r2.height == pytest.approx(5 * CM)


def test_rect_set_name() -> None:
    """Rect.set_name returns self with the updated name."""
    r = Rect(Point(0, 0), 10 * CM, 5 * CM)
    result = r.set_name("hem")
    assert result is r
    assert r.name == "hem"


# ---------------------------------------------------------------------------
# Triangle
# ---------------------------------------------------------------------------


def test_triangle_str_without_name() -> None:
    """Triangle.__str__ without name contains all three vertices."""
    t = Triangle(Point(0, 0), Point(5 * CM, 0), Point(2.5 * CM, 4 * CM))
    s = str(t)
    assert "Triangle(p1=" in s


def test_triangle_str_with_name() -> None:
    """Triangle.__str__ with name includes the name."""
    t = Triangle(Point(0, 0), Point(5 * CM, 0), Point(2.5 * CM, 4 * CM), name="notch")
    assert "notch" in str(t)


def test_triangle_repr() -> None:
    """Triangle.__repr__ delegates to __str__."""
    t = Triangle(Point(0, 0), Point(5 * CM, 0), Point(2.5 * CM, 4 * CM))
    assert repr(t) == str(t)


def test_triangle_translate() -> None:
    """Triangle.translate moves all three vertices."""
    t = Triangle(Point(0, 0), Point(5 * CM, 0), Point(2.5 * CM, 4 * CM))
    t2 = t.translate(1 * CM, 2 * CM)
    assert t2.p1.x == pytest.approx(1 * CM)
    assert t2.p2.x == pytest.approx(6 * CM)
    assert t2.p3.y == pytest.approx(6 * CM)


def test_triangle_set_name() -> None:
    """Triangle.set_name returns self with the updated name."""
    t = Triangle(Point(0, 0), Point(5 * CM, 0), Point(2.5 * CM, 4 * CM))
    result = t.set_name("dart_notch")
    assert result is t
    assert t.name == "dart_notch"


# ---------------------------------------------------------------------------
# InfoBox
# ---------------------------------------------------------------------------


def test_infobox_str() -> None:
    """InfoBox.__str__ contains 'InfoBox'."""
    box = InfoBox(Point(0, 0), "Front", ["Size 38"])
    assert "InfoBox" in str(box)


def test_infobox_repr() -> None:
    """InfoBox.__repr__ delegates to __str__."""
    box = InfoBox(Point(0, 0), "Front", ["Size 38"])
    assert repr(box) == str(box)


def test_infobox_translate() -> None:
    """InfoBox.translate moves the position."""
    box = InfoBox(Point(0, 0), "Back", ["S"])
    box2 = box.translate(5 * CM, 5 * CM)
    assert box2.position.x == pytest.approx(5 * CM)
    assert box2.position.y == pytest.approx(5 * CM)


# ---------------------------------------------------------------------------
# Point extras
# ---------------------------------------------------------------------------


def test_point_str_with_name() -> None:
    """Point.__str__ includes the name when set via object.__setattr__ (frozen dataclass)."""
    p = Point(10.0, 20.0)
    object.__setattr__(p, "name", "cf")
    assert "cf" in str(p)


def test_point_distance_to_numpy_array() -> None:
    """Point.distance_to accepts a numpy array (non-Point branch)."""

    p = Point(3 * CM, 4 * CM)
    assert p.distance_to(p.coords) == pytest.approx(0.0)


def test_point_eq_non_point_returns_not_implemented() -> None:
    """Point.__eq__ returns NotImplemented for non-Point objects."""
    result = Point(0, 0).__eq__("not a point")
    assert result is NotImplemented


def test_point_hash_is_stable() -> None:
    """Equal Points produce identical hash values."""
    p1 = Point(5 * CM, 3 * CM)
    p2 = Point(5 * CM, 3 * CM)
    assert hash(p1) == hash(p2)
