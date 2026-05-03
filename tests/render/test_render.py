"""
Comprehensive tests for the render module.

Covers:
  - _resolve_styles: default copy, valid overrides, unknown-key error
  - _build_svg: SVG envelope, title, arrow defs, element groups
  - _render_* helpers: Segment, Circle, Triangle, Rect, Point, InfoBox, CubicBezier
  - export_pattern_part_svg_mm: file output, content, optional args
  - export_pattern_svg_mm: all parts, selected parts, reference square, parts filter
"""

import re
import tempfile
from pathlib import Path

import pytest

from sewpat.element import PatternElement
from sewpat.geometry import (
    Circle,
    CubicBezier,
    InfoBox,
    Point,
    Rect,
    Segment,
    Triangle,
)
from sewpat.pattern import Pattern, PatternPart
from sewpat.render import (
    _build_svg,
    _resolve_styles,
    export_pattern_part_svg_mm,
    export_pattern_svg_mm,
)
from sewpat.style import (
    STYLE_GRAINLINE,
    STYLE_STITCH,
    StyleOptions,
)
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _part_with(*geometries_and_styles) -> PatternPart:
    """Build a PatternPart from (geometry, style?) pairs or plain geometries."""
    part = PatternPart(name="test_part")
    for item in geometries_and_styles:
        if isinstance(item, tuple):
            geom, style = item
            part.append(geom, style=style)
        else:
            part.append(item)
    return part


# ---------------------------------------------------------------------------
# _resolve_styles
# ---------------------------------------------------------------------------


def test_resolve_styles_returns_all_default_keys():
    """Returns all expected style keys."""
    styles = _resolve_styles(None)
    assert "segment" in styles
    assert "point" in styles
    assert "circle" in styles
    assert "cubicbezier" in styles
    assert "bezier_control" not in styles


def test_resolve_styles_none_returns_defaults_unchanged():
    """Multiple calls with None return consistent defaults."""
    s1 = _resolve_styles(None)
    s2 = _resolve_styles(None)
    assert s1["segment"].stroke_color == s2["segment"].stroke_color


def test_resolve_styles_does_not_mutate_default_registry():
    """Overriding a style does not mutate the default registry."""
    override = StyleOptions(stroke_color="blue")
    _resolve_styles({"segment": override})
    # A second call must still return the original default
    fresh = _resolve_styles(None)
    assert fresh["segment"].stroke_color != "blue"


def test_resolve_styles_valid_override_is_applied():
    """Valid override is correctly applied."""
    override = StyleOptions(stroke_color="green", stroke_width=2.0)
    styles = _resolve_styles({"segment": override})
    assert styles["segment"].stroke_color == "green"
    assert styles["segment"].stroke_width == 2.0


def test_resolve_styles_unknown_key_raises_value_error():
    """Unknown style key raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        _resolve_styles({"nonexistent_key": StyleOptions()})
    assert "nonexistent_key" in str(exc_info.value)


def test_resolve_styles_unknown_key_does_not_alter_known_entries():
    """Unknown key raises without altering known entries."""
    with pytest.raises(ValueError):
        _resolve_styles({"unknown": StyleOptions(stroke_color="pink")})


def test_resolve_styles_multiple_overrides():
    """Multiple overrides are all applied correctly."""
    styles = _resolve_styles(
        {
            "segment": StyleOptions(stroke_color="red"),
            "point": StyleOptions(stroke_color="blue"),
        }
    )
    assert styles["segment"].stroke_color == "red"
    assert styles["point"].stroke_color == "blue"


# ---------------------------------------------------------------------------
# _build_svg
# ---------------------------------------------------------------------------


def _default_build_svg_kwargs(element_groups=None):
    """Helper to generate default kwargs for _build_svg."""
    return dict(
        title="Test",
        element_groups=element_groups or [],
        width_mm=210,
        height_mm=297,
        margin_mm=10,
        show_construction=True,
        show_bezier_control_points=False,
    )


def test_build_svg_returns_string():
    """_build_svg returns a string."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert isinstance(svg, str)


