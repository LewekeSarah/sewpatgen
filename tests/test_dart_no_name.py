"""Regression: SVG export must not crash when dart has no name."""

import pytest
from sewpat import Dart, DartType, Point, Segment, PatternPart, Pattern, MM
from sewpat.element import PatternElement
from sewpat.style import StyleOptions
from sewpat.render import export_pattern_svg_mm


def _nameless_dart() -> Dart:
    edge = PatternElement(Segment(Point(0, 0), Point(100, 0)), style=StyleOptions())
    return Dart.from_edge_at_t(edge, t=0.5, width=20 * MM, depth=50 * MM)
    # name is intentionally omitted → None


def test_add_dart_no_name_tip_elements():
    part = PatternPart("test")
    result = part.add_dart(_nameless_dart(), notches=False, precision_tip=True)
    # Only two circles — no InfoBox when name is None
    tip_elems = [e for e in result.elements if e.role == "dart_tip"]
    assert len(tip_elems) == 2


def test_svg_export_no_name(tmp_path):
    part = PatternPart("test")
    part.add_dart(_nameless_dart(), notches=False, precision_tip=True)
    pattern = Pattern("test")
    pattern.add_part(part)
    out = tmp_path / "noname.svg"
    export_pattern_svg_mm(pattern, filename=str(out), width_mm=210, height_mm=297)
    assert out.exists()
    assert "<svg" in out.read_text()


def test_svg_export_direct_dart_no_name(tmp_path):
    """Dart constructed directly (not via factory) without a name."""
    part = PatternPart("test")
    dart = Dart(
        leg_a=Point(40, 0),
        leg_b=Point(60, 0),
        center=Point(50, 0),
        tip=Point(50, 50),
        dart_type=DartType.TRIANGLE,
        # name omitted
    )
    part.add_dart(dart, notches=False, precision_tip=True)
    pattern = Pattern("test")
    pattern.add_part(part)
    out = tmp_path / "direct_noname.svg"
    export_pattern_svg_mm(pattern, filename=str(out), width_mm=210, height_mm=297)
    assert out.exists()
    assert "<svg" in out.read_text()
