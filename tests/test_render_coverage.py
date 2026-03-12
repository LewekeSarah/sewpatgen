"""Tests that close the remaining coverage gaps in render.py.

Covers the following previously uncovered lines:
  - _render_segment: marker-start="distance" (185), marker-start=custom (187),
    marker-end="distance" (195), marker-end=custom (197),
    scissor shortening logic (204–209)
  - _geoms_to_path_data: open chain with Segment (462–479),
    mixed Segment/CubicBezier chain, closed chain (Z suffix)
  - _render_seam_allowance_chain: happy path (487–498), no-geoms guard (490–491)
  - _render_elements: SA element collection (542–545),
    Point setattr try/except (566–567, 572–573), SA-chain flush (577)
  - _build_svg: show_seam_allowance=False branch (642)
"""

from typing import Any

from sewpat.element import PatternElement
from sewpat.geometry import CubicBezier, Point, Segment
from sewpat.pattern import PatternPart
from sewpat.render import (
    _build_svg,
    _geoms_to_path_data,
    _render_seam_allowance_chain,
    _render_segment,
)
from sewpat.style import StyleOptions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _style(**kwargs: Any) -> dict[str, Any]:
    """Build a minimal raw style dict for direct _render_segment tests."""
    base: dict[str, Any] = {
        "stroke": "black",
        "stroke-width": 0.5,
        "stroke-linejoin": "miter",
        "stroke-miterlimit": 4,
        "fill": "none",
        "opacity": 1.0,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# _render_segment — marker-start / marker-end branches (lines 185, 187, 195, 197)
# ---------------------------------------------------------------------------


class TestRenderSegmentMarkerStart:
    """Tests for the marker-start branches in _render_segment."""

    def test_marker_start_distance(self) -> None:
        """marker-start='distance' emits the distance-start url (line 185)."""
        seg = Segment(Point(0, 0), Point(10, 0))
        sd = _style(**{"marker-start": "distance"})
        result = " ".join(_render_segment(seg, sd))
        assert 'marker-start="url(#distance-start)"' in result

    def test_marker_start_custom(self) -> None:
        """marker-start with an arbitrary value emits url(#<value>) (line 187)."""
        seg = Segment(Point(0, 0), Point(10, 0))
        sd = _style(**{"marker-start": "dot"})
        result = " ".join(_render_segment(seg, sd))
        assert 'marker-start="url(#dot)"' in result

    def test_marker_start_none_omitted(self) -> None:
        """No marker-start attribute when marker-start is not in style dict."""
        seg = Segment(Point(0, 0), Point(10, 0))
        result = " ".join(_render_segment(seg, _style()))
        assert "marker-start" not in result

    def test_marker_start_arrow_uses_arrow_id(self) -> None:
        """marker-start='arrow' emits url(#arrow) (existing branch, stays covered)."""
        seg = Segment(Point(0, 0), Point(10, 0))
        sd = _style(**{"marker-start": "arrow"})
        result = " ".join(_render_segment(seg, sd))
        assert 'marker-start="url(#arrow)"' in result


class TestRenderSegmentMarkerEnd:
    """Tests for the marker-end branches in _render_segment."""

    def test_marker_end_distance(self) -> None:
        """marker-end='distance' emits the distance-end url (line 195)."""
        seg = Segment(Point(0, 0), Point(10, 0))
        sd = _style(**{"marker-end": "distance"})
        result = " ".join(_render_segment(seg, sd))
        assert 'marker-end="url(#distance-end)"' in result

    def test_marker_end_custom(self) -> None:
        """marker-end with an arbitrary value emits url(#<value>) (line 197)."""
        seg = Segment(Point(0, 0), Point(10, 0))
        sd = _style(**{"marker-end": "stop"})
        result = " ".join(_render_segment(seg, sd))
        assert 'marker-end="url(#stop)"' in result

    def test_marker_end_none_omitted(self) -> None:
        """No marker-end attribute when marker-end is not in style dict."""
        seg = Segment(Point(0, 0), Point(10, 0))
        result = " ".join(_render_segment(seg, _style()))
        assert "marker-end" not in result

    def test_marker_end_arrow_uses_arrow_end_id(self) -> None:
        """marker-end='arrow' emits url(#arrow-end) (existing branch, stays covered)."""
        seg = Segment(Point(0, 0), Point(10, 0))
        sd = _style(**{"marker-end": "arrow"})
        result = " ".join(_render_segment(seg, sd))
        assert 'marker-end="url(#arrow-end)"' in result


# ---------------------------------------------------------------------------
# _render_segment — scissor shortening (lines 204–209)
# ---------------------------------------------------------------------------


class TestRenderSegmentScissor:
    """Tests for the scissor marker endpoint shortening in _render_segment."""

    def test_scissor_marker_shortens_endpoint(self) -> None:
        """With marker-end='scissor' the rendered x2/y2 differs from p2 (lines 204–209)."""

        p1 = Point(0, 0)
        p2 = Point(20, 0)  # horizontal segment; dy=0 so only x2 changes
        seg = Segment(p1, p2)
        sd = _style(**{"marker-end": "scissor"})
        result = " ".join(_render_segment(seg, sd))

        # The shortened x2 must be strictly less than 20
        # Extract x2 value from rendered line tag
        import re

        m = re.search(r'x2="([^"]+)"', result)
        assert m is not None, "x2 attribute not found in rendered SVG"
        x2_rendered = float(m.group(1))
        assert x2_rendered < 20.0, (
            f"Expected scissor shortening to reduce x2 below 20, got {x2_rendered}"
        )

    def test_scissor_marker_zero_length_no_crash(self) -> None:
        """Zero-length segment with scissor marker does not crash (length==0 guard)."""
        seg = Segment(Point(5, 5), Point(5, 5))
        sd = _style(**{"marker-end": "scissor"})
        result = _render_segment(seg, sd)
        assert isinstance(result, list)

    def test_non_scissor_endpoint_unchanged(self) -> None:
        """Without scissor marker the endpoint coordinates are unchanged."""
        seg = Segment(Point(0, 0), Point(20, 0))
        sd = _style()
        result = " ".join(_render_segment(seg, sd))
        assert 'x2="20.0"' in result


# ---------------------------------------------------------------------------
# _geoms_to_path_data (lines 462–479)
# ---------------------------------------------------------------------------


class TestGeomsToPathData:
    """Tests for _geoms_to_path_data."""

    def test_empty_list_returns_empty_string(self) -> None:
        """Empty geometry list returns empty string (line 462–463)."""
        assert _geoms_to_path_data([]) == ""

    def test_single_segment_moveto_and_lineto(self) -> None:
        """Single Segment produces M … L … path data (line 470–471)."""
        seg = Segment(Point(0, 0), Point(10, 5))
        data = _geoms_to_path_data([seg])
        assert data.startswith("M 0.0,0.0")
        assert "L 10.0,5.0" in data

    def test_multiple_segments_chain(self) -> None:
        """Multiple consecutive Segments form a connected path."""
        s1 = Segment(Point(0, 0), Point(10, 0))
        s2 = Segment(Point(10, 0), Point(10, 10))
        data = _geoms_to_path_data([s1, s2])
        assert "M 0.0,0.0" in data
        assert "L 10.0,0.0" in data
        assert "L 10.0,10.0" in data

    def test_cubic_bezier_produces_C_command(self) -> None:
        """A CubicBezier produces a C command (line 472–473)."""
        b = CubicBezier(Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0))
        data = _geoms_to_path_data([b])
        assert data.startswith("M 0.0,0.0")
        assert "C 5.0,5.0 15.0,5.0 20.0,0.0" in data

    def test_mixed_segment_and_bezier(self) -> None:
        """Mixed Segment + CubicBezier chain produces both L and C commands."""
        seg = Segment(Point(0, 0), Point(10, 0))
        bez = CubicBezier(Point(10, 0), Point(12, 5), Point(18, 5), Point(20, 0))
        data = _geoms_to_path_data([seg, bez])
        assert "L 10.0,0.0" in data
        assert "C 12.0,5.0 18.0,5.0 20.0,0.0" in data

    def test_closed_chain_appends_Z(self) -> None:
        """When last.end ≈ first.start, path data ends with Z (lines 475–477)."""
        # Triangle: three segments that form a closed loop
        s1 = Segment(Point(0, 0), Point(10, 0))
        s2 = Segment(Point(10, 0), Point(5, 8))
        s3 = Segment(Point(5, 8), Point(0, 0))
        data = _geoms_to_path_data([s1, s2, s3])
        assert data.endswith("Z")

    def test_open_chain_no_Z(self) -> None:
        """An open chain does NOT end with Z."""
        s1 = Segment(Point(0, 0), Point(10, 0))
        s2 = Segment(Point(10, 0), Point(10, 10))
        data = _geoms_to_path_data([s1, s2])
        assert not data.endswith("Z")