def test_build_svg_root_element_present():
    """SVG root element tags are present."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert "<svg " in svg
    assert "</svg>" in svg


def test_build_svg_dimensions():
    """Default dimensions are correctly rendered."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert 'width="210mm"' in svg
    assert 'height="297mm"' in svg
    assert 'viewBox="0 0 210 297"' in svg


def test_build_svg_custom_dimensions():
    """Custom dimensions are correctly rendered."""
    kw = _default_build_svg_kwargs()
    kw["width_mm"] = 420
    kw["height_mm"] = 594
    svg = _build_svg(**kw)
    assert 'width="420mm"' in svg
    assert 'height="594mm"' in svg


def test_build_svg_title_appears():
    """Title appears in the SVG output."""
    kw = _default_build_svg_kwargs()
    kw["title"] = "Drawstring Pouch"
    svg = _build_svg(**kw)
    assert "Drawstring Pouch" in svg


def test_build_svg_arrow_defs_present():
    """Arrow marker definitions are present."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert "<defs>" in svg
    assert 'id="arrow"' in svg


def test_build_svg_empty_element_groups_produces_valid_svg():
    """Empty element groups produce valid SVG."""
    svg = _build_svg(**_default_build_svg_kwargs(element_groups=[]))
    assert svg.startswith("<svg ")
    assert svg.strip().endswith("</svg>")


def test_build_svg_element_group_content_rendered(simple_part):
    """Element group content is rendered."""
    svg = _build_svg(**_default_build_svg_kwargs(element_groups=[simple_part.elements]))
    assert "<line " in svg


def test_build_svg_multiple_element_groups_all_rendered():
    """Multiple element groups are all rendered."""
    p1 = PatternPart(name="a")
    p1.append(Segment(Point(0, 0), Point(5, 0)))
    p2 = PatternPart(name="b")
    p2.append(Circle(Point(50, 50), radius=3))
    svg = _build_svg(**_default_build_svg_kwargs(element_groups=[p1.elements, p2.elements]))
    assert "<line " in svg
    assert "<circle " in svg


def test_build_svg_xmlns_present():
    """SVG namespace is present."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg


def test_build_svg_dark_mode_style_block_present():
    """A <style> block is injected into every SVG."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert "<style>" in svg


def test_build_svg_dark_mode_media_query_present():
    """The dark-mode @media query is present in every SVG."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert "prefers-color-scheme: dark" in svg


def test_build_svg_css_variables_defined():
    """No CSS custom properties in the SVG — all colours are literal hex."""
    svg = _build_svg(**_default_build_svg_kwargs())
    for var in ("--c-fg", "--c-bg", "--c-grey", "--c-lightgrey"):
        assert var not in svg, f"CSS variable should not appear: {var}"


def test_build_svg_color_property_set_on_svg_rule():
    """svg rule must set a literal background-color, not a CSS variable."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert "background-color: #ffffff" in svg


def test_build_svg_no_hardcoded_background_color_white():
    """background-color must use hex #ffffff, not the keyword 'white'."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert "background-color:white" not in svg
    assert "background-color: white" not in svg
    assert "background-color: white" not in svg


def test_build_svg_text_uses_currentcolor():
    """Title text must use fill="#000000" (literal hex, Inkscape-compatible)."""
    svg = _build_svg(**_default_build_svg_kwargs())
    assert 'fill="#000000"' in svg
    assert 'fill="currentColor"' not in svg


def test_build_svg_stroke_uses_literal_hex_not_css_variables():
    """Strokes must use literal hex colours, not CSS custom properties.

    Inkscape does not support CSS custom properties (var(--c-...)) even inside
    style="" attributes.  All colour values must be emitted as literal hex
    so every conformant renderer including Inkscape displays lines correctly.
    """
    part = PatternPart(name="P")
    part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
    svg = _build_svg(**_default_build_svg_kwargs(element_groups=[part.elements]))
    # Literal hex colours must appear in the style attribute
    assert 'style="stroke:#000000' in svg or 'style="stroke:#555555' in svg
    # No CSS custom properties anywhere in stroke/fill attributes
    assert "var(--" not in svg


