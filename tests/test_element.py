"""Tests for element.py — PatternElement.split_at_dart, PrecisionPoint."""

import unittest

from sewpat.element import PatternElement, PrecisionPoint
from sewpat.geometry import (
    Circle,
    CubicBezier,
    Dart,
    Point,
    Rect,
    Segment,
)
from sewpat.style import STYLE_STITCH, StyleOptions
from sewpat.units import CM, MM

# ---------------------------------------------------------------------------
# PatternElement.split_at_dart
# ---------------------------------------------------------------------------


class TestSplitAtDart(unittest.TestCase):
    """Tests for PatternElement.split_at_dart."""

    def _make_dart(self, seg: Segment) -> Dart:
        """Create a triangle dart whose legs lie at t=0.25 and t=0.75 of seg."""
        leg_a = seg.point_at_t(0.25)
        leg_b = seg.point_at_t(0.75)
        center = seg.point_at_t(0.5)
        tip = center.translate(0, -2 * CM)
        return Dart(leg_a=leg_a, leg_b=leg_b, center=center, tip=tip)

    def test_segment_splits_into_two_outer_parts(self):
        """A segment split by a dart returns two outer PatternElement stubs."""
        seg = Segment(Point(0, 0), Point(10 * CM, 0))
        dart = self._make_dart(seg)
        elem = PatternElement(seg, style=STYLE_STITCH, is_outline=True)
        children = elem.split_at_dart(dart)
        self.assertEqual(len(children), 2)

    def test_children_inherit_style(self):
        """Children inherit the style of the parent element."""
        seg = Segment(Point(0, 0), Point(10 * CM, 0))
        dart = self._make_dart(seg)
        elem = PatternElement(seg, style=STYLE_STITCH, is_outline=True)
        children = elem.split_at_dart(dart)
        for child in children:
            self.assertEqual(child.style, STYLE_STITCH)

    def test_children_inherit_is_outline(self):
        """Children inherit is_outline from the parent."""
        seg = Segment(Point(0, 0), Point(10 * CM, 0))
        dart = self._make_dart(seg)
        elem = PatternElement(seg, is_outline=True)
        children = elem.split_at_dart(dart)
        for child in children:
            self.assertTrue(child.is_outline)

    def test_non_segment_raises_type_error(self):
        """TypeError is raised for unsupported geometry types."""
        rect = Rect(Point(0, 0), 5 * CM, 5 * CM)
        elem = PatternElement(rect)
        dart = Dart(
            leg_a=Point(1 * CM, 0),
            leg_b=Point(4 * CM, 0),
            center=Point(2.5 * CM, 0),
            tip=Point(2.5 * CM, -2 * CM),
        )
        with self.assertRaises(TypeError):
            elem.split_at_dart(dart)

    def test_cubic_bezier_splits(self):
        """A CubicBezier element can also be split at a dart."""
        p0 = Point(0, 0)
        p3 = Point(10 * CM, 0)
        bez = CubicBezier(p0, Point(3 * CM, -2 * CM), Point(7 * CM, -2 * CM), p3)
        leg_a = bez.point_at_t(0.25)
        leg_b = bez.point_at_t(0.75)
        center = bez.point_at_t(0.5)
        tip = center.translate(0, -2 * CM)
        dart = Dart(leg_a=leg_a, leg_b=leg_b, center=center, tip=tip)
        elem = PatternElement(bez, is_outline=True)
        children = elem.split_at_dart(dart)
        self.assertGreaterEqual(len(children), 1)


# ---------------------------------------------------------------------------
# PrecisionPoint
# ---------------------------------------------------------------------------


class TestPrecisionPoint(unittest.TestCase):
    """Tests for PrecisionPoint."""

    def test_default_radii(self):
        """Default outer and inner radii are correct."""
        p = Point(5 * CM, 5 * CM)
        pp = PrecisionPoint(p)
        self.assertAlmostEqual(pp.outer_radius, 2.0 * MM)
        self.assertAlmostEqual(pp.inner_radius, 0.2 * MM)

    def test_custom_radii(self):
        """Custom radii are stored correctly."""
        p = Point(0, 0)
        pp = PrecisionPoint(p, outer_radius=3 * MM, inner_radius=0.5 * MM)
        self.assertAlmostEqual(pp.outer_radius, 3 * MM)
        self.assertAlmostEqual(pp.inner_radius, 0.5 * MM)

    def test_build_elements_returns_two_circles(self):
        """build_elements() returns exactly two PatternElements."""
        p = Point(5 * CM, 5 * CM)
        pp = PrecisionPoint(p)
        elems = pp.build_elements()
        self.assertEqual(len(elems), 2)
        for e in elems:
            self.assertIsInstance(e, PatternElement)

    def test_build_elements_are_circles(self):
        """The two elements wrap Circle geometry."""
        p = Point(0, 0)
        pp = PrecisionPoint(p)
        elems = pp.build_elements()
        for e in elems:
            self.assertIsInstance(e.geometry, Circle)

    def test_custom_style_applied(self):
        """A custom style is stored and returned by build_elements."""
        p = Point(0, 0)
        style = StyleOptions(stroke_color="blue")
        pp = PrecisionPoint(p, style=style)
        elems = pp.build_elements()
        for e in elems:
            self.assertEqual(e.style, style)


if __name__ == "__main__":
    unittest.main()
