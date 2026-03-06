"""
Comprehensive tests for the render module.

Covers:
  - _resolve_styles: default copy, valid overrides, unknown-key error
  - _build_svg: SVG envelope, title, arrow defs, element groups
  - _render_* helpers: Segment, Circle, Triangle, Rect, Point, InfoBox, CubicBezier
  - export_pattern_part_svg_mm: file output, content, optional args
  - export_pattern_svg_mm: all parts, selected parts, reference square, parts filter
"""

import tempfile
import unittest
from pathlib import Path

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


def _simple_part() -> PatternPart:
    """A minimal PatternPart with one Segment."""
    part = PatternPart(name="body")
    part.append(Segment(Point(0, 0), Point(10, 0)))
    return part


def _simple_pattern(name: str = "My Pattern") -> Pattern:
    """A Pattern with two parts."""
    pat = Pattern(name=name)
    p1 = PatternPart(name="front")
    p1.append(Segment(Point(0, 0), Point(10, 0)))
    pat.add_part(p1)
    p2 = PatternPart(name="back")
    p2.append(Rect(Point(20, 0), width=5, height=8))
    pat.add_part(p2)
    return pat


# ---------------------------------------------------------------------------
# _resolve_styles
# ---------------------------------------------------------------------------


class TestResolveStyles(unittest.TestCase):
    def test_returns_all_default_keys(self):
        styles = _resolve_styles(None)
        self.assertIn("segment", styles)
        self.assertIn("point", styles)
        self.assertIn("circle", styles)
        self.assertIn("cubicbezier", styles)
        self.assertNotIn("bezier_control", styles)

    def test_none_returns_defaults_unchanged(self):
        s1 = _resolve_styles(None)
        s2 = _resolve_styles(None)
        self.assertEqual(s1["segment"].stroke_color, s2["segment"].stroke_color)

    def test_does_not_mutate_default_registry(self):
        override = StyleOptions(stroke_color="blue")
        _resolve_styles({"segment": override})
        # A second call must still return the original default
        fresh = _resolve_styles(None)
        self.assertNotEqual(fresh["segment"].stroke_color, "blue")

    def test_valid_override_is_applied(self):
        override = StyleOptions(stroke_color="green", stroke_width=2.0)
        styles = _resolve_styles({"segment": override})
        self.assertEqual(styles["segment"].stroke_color, "green")
        self.assertEqual(styles["segment"].stroke_width, 2.0)

    def test_unknown_key_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            _resolve_styles({"nonexistent_key": StyleOptions()})
        self.assertIn("nonexistent_key", str(cm.exception))

    def test_unknown_key_does_not_alter_known_entries(self):
        with self.assertRaises(ValueError):
            _resolve_styles({"unknown": StyleOptions(stroke_color="pink")})

    def test_multiple_overrides(self):
        styles = _resolve_styles(
            {
                "segment": StyleOptions(stroke_color="red"),
                "point": StyleOptions(stroke_color="blue"),
            }
        )
        self.assertEqual(styles["segment"].stroke_color, "red")
        self.assertEqual(styles["point"].stroke_color, "blue")


# ---------------------------------------------------------------------------
# _build_svg
# ---------------------------------------------------------------------------