# ---------------------------------------------------------------------------
# _render_seam_allowance_chain (lines 487–498)
# ---------------------------------------------------------------------------


class TestRenderSeamAllowanceChain:
    """Tests for _render_seam_allowance_chain."""

    def _make_sa_elem(self, geom: Segment | CubicBezier) -> PatternElement:
        """Create an is_seam_allowance PatternElement."""
        elem = PatternElement(geom, is_seam_allowance=True)
        return elem

    def test_returns_one_path_for_segments(self) -> None:
        """Happy path: Segment list produces one <path> element (lines 493–498)."""
        elems = [
            self._make_sa_elem(Segment(Point(0, 0), Point(10, 0))),
            self._make_sa_elem(Segment(Point(10, 0), Point(10, 10))),
        ]
        sd = _style()
        result = _render_seam_allowance_chain(elems, sd)
        assert len(result) == 1
        assert result[0].startswith("<path ")
        assert "M 0.0,0.0" in result[0]

    def test_returns_one_path_for_bezier(self) -> None:
        """CubicBezier SA elements also produce one <path>."""
        bez = CubicBezier(Point(0, 0), Point(5, 5), Point(15, 5), Point(20, 0))
        elems = [self._make_sa_elem(bez)]
        result = _render_seam_allowance_chain(elems, _style())
        assert len(result) == 1
        assert "C " in result[0]

    def test_empty_sa_list_returns_empty(self) -> None:
        """An empty SA list returns [] (lines 490–491)."""
        result = _render_seam_allowance_chain([], _style())
        assert result == []

    def test_non_geometry_elements_filtered_out(self) -> None:
        """Elements whose geometry is not Segment/CubicBezier are silently ignored."""
        from sewpat.geometry import Circle

        elem_circle = PatternElement(Circle(Point(5, 5), radius=3), is_seam_allowance=True)
        result = _render_seam_allowance_chain([elem_circle], _style())
        # No valid geoms → empty
        assert result == []