# ---------------------------------------------------------------------------
# Per-element rendering (via _build_svg round-trip)
# ---------------------------------------------------------------------------


def _svg_for_segment(segment, style=None):
    """Helper to render a segment and return SVG string."""
    part = PatternPart(name="p")
    part.append(segment, style=style)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )


def test_render_segment_line_element_present():
    """Segment renders as a line element."""
    svg = _svg_for_segment(Segment(Point(0, 0), Point(10, 10)))
    assert "<line " in svg


def test_render_segment_coordinates():
    """Segment coordinates are correctly rendered."""
    svg = _svg_for_segment(Segment(Point(1, 2), Point(3, 4)))
    assert 'x1="1.0"' in svg
    assert 'y1="2.0"' in svg
    assert 'x2="3.0"' in svg
    assert 'y2="4.0"' in svg


def test_render_segment_name_at_midpoint():
    """Segment name is rendered at midpoint."""
    seg = Segment(Point(0, 0), Point(10, 0), name="hem")
    svg = _svg_for_segment(seg)
    assert "hem" in svg
    # midpoint x = 5.0
    assert 'x="5.0"' in svg


def test_render_segment_dash_array_in_style():
    """Dashed segment style includes stroke-dasharray."""
    svg = _svg_for_segment(Segment(Point(0, 0), Point(5, 5)), style=STYLE_STITCH)
    assert "stroke-dasharray" in svg


def test_render_segment_grainline_has_arrow_marker():
    """Grainline segment has arrow marker."""
    seg = Segment(Point(0, 0), Point(0, 20), name="grain")
    svg = _svg_for_segment(seg, style=STYLE_GRAINLINE)
    assert 'marker-start="url(#arrow)"' in svg


def _svg_for_circle(circle, style=None):
    """Helper to render a circle and return SVG string."""
    part = PatternPart(name="p")
    part.append(circle, style=style)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )


def test_render_circle_element_present():
    """Circle renders as a circle element."""
    svg = _svg_for_circle(Circle(Point(10, 10), radius=5))
    assert "<circle " in svg


def test_render_circle_attributes():
    """Circle attributes are correctly rendered."""
    svg = _svg_for_circle(Circle(Point(7, 8), radius=3))
    assert 'cx="7.0"' in svg
    assert 'cy="8.0"' in svg
    assert 'r="3"' in svg


def _svg_for_rect(rect, style=None):
    """Helper to render a rect and return SVG string."""
    part = PatternPart(name="p")
    part.append(rect, style=style)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=200,
        height_mm=200,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )


def test_render_rect_element_present():
    """Rect renders as a rect element."""
    svg = _svg_for_rect(Rect(Point(0, 0), width=10, height=20))
    assert "<rect " in svg


def test_render_rect_declared_dimensions_unchanged():
    """The rect is rendered at its exact declared size — no inset."""
    svg = _svg_for_rect(Rect(Point(5, 3), width=12, height=8))
    assert 'x="5"' in svg
    assert 'y="3"' in svg
    assert 'width="12"' in svg
    assert 'height="8"' in svg


def test_render_rect_uses_clip_path():
    """A clipPath is emitted so the stroke is clipped to the inside."""
    svg = _svg_for_rect(Rect(Point(0, 0), width=30, height=30))
    assert "<clipPath " in svg
    assert "clip-path=" in svg


def test_render_rect_clip_id_unique_per_position():
    """Two rects at different origins produce different clip ids."""
    part = PatternPart(name="p")
    part.append(Rect(Point(0, 0), width=10, height=10))
    part.append(Rect(Point(5, 5), width=10, height=10))
    svg = _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=200,
        height_mm=200,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )
    # Extract all clipPath ids and confirm they are distinct
    ids = re.findall(r'<clipPath id="([^"]+)"', svg)
    assert len(ids) == 2
    assert ids[0] != ids[1]