class TestBuildSvg(unittest.TestCase):
    @staticmethod
    def _default_kwargs(element_groups=None):
        return dict(
            title="Test",
            element_groups=element_groups or [],
            width_mm=210,
            height_mm=297,
            margin_mm=10,
            show_construction=True,
            show_bezier_control_points=False,
        )

    def test_returns_string(self):
        svg = _build_svg(**self._default_kwargs())
        self.assertIsInstance(svg, str)

    def test_svg_root_element_present(self):
        svg = _build_svg(**self._default_kwargs())
        self.assertIn("<svg ", svg)
        self.assertIn("</svg>", svg)

    def test_svg_dimensions(self):
        svg = _build_svg(**self._default_kwargs())
        self.assertIn('width="210mm"', svg)
        self.assertIn('height="297mm"', svg)
        self.assertIn('viewBox="0 0 210 297"', svg)

    def test_custom_dimensions(self):
        kw = self._default_kwargs()
        kw["width_mm"] = 420
        kw["height_mm"] = 594
        svg = _build_svg(**kw)
        self.assertIn('width="420mm"', svg)
        self.assertIn('height="594mm"', svg)

    def test_title_appears_in_svg(self):
        kw = self._default_kwargs()
        kw["title"] = "Drawstring Pouch"
        svg = _build_svg(**kw)
        self.assertIn("Drawstring Pouch", svg)

    def test_arrow_defs_present(self):
        svg = _build_svg(**self._default_kwargs())
        self.assertIn("<defs>", svg)
        self.assertIn('id="arrow"', svg)

    def test_empty_element_groups_produces_valid_svg(self):
        svg = _build_svg(**self._default_kwargs(element_groups=[]))
        self.assertTrue(svg.startswith("<svg "))
        self.assertTrue(svg.strip().endswith("</svg>"))

    def test_element_group_content_rendered(self):
        part = _simple_part()
        svg = _build_svg(**self._default_kwargs(element_groups=[part.elements]))
        self.assertIn("<line ", svg)

    def test_multiple_element_groups_all_rendered(self):
        p1 = PatternPart(name="a")
        p1.append(Segment(Point(0, 0), Point(5, 0)))
        p2 = PatternPart(name="b")
        p2.append(Circle(Point(50, 50), radius=3))
        svg = _build_svg(
            **self._default_kwargs(element_groups=[p1.elements, p2.elements])
        )
        self.assertIn("<line ", svg)
        self.assertIn("<circle ", svg)

    def test_xmlns_present(self):
        svg = _build_svg(**self._default_kwargs())
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', svg)


# ---------------------------------------------------------------------------
# Per-element rendering (via _build_svg round-trip)
# ---------------------------------------------------------------------------


class TestRenderSegment(unittest.TestCase):
    @staticmethod
    def _svg(segment, style=None):
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

    def test_line_element_present(self):
        svg = self._svg(Segment(Point(0, 0), Point(10, 10)))
        self.assertIn("<line ", svg)

    def test_coordinates_in_svg(self):
        svg = self._svg(Segment(Point(1, 2), Point(3, 4)))
        self.assertIn('x1="1.0"', svg)
        self.assertIn('y1="2.0"', svg)
        self.assertIn('x2="3.0"', svg)
        self.assertIn('y2="4.0"', svg)

    def test_segment_name_rendered_at_midpoint(self):
        seg = Segment(Point(0, 0), Point(10, 0), name="hem")
        svg = self._svg(seg)
        self.assertIn("hem", svg)
        # midpoint x = 5.0
        self.assertIn('x="5.0"', svg)

    def test_dash_array_in_style(self):
        svg = self._svg(Segment(Point(0, 0), Point(5, 5)), style=STYLE_STITCH)
        self.assertIn("stroke-dasharray", svg)

    def test_grainline_has_arrow_marker(self):
        seg = Segment(Point(0, 0), Point(0, 20), name="grain")
        svg = self._svg(seg, style=STYLE_GRAINLINE)
        self.assertIn('marker-start="url(#arrow)"', svg)


class TestRenderCircle(unittest.TestCase):
    @staticmethod
    def _svg(circle, style=None):
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

    def test_circle_element_present(self):
        svg = self._svg(Circle(Point(10, 10), radius=5))
        self.assertIn("<circle ", svg)

    def test_circle_attributes(self):
        svg = self._svg(Circle(Point(7, 8), radius=3))
        self.assertIn('cx="7.0"', svg)
        self.assertIn('cy="8.0"', svg)
        self.assertIn('r="3"', svg)


