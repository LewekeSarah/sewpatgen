"""Tests for rendering Ray and Line geometry in render.py.

These tests cover the previously untested Ray and Line rendering paths.
"""

from sewpat.geometry import Line, Point, Ray
from sewpat.render import _render_line, _render_ray


def test_render_ray_returns_svg_elements() -> None:
    """_render_ray returns a list of SVG strings."""
    ray = Ray(Point(10, 10), (1, 0), name="test_ray")
    style_dict = {"stroke": "black", "stroke-width": "1"}

    result = _render_ray(ray, style_dict)
    assert isinstance(result, list)
    assert len(result) > 0
    assert any("<line" in s for s in result)


def test_render_ray_with_name_includes_label() -> None:
    """_render_ray includes the name as a text label."""
    ray = Ray(Point(0, 0), (1, 0), name="my_ray")
    style_dict = {"stroke": "black", "stroke-width": "1"}

    result = _render_ray(ray, style_dict)
    svg_text = "".join(result)
    assert "my_ray" in svg_text


def test_render_ray_without_name() -> None:
    """_render_ray works without a name."""
    ray = Ray(Point(50, 50), (0, 1))  # vertical ray
    style_dict = {"stroke": "blue"}

    result = _render_ray(ray, style_dict)
    assert isinstance(result, list)
    assert len(result) > 0


def test_render_line_returns_svg_elements() -> None:
    """_render_line returns a list of SVG strings."""
    line = Line(Point(50, 50), (1, 0), name="test_line")
    style_dict = {"stroke": "red", "stroke-width": "2"}

    result = _render_line(line, style_dict)
    assert isinstance(result, list)
    assert len(result) > 0
    assert any("<line" in s for s in result)


def test_render_line_with_name_includes_label() -> None:
    """_render_line includes the name as a text label."""
    line = Line(Point(10, 20), (1, 1), name="my_line")
    style_dict = {"stroke": "green"}

    result = _render_line(line, style_dict)
    svg_text = "".join(result)
    assert "my_line" in svg_text


def test_render_line_without_name() -> None:
    """_render_line works without a name."""
    line = Line(Point(100, 100), (1, 0))
    style_dict = {"stroke": "black"}

    result = _render_line(line, style_dict)
    assert isinstance(result, list)
    assert len(result) > 0
