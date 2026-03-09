"""Tests for __repr__ and __str__ methods in geometry primitives.

These tests ensure that all geometry classes have working string representations,
which is important for debugging and logging.
"""

from sewpat.geometry import Circle, Line, Point, Ray, Segment


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