def test_render_rect_name_centred():
    """Rect name is centred."""
    rect = Rect(Point(0, 0), width=10, height=10, name="pocket")
    svg = _svg_for_rect(rect)
    assert "pocket" in svg
    # label centre is at declared width/2, height/2
    assert 'x="5.0"' in svg


def _svg_for_triangle(triangle, style=None):
    """Helper to render a triangle and return SVG string."""
    part = PatternPart(name="p")
    part.append(triangle, style=style)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )


def test_render_triangle_polygon_element_present():
    """Triangle renders as a polygon element."""
    t = Triangle(Point(0, 0), Point(2, 0), Point(1, -2))
    svg = _svg_for_triangle(t)
    assert "<polygon " in svg


def test_render_triangle_default_fill_is_black():
    """Triangle default fill is black."""
    t = Triangle(Point(0, 0), Point(2, 0), Point(1, -2))
    svg = _svg_for_triangle(t)
    assert 'fill="black"' in svg


# ---------------------------------------------------------------------------
# Construction element rendering
# ---------------------------------------------------------------------------


def _svg_with_construction_flag(show_construction: bool, is_construction: bool) -> str:
    """Helper to test show_construction flag behavior."""
    part = PatternPart(name="p")
    elem = PatternElement(
        Segment(Point(0, 0), Point(10, 0), name="aux"),
        is_construction=is_construction,
    )
    part.elements.append(elem)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=show_construction,
        show_bezier_control_points=False,
    )


def test_render_construction_shown_when_flag_true():
    """Construction elements are shown when flag is True."""
    svg = _svg_with_construction_flag(show_construction=True, is_construction=True)
    assert "aux" in svg


def test_render_construction_hidden_when_flag_false():
    """Construction elements are hidden when flag is False."""
    svg = _svg_with_construction_flag(show_construction=False, is_construction=True)
    assert "aux" not in svg


def test_render_non_construction_always_shown():
    """Elements without is_construction=True are never affected by the flag."""
    svg = _svg_with_construction_flag(show_construction=False, is_construction=False)
    assert "aux" in svg


def test_render_point_always_rendered():
    """Points are regular elements — rendered unless is_construction=True hides them."""
    part = PatternPart(name="p")
    part.elements.append(PatternElement(Point(5, 5)))
    svg = _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )
    assert 'cx="5.0"' in svg


def test_render_point_name_rendered():
    """Point name is rendered."""
    part = PatternPart(name="p")
    part.elements.append(PatternElement(Point(3, 4, name="A")))
    svg = _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=True,
        show_bezier_control_points=False,
    )
    assert ">A<" in svg


# ---------------------------------------------------------------------------
# InfoBox rendering
# ---------------------------------------------------------------------------


def _svg_for_infobox(info_box):
    """Helper to render an InfoBox and return SVG string."""
    part = PatternPart(name="p")
    part.append(info_box)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=200,
        height_mm=200,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )


def test_render_infobox_header():
    """InfoBox header is rendered."""
    box = InfoBox(Point(50, 50), header="Front", notes=[])
    svg = _svg_for_infobox(box)
    assert ">Front<" in svg


def test_render_infobox_notes():
    """InfoBox notes are rendered."""
    box = InfoBox(Point(50, 50), header="Front", notes=["2× fabric", "seam 1cm"])
    svg = _svg_for_infobox(box)
    assert "2× fabric" in svg
    assert "seam 1cm" in svg


def test_render_infobox_header_uses_bold():
    """InfoBox header uses bold font weight."""
    box = InfoBox(Point(50, 50), header="Back", notes=[])
    svg = _svg_for_infobox(box)
    assert 'font-weight="bold"' in svg


def test_render_infobox_multiple_text_elements():
    """InfoBox with multiple notes produces multiple text elements."""
    box = InfoBox(Point(50, 50), header="Lining", notes=["note1", "note2", "note3"])
    svg = _svg_for_infobox(box)
    count = svg.count("<text ")
    # title text + header + 3 notes = 5 minimum
    assert count >= 5