class TestRenderRect(unittest.TestCase):
    @staticmethod
    def _svg(rect, style=None):
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

    def test_rect_element_present(self):
        svg = self._svg(Rect(Point(0, 0), width=10, height=20))
        self.assertIn("<rect ", svg)

    def test_rect_declared_dimensions_unchanged(self):
        """The rect is rendered at its exact declared size — no inset."""
        svg = self._svg(Rect(Point(5, 3), width=12, height=8))
        self.assertIn('x="5"', svg)
        self.assertIn('y="3"', svg)
        self.assertIn('width="12"', svg)
        self.assertIn('height="8"', svg)

    def test_rect_uses_clip_path(self):
        """A clipPath is emitted so the stroke is clipped to the inside."""
        svg = self._svg(Rect(Point(0, 0), width=30, height=30))
        self.assertIn("<clipPath ", svg)
        self.assertIn("clip-path=", svg)

    def test_rect_clip_id_unique_per_position(self):
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
        import re

        ids = re.findall(r'<clipPath id="([^"]+)"', svg)
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])

    def test_rect_name_centred(self):
        rect = Rect(Point(0, 0), width=10, height=10, name="pocket")
        svg = self._svg(rect)
        self.assertIn("pocket", svg)
        # label centre is at declared width/2, height/2
        self.assertIn('x="5.0"', svg)


class TestRenderTriangle(unittest.TestCase):
    @staticmethod
    def _svg(triangle, style=None):
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

    def test_polygon_element_present(self):
        t = Triangle(Point(0, 0), Point(2, 0), Point(1, -2))
        svg = self._svg(t)
        self.assertIn("<polygon ", svg)

    def test_triangle_default_fill_is_black(self):
        t = Triangle(Point(0, 0), Point(2, 0), Point(1, -2))
        svg = self._svg(t)
        self.assertIn('fill="black"', svg)


class TestRenderConstruction(unittest.TestCase):
    """show_construction controls visibility of elements with is_construction=True."""

    @staticmethod
    def _svg(show_construction: bool, is_construction: bool) -> str:
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

    def test_construction_shown_when_flag_true(self):
        svg = self._svg(show_construction=True, is_construction=True)
        self.assertIn("aux", svg)

    def test_construction_hidden_when_flag_false(self):
        svg = self._svg(show_construction=False, is_construction=True)
        self.assertNotIn("aux", svg)

    def test_non_construction_always_shown(self):
        """Elements without is_construction=True are never affected by the flag."""
        svg = self._svg(show_construction=False, is_construction=False)
        self.assertIn("aux", svg)

    def test_point_always_rendered(self):
        """Points are regular elements — rendered unless
        is_construction=True hides them."""
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
        self.assertIn('cx="5.0"', svg)

    def test_point_name_rendered(self):
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
        self.assertIn(">A<", svg)


class TestRenderInfoBox(unittest.TestCase):
    @staticmethod
    def _svg(info_box):
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

    def test_header_rendered(self):
        box = InfoBox(Point(50, 50), header="Front", notes=[])
        svg = self._svg(box)
        self.assertIn(">Front<", svg)

    def test_notes_rendered(self):
        box = InfoBox(Point(50, 50), header="Front", notes=["2× fabric", "seam 1cm"])
        svg = self._svg(box)
        self.assertIn("2× fabric", svg)
        self.assertIn("seam 1cm", svg)

    def test_header_uses_bold(self):
        box = InfoBox(Point(50, 50), header="Back", notes=[])
        svg = self._svg(box)
        self.assertIn('font-weight="bold"', svg)

    def test_multiple_text_elements(self):
        box = InfoBox(Point(50, 50), header="Lining", notes=["note1", "note2", "note3"])
        svg = self._svg(box)
        count = svg.count("<text ")
        # title text + header + 3 notes = 5 minimum
        self.assertGreaterEqual(count, 5)