# ---------------------------------------------------------------------------
# _render_elements: SA collection + Point setattr + SA flush  (542–545, 566–567, 572–573, 577)
# ---------------------------------------------------------------------------


class TestRenderElementsSACollectionAndFlush:
    """Tests that SA elements are collected and flushed as one path."""

    def test_sa_elements_rendered_as_single_path(self, svg_for_part) -> None:
        """is_seam_allowance elements are collected and emitted as one <path> (542–545, 577)."""
        part = PatternPart(name="test")
        sa_style = StyleOptions(stroke_color="red")
        e1 = PatternElement(
            Segment(Point(0, 0), Point(10, 0)), is_seam_allowance=True, style=sa_style
        )
        e2 = PatternElement(
            Segment(Point(10, 0), Point(10, 10)), is_seam_allowance=True, style=sa_style
        )
        part.elements.extend([e1, e2])
        svg = svg_for_part(part)
        assert "<path " in svg

    def test_sa_elements_are_not_individually_rendered(self, svg_for_part) -> None:
        """SA Segment elements are NOT individually rendered as <line> elements."""
        part = PatternPart(name="test")
        sa_style = StyleOptions(stroke_color="blue")
        e1 = PatternElement(
            Segment(Point(0, 0), Point(5, 0)), is_seam_allowance=True, style=sa_style
        )
        part.elements.append(e1)
        svg = svg_for_part(part)
        assert "<line " not in svg

    def test_sa_style_applied_to_path(self, svg_for_part) -> None:
        """The style of the first SA element is applied to the combined path."""
        part = PatternPart(name="test")
        sa_style = StyleOptions(stroke_color="magenta")
        e1 = PatternElement(
            Segment(Point(0, 0), Point(10, 0)), is_seam_allowance=True, style=sa_style
        )
        part.elements.append(e1)
        svg = svg_for_part(part)
        assert "magenta" in svg

    def test_non_sa_and_sa_mixed_renders_both_types(self, svg_for_part) -> None:
        """Normal elements render as <line> while SA elements render as <path>."""
        part = PatternPart(name="test")
        part.append(Segment(Point(0, 20), Point(20, 20)))
        e_sa = PatternElement(Segment(Point(0, 0), Point(10, 0)), is_seam_allowance=True)
        part.elements.append(e_sa)
        svg = svg_for_part(part)
        assert "<line " in svg
        assert "<path " in svg


class TestRenderElementsPointSetattr:
    """Tests that the Point setattr try/except path is exercised (lines 566–567, 572–573)."""

    def test_named_point_label_rendered(self, svg_for_part) -> None:
        """A named Point has its name rendered via the setattr path (lines 566, 572)."""
        part = PatternPart(name="test")
        pt = Point(10, 10, name="apex")
        part.elements.append(PatternElement(pt))
        svg = svg_for_part(part)
        assert "apex" in svg

    def test_unnamed_point_no_extra_label(self, svg_for_part) -> None:
        """An unnamed Point renders without crashing (setattr path with None)."""
        part = PatternPart(name="test")
        part.elements.append(PatternElement(Point(5, 5)))
        svg = svg_for_part(part)
        assert 'cx="5.0"' in svg

    def test_point_with_element_name_override(self, svg_for_part) -> None:
        """PatternElement name overrides geometry name on the rendered label."""
        part = PatternPart(name="test")
        part.elements.append(PatternElement(Point(3, 4, name="geo_name"), name="override_name"))
        svg = svg_for_part(part)
        assert "override_name" in svg