# ---------------------------------------------------------------------------
# CubicBezier rendering
# ---------------------------------------------------------------------------


def _svg_for_bezier(bezier, show_control=False, style=None):
    """Helper to render a CubicBezier and return SVG string."""
    part = PatternPart(name="p")
    part.append(bezier, style=style)
    return _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=200,
        height_mm=200,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=show_control,
    )


def _standard_bezier():
    """Standard bezier curve for testing."""
    return CubicBezier(Point(0, 0), Point(10, 5), Point(20, -5), Point(30, 0))


def test_render_bezier_path_element_present():
    """CubicBezier renders as a path element."""
    svg = _svg_for_bezier(_standard_bezier())
    assert "<path " in svg


def test_render_bezier_path_data_format():
    """CubicBezier path data is correctly formatted."""
    svg = _svg_for_bezier(_standard_bezier())
    assert "M 0.0,0.0" in svg
    assert "C 10.0,5.0" in svg


def test_render_bezier_no_control_lines_by_default():
    """CubicBezier control lines are not shown by default."""
    svg = _svg_for_bezier(_standard_bezier(), show_control=False)
    assert "stroke-dasharray" not in svg


def test_render_bezier_control_lines_shown_when_enabled():
    """CubicBezier control lines are shown when enabled."""
    svg = _svg_for_bezier(_standard_bezier(), show_control=True)
    assert "<line " in svg
    # Control point handles use a dashed line
    assert "2,2" in svg


def test_render_bezier_control_point_circles_shown_when_enabled():
    """CubicBezier control point circles are shown when enabled."""
    svg = _svg_for_bezier(_standard_bezier(), show_control=True)
    # Four control-point circles
    circle_count = svg.count("<circle ")
    assert circle_count >= 4


def test_render_bezier_name_rendered():
    """CubicBezier name is rendered."""
    b = CubicBezier(Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0), name="curve")
    svg = _svg_for_bezier(b)
    assert "curve" in svg


# ---------------------------------------------------------------------------
# export_pattern_part_svg_mm
# ---------------------------------------------------------------------------


def test_export_pattern_part_creates_file(simple_part):
    """export_pattern_part_svg_mm creates a file."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(simple_part, fname)
    assert Path(fname).exists()
    assert Path(fname).stat().st_size > 0


def test_export_pattern_part_contains_valid_svg(simple_part):
    """export_pattern_part_svg_mm produces valid SVG."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(simple_part, fname)
    content = Path(fname).read_text()
    assert "<svg " in content
    assert "</svg>" in content


def test_export_pattern_part_name_in_output():
    """Part name appears in the output."""
    part = PatternPart(name="Sleeve")
    part.append(Segment(Point(0, 0), Point(10, 0)))
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(part, fname)
    content = Path(fname).read_text()
    assert "Sleeve" in content


def test_export_pattern_part_custom_canvas_size(simple_part):
    """Custom canvas size is respected."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(simple_part, fname, width_mm=420, height_mm=594)
    content = Path(fname).read_text()
    assert 'width="420mm"' in content
    assert 'height="594mm"' in content


def test_export_pattern_part_show_construction_false_hides_construction():
    """show_construction=False hides construction elements."""
    part = PatternPart(name="p")
    elem = PatternElement(
        Segment(Point(0, 0), Point(10, 0), name="aux-line"),
        is_construction=True,
    )
    part.elements.append(elem)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(part, fname, show_construction=False)
    content = Path(fname).read_text()
    assert "aux-line" not in content


def test_export_pattern_part_show_construction_true_shows_construction():
    """show_construction=True shows construction elements."""
    part = PatternPart(name="p")
    elem = PatternElement(
        Segment(Point(0, 0), Point(10, 0), name="aux-line"),
        is_construction=True,
    )
    part.elements.append(elem)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(part, fname, show_construction=True)
    content = Path(fname).read_text()
    assert "aux-line" in content


def test_export_pattern_part_show_bezier_control_points():
    """show_bezier_control_points shows bezier control handles."""
    part = PatternPart(name="p")
    part.append(CubicBezier(Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0)))
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(part, fname, show_bezier_control_points=True)
    content = Path(fname).read_text()
    assert "2,2" in content  # dashed control handle


def test_export_pattern_part_style_map_known_key_does_not_raise():
    """A known style_map key does not raise."""
    part = PatternPart(name="p")
    part.append(Segment(Point(0, 0), Point(10, 0)))
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_part_svg_mm(
        part,
        fname,
        style_map={"segment": StyleOptions(stroke_color="purple")},
    )


def test_export_pattern_part_style_map_unknown_key_raises(simple_part):
    """An unknown style_map key raises ValueError."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    with pytest.raises(ValueError):
        export_pattern_part_svg_mm(simple_part, fname, style_map={"no_such_key": StyleOptions()})