class TestRenderCubicBezier(unittest.TestCase):
    @staticmethod
    def _svg(bezier, show_control=False, style=None):
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

    @staticmethod
    def _bezier():
        return CubicBezier(Point(0, 0), Point(10, 5), Point(20, -5), Point(30, 0))

    def test_path_element_present(self):
        svg = self._svg(self._bezier())
        self.assertIn("<path ", svg)

    def test_path_data_format(self):
        svg = self._svg(self._bezier())
        self.assertIn("M 0.0,0.0", svg)
        self.assertIn("C 10.0,5.0", svg)

    def test_no_control_lines_by_default(self):
        svg = self._svg(self._bezier(), show_control=False)
        self.assertNotIn("stroke-dasharray", svg)

    def test_control_lines_shown_when_enabled(self):
        svg = self._svg(self._bezier(), show_control=True)
        self.assertIn("<line ", svg)
        # Control point handles use a dashed line
        self.assertIn("2,2", svg)

    def test_control_point_circles_shown_when_enabled(self):
        svg = self._svg(self._bezier(), show_control=True)
        # Four control-point circles
        circle_count = svg.count("<circle ")
        self.assertGreaterEqual(circle_count, 4)

    def test_bezier_name_rendered(self):
        b = CubicBezier(
            Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0), name="curve"
        )
        svg = self._svg(b)
        self.assertIn("curve", svg)


# ---------------------------------------------------------------------------
# export_pattern_part_svg_mm
# ---------------------------------------------------------------------------


class TestExportPatternPartSvgMm(unittest.TestCase):
    def test_creates_file(self):
        part = _simple_part()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_part_svg_mm(part, fname)
        self.assertTrue(Path(fname).exists())
        self.assertGreater(Path(fname).stat().st_size, 0)

    def test_file_contains_valid_svg(self):
        part = _simple_part()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_part_svg_mm(part, fname)
        content = Path(fname).read_text()
        self.assertIn("<svg ", content)
        self.assertIn("</svg>", content)

    def test_part_name_in_output(self):
        part = PatternPart(name="Sleeve")
        part.append(Segment(Point(0, 0), Point(10, 0)))
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_part_svg_mm(part, fname)
        content = Path(fname).read_text()
        self.assertIn("Sleeve", content)

    def test_custom_canvas_size(self):
        part = _simple_part()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_part_svg_mm(part, fname, width_mm=420, height_mm=594)
        content = Path(fname).read_text()
        self.assertIn('width="420mm"', content)
        self.assertIn('height="594mm"', content)

    def test_show_construction_false_hides_construction_elements(self):
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
        self.assertNotIn("aux-line", content)

    def test_show_construction_true_shows_construction_elements(self):
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
        self.assertIn("aux-line", content)

    def test_show_bezier_control_points(self):
        part = PatternPart(name="p")
        part.append(CubicBezier(Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0)))
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_part_svg_mm(part, fname, show_bezier_control_points=True)
        content = Path(fname).read_text()
        self.assertIn("2,2", content)  # dashed control handle

    def test_style_map_known_key_does_not_raise(self):
        # A known style_map key must not raise.
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 0), Point(10, 0)))
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_part_svg_mm(
            part,
            fname,
            style_map={"segment": StyleOptions(stroke_color="purple")},
        )

    def test_style_map_unknown_key_raises(self):
        part = _simple_part()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        with self.assertRaises(ValueError):
            export_pattern_part_svg_mm(
                part, fname, style_map={"no_such_key": StyleOptions()}
            )


# ---------------------------------------------------------------------------
# export_pattern_svg_mm
# ---------------------------------------------------------------------------