# ---------------------------------------------------------------------------
# _build_svg: show_seam_allowance=False (line 642)
# ---------------------------------------------------------------------------


class TestBuildSvgShowSeamAllowance:
    """Tests for the show_seam_allowance=False branch in _build_svg."""

    def test_show_seam_allowance_false_excludes_sa_elements(self) -> None:
        """show_seam_allowance=False: SA elements are excluded from output (line 642)."""
        import re

        def count_content_paths(svg: str) -> int:
            """Count <path d="M…"> elements outside the <defs> block."""
            svg_no_defs = re.sub(r"<defs>.*?</defs>", "", svg, flags=re.DOTALL)
            return svg_no_defs.count('<path d="M')

        part = PatternPart(name="test")
        # Normal segment
        part.append(Segment(Point(0, 20), Point(20, 20), name="outline"))
        # SA segment (is_seam_allowance=True)
        sa_elem = PatternElement(
            Segment(Point(0, 0), Point(10, 0)),
            is_seam_allowance=True,
        )
        part.elements.append(sa_elem)

        svg_no_sa = _build_svg(
            title="t",
            element_groups=[part.elements],
            width_mm=200,
            height_mm=200,
            margin_mm=5,
            show_construction=True,
            show_bezier_control_points=False,
            show_seam_allowance=False,
        )
        svg_with_sa = _build_svg(
            title="t",
            element_groups=[part.elements],
            width_mm=200,
            height_mm=200,
            margin_mm=5,
            show_construction=True,
            show_bezier_control_points=False,
            show_seam_allowance=True,
        )
        # SA hidden → no content path; SA shown → one content path
        assert count_content_paths(svg_no_sa) == 0
        assert count_content_paths(svg_with_sa) == 1
        # Normal outline is always rendered
        assert "<line " in svg_no_sa
        assert "<line " in svg_with_sa

    def test_show_seam_allowance_true_includes_sa_elements(self) -> None:
        """show_seam_allowance=True (default): SA elements ARE rendered."""
        part = PatternPart(name="test")
        sa_elem = PatternElement(
            Segment(Point(0, 0), Point(10, 0)),
            is_seam_allowance=True,
        )
        part.elements.append(sa_elem)

        svg = _build_svg(
            title="t",
            element_groups=[part.elements],
            width_mm=200,
            height_mm=200,
            margin_mm=5,
            show_construction=True,
            show_bezier_control_points=False,
            show_seam_allowance=True,
        )
        assert "<path " in svg

    def test_show_seam_allowance_false_notch_elements_excluded(self) -> None:
        """show_seam_allowance=True (default) hides is_seam_notch elements."""
        part = PatternPart(name="test")
        notch_elem = PatternElement(Segment(Point(0, 0), Point(5, 0)))
        notch_elem.is_seam_notch = True
        part.elements.append(notch_elem)

        # With show_seam_allowance=True, is_seam_notch elements are filtered
        svg = _build_svg(
            title="t",
            element_groups=[part.elements],
            width_mm=200,
            height_mm=200,
            margin_mm=5,
            show_construction=True,
            show_bezier_control_points=False,
            show_seam_allowance=True,
        )
        # Seam-notch elements are excluded when SA is shown
        assert "<line " not in svg


# ---------------------------------------------------------------------------
# Integration: Style override applied to SA chain via _render_elements
# ---------------------------------------------------------------------------


class TestStyleOverrideWithSAChain:
    """Integration test: style_map overrides apply correctly when SA elements exist."""

    def test_style_map_segment_override_does_not_affect_sa_path(self) -> None:
        """The segment style_map override does not affect the SA chain colour."""
        part = PatternPart(name="test")
        # Normal segment
        part.append(Segment(Point(0, 20), Point(20, 20)))
        # SA segment uses its own per-element style
        sa_style = StyleOptions(stroke_color="purple")
        sa_elem = PatternElement(
            Segment(Point(0, 0), Point(10, 0)), is_seam_allowance=True, style=sa_style
        )
        part.elements.append(sa_elem)

        svg = _build_svg(
            title="t",
            element_groups=[part.elements],
            width_mm=200,
            height_mm=200,
            margin_mm=5,
            show_construction=True,
            show_bezier_control_points=False,
            show_seam_allowance=True,
            styles={
                "segment": StyleOptions(stroke_color="orange"),
                "point": StyleOptions(),
                "circle": StyleOptions(),
                "cubicbezier": StyleOptions(),
            },
        )
        # SA path uses 'purple' from its own style
        assert "purple" in svg