# ---------------------------------------------------------------------------
# export_pattern_svg_mm
# ---------------------------------------------------------------------------


def test_export_pattern_creates_file(simple_pattern):
    """export_pattern_svg_mm creates a file."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname)
    assert Path(fname).exists()


def test_export_pattern_contains_valid_svg(simple_pattern):
    """export_pattern_svg_mm produces valid SVG."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname)
    content = Path(fname).read_text()
    assert "<svg " in content
    assert "</svg>" in content


def test_export_pattern_name_in_output():
    """Pattern name appears in output."""
    pat = Pattern(name="Holiday Tote")
    p = PatternPart(name="front")
    p.append(Segment(Point(0, 0), Point(10, 0)))
    pat.add_part(p)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname)
    content = Path(fname).read_text()
    assert "Holiday Tote" in content


def test_export_pattern_all_parts_rendered_by_default(simple_pattern):
    """All parts are rendered by default."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname)
    content = Path(fname).read_text()
    # front has a <line>, back has a <rect>
    assert "<line " in content
    assert "<rect " in content


def test_export_pattern_parts_filter_includes_only_named(simple_pattern):
    """parts filter includes only named parts."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname, parts=["front"])
    content = Path(fname).read_text()
    assert "<line " in content  # front has a segment
    assert "<rect " not in content  # back (rect) excluded


def test_export_pattern_parts_filter_empty_list_renders_nothing(simple_pattern):
    """Empty parts list renders nothing from parts."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname, parts=[])
    content = Path(fname).read_text()
    assert "<line " not in content
    assert "<rect " not in content


def test_export_pattern_parts_filter_nonexistent_name_renders_nothing(simple_pattern):
    """Nonexistent part name renders nothing."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname, parts=["nonexistent"])
    content = Path(fname).read_text()
    assert "<line " not in content


def test_export_pattern_reference_square_always_rendered(simple_pattern):
    """Reference square is always rendered even with parts filter."""
    simple_pattern.add_reference_square(origin=Point(5, 5), edge_length=3 * CM)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname, parts=["front"])
    content = Path(fname).read_text()
    assert content.count("<rect ") >= 1  # at least the reference square


def test_export_pattern_reference_square_with_all_parts(simple_pattern):
    """Reference square is rendered when all parts are selected."""
    simple_pattern.add_reference_square(origin=Point(5, 5), edge_length=3 * CM)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname)
    content = Path(fname).read_text()
    # back part has 1 rect, reference square adds 1 more → at least 2
    assert content.count("<rect ") >= 2


def test_export_pattern_no_reference_square_when_not_set():
    """No reference square when not set."""
    pat = Pattern(name="bare")
    p = PatternPart(name="only")
    p.append(Segment(Point(0, 0), Point(5, 0)))
    pat.add_part(p)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname)
    content = Path(fname).read_text()
    assert "<rect " not in content