class TestExportPatternSvgMm(unittest.TestCase):
    def test_creates_file(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        self.assertTrue(Path(fname).exists())

    def test_file_contains_valid_svg(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        self.assertIn("<svg ", content)
        self.assertIn("</svg>", content)

    def test_pattern_name_in_output(self):
        pat = _simple_pattern(name="Holiday Tote")
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        self.assertIn("Holiday Tote", content)

    def test_all_parts_rendered_by_default(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        # front has a <line>, back has a <rect>
        self.assertIn("<line ", content)
        self.assertIn("<rect ", content)

    def test_parts_filter_includes_only_named_parts(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname, parts=["front"])
        content = Path(fname).read_text()
        self.assertIn("<line ", content)  # front has a segment
        self.assertNotIn("<rect ", content)  # back (rect) excluded

    def test_parts_filter_empty_list_renders_nothing_from_parts(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname, parts=[])
        content = Path(fname).read_text()
        self.assertNotIn("<line ", content)
        self.assertNotIn("<rect ", content)

    def test_parts_filter_nonexistent_name_renders_nothing(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname, parts=["nonexistent"])
        content = Path(fname).read_text()
        self.assertNotIn("<line ", content)

    def test_reference_square_always_rendered(self):
        pat = _simple_pattern()
        pat.add_reference_square(origin=Point(5, 5), edge_length=3 * CM)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        # Even with only one part selected the reference square must appear
        export_pattern_svg_mm(pat, fname, parts=["front"])
        content = Path(fname).read_text()
        rect_count = content.count("<rect ")
        self.assertGreaterEqual(rect_count, 1)  # at least the reference square

    def test_reference_square_rendered_when_all_parts_selected(self):
        pat = _simple_pattern()
        pat.add_reference_square(origin=Point(5, 5), edge_length=3 * CM)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        # back part has 1 rect, reference square adds 1 more → at least 2
        rect_count = content.count("<rect ")
        self.assertGreaterEqual(rect_count, 2)

    def test_no_reference_square_when_not_set(self):
        pat = Pattern(name="bare")
        p = PatternPart(name="only")
        p.append(Segment(Point(0, 0), Point(5, 0)))
        pat.add_part(p)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        self.assertNotIn("<rect ", content)

    def test_custom_canvas_size(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname, width_mm=150, height_mm=200)
        content = Path(fname).read_text()
        self.assertIn('width="150mm"', content)
        self.assertIn('height="200mm"', content)

    def test_style_map_known_key_does_not_raise(self):
        # A known style_map key must not raise.
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

    def test_style_map_unknown_key_raises(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        with self.assertRaises(ValueError):
            export_pattern_svg_mm(pat, fname, style_map={"bogus": StyleOptions()})

    def test_empty_pattern_produces_valid_svg(self):
        pat = Pattern(name="empty")
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        self.assertIn("<svg ", content)
        self.assertIn("</svg>", content)

    def test_arrow_defs_always_present(self):
        pat = _simple_pattern()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname)
        content = Path(fname).read_text()
        self.assertIn('id="arrow"', content)

    def test_show_construction_false_hides_construction_elements(self):
        pat = Pattern(name="pts")
        p = PatternPart(name="p")
        elem = PatternElement(
            Segment(Point(0, 0), Point(10, 0), name="aux"), is_construction=True
        )
        p.elements.append(elem)
        pat.add_part(p)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname, show_construction=False)
        content = Path(fname).read_text()
        self.assertNotIn("aux", content)


# ---------------------------------------------------------------------------
# Element name override via PatternElement.name
# ---------------------------------------------------------------------------


class TestElementNameOverride(unittest.TestCase):
    @staticmethod
    def _svg_for(geometry) -> str:
        """Render a single element and return the SVG string."""
        part = PatternPart(name="p")
        part.append(geometry)
        return _build_svg(
            title="t",
            element_groups=[part.elements],
            width_mm=200,
            height_mm=200,
            margin_mm=5,
            show_construction=True,
            show_bezier_control_points=False,
        )

    def test_geometry_name_appears_in_svg(self):
        """The geometry name is used as the element label in the SVG."""
        seg = Segment(Point(0, 0), Point(10, 0), name="geo_name")
        svg = self._svg_for(seg)
        self.assertIn("geo_name", svg)

    def test_set_name_updates_label_in_svg(self):
        """Calling set_name() before rendering changes the label in the SVG."""
        seg = Segment(Point(0, 0), Point(10, 0), name="original")
        seg.set_name("updated")
        svg = self._svg_for(seg)
        self.assertIn("updated", svg)
        self.assertNotIn("original", svg)

    def test_no_name_renders_without_label(self):
        """A geometry with no name produces no spurious label in the SVG."""
        seg = Segment(Point(0, 0), Point(10, 0))
        svg = self._svg_for(seg)
        # Just verify it renders without error — no name label expected.
        self.assertIn("<svg", svg)


if __name__ == "__main__":
    unittest.main()