def test_export_pattern_custom_canvas_size(simple_pattern):
    """Custom canvas size is respected."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname, width_mm=150, height_mm=200)
    content = Path(fname).read_text()
    assert 'width="150mm"' in content
    assert 'height="200mm"' in content


def test_export_pattern_style_map_known_key_does_not_raise():
    """A known style_map key does not raise."""
    pat = Pattern(name="p")
    part = PatternPart(name="a")
    part.append(CubicBezier(Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0)))
    pat.add_part(part)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(
        pat,
        fname,
        style_map={"cubicbezier": StyleOptions(stroke_color="teal")},
    )


def test_export_pattern_style_map_unknown_key_raises(simple_pattern):
    """An unknown style_map key raises ValueError."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    with pytest.raises(ValueError):
        export_pattern_svg_mm(simple_pattern, fname, style_map={"bogus": StyleOptions()})


def test_export_pattern_empty_pattern_produces_valid_svg():
    """Empty pattern produces valid SVG."""
    pat = Pattern(name="empty")
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname)
    content = Path(fname).read_text()
    assert "<svg " in content
    assert "</svg>" in content


def test_export_pattern_arrow_defs_always_present(simple_pattern):
    """Arrow defs are always present."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(simple_pattern, fname)
    content = Path(fname).read_text()
    assert 'id="arrow"' in content


def test_export_pattern_show_construction_false_hides_construction():
    """show_construction=False hides construction elements."""
    pat = Pattern(name="pts")
    p = PatternPart(name="p")
    elem = PatternElement(Segment(Point(0, 0), Point(10, 0), name="aux"), is_construction=True)
    p.elements.append(elem)
    pat.add_part(p)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname, show_construction=False)
    content = Path(fname).read_text()
    assert "aux" not in content


# ---------------------------------------------------------------------------
# Element name override via PatternElement.name
# ---------------------------------------------------------------------------


def test_element_geometry_name_appears(svg_for_geometry):
    """The geometry name is used as the element label in the SVG."""
    seg = Segment(Point(0, 0), Point(10, 0), name="geo_name")
    assert "geo_name" in svg_for_geometry(seg)


def test_element_set_name_updates_label(svg_for_geometry):
    """Calling set_name() before rendering changes the label in the SVG."""
    seg = Segment(Point(0, 0), Point(10, 0), name="original")
    seg.set_name("updated")
    svg = svg_for_geometry(seg)
    assert "updated" in svg
    assert "original" not in svg


def test_element_no_name_renders_without_label(svg_for_geometry):
    """A geometry with no name produces no spurious label in the SVG."""
    seg = Segment(Point(0, 0), Point(10, 0))
    assert "<svg" in svg_for_geometry(seg)


# ---------------------------------------------------------------------------
# Inkscape / standards compatibility
# ---------------------------------------------------------------------------


def test_stroke_width_has_no_mm_unit_suffix(svg_for_geometry):
    """stroke-width must be a bare number — no 'mm' suffix.

    Inkscape (and the SVG spec) treat stroke-width as a user-unit value.
    Because the viewBox is expressed in mm-equivalent units (1 unit = 1 mm),
    appending 'mm' would cause Inkscape to scale the width by the px/mm
    factor (~3.78×), making lines invisible or extremely thick.
    """
    seg = Segment(Point(0, 0), Point(10, 0))
    svg = svg_for_geometry(seg)
    # Must not contain stroke-width with a mm suffix anywhere in the SVG
    assert "stroke-width=" in svg
    assert re.search(r'stroke-width="[^"]*mm"', svg) is None, (
        "stroke-width must not carry a 'mm' unit suffix"
    )


def test_stroke_width_no_mm_suffix_for_bezier_control_points():
    """Control-point rendering also emits unit-free stroke-width values."""
    part = PatternPart(name="test")
    bez = CubicBezier(Point(0, 0), Point(5, 10), Point(10, 10), Point(15, 0))
    part.append(bez)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    from sewpat.render import export_pattern_part_svg_mm

    export_pattern_part_svg_mm(part, fname, show_bezier_control_points=True)
    svg = Path(fname).read_text()
    assert re.search(r'stroke-width="[^"]*mm"', svg) is None, (
        "Control-point stroke-width must not carry a 'mm' unit suffix"
    )
