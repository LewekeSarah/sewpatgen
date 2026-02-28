"""Tests for the part module.

Covers:
  - PatternElement: creation, get_name (own name, geometry name, no name)
  - PatternPart: append, extend, centroid, add_grainline, add_info_box,
                 add_precision_points, add_notches
  - Pattern: add_part, get_part, add_reference_square, anchor default
"""

import math
import unittest
from typing import cast

from sewpat.geometry import Circle, InfoBox, Point, Rect, Segment, Triangle
from sewpat.part import Pattern, PatternElement, PatternPart
from sewpat.style import STYLE_GRAINLINE, StyleOptions
from sewpat.units import CM, MM


# ---------------------------------------------------------------------------
# PatternElement
# ---------------------------------------------------------------------------


class TestPatternElement(unittest.TestCase):
    """Tests for PatternElement."""

    def test_creation_default_style(self):
        """PatternElement with no style gets a default StyleOptions instance."""
        p = Point(0, 0)
        elem = PatternElement(geometry=p)
        self.assertIsInstance(elem.style, StyleOptions)
        self.assertIsNone(elem.name)
        self.assertIs(elem.geometry, p)

    def test_creation_with_style_and_name(self):
        """Explicit style and name are stored correctly."""
        p = Point(1, 2)
        style = StyleOptions(stroke_color="red")
        elem = PatternElement(geometry=p, style=style, name="my-point")
        self.assertIs(elem.style, style)
        self.assertEqual(elem.name, "my-point")

    def test_get_name_returns_element_name_over_geometry_name(self):
        """Element name takes precedence over geometry name."""
        seg = Segment(Point(0, 0), Point(1, 0), name="geo-name")
        elem = PatternElement(geometry=seg, name="elem-name")
        self.assertEqual(elem.get_name(), "elem-name")

    def test_get_name_falls_back_to_geometry_name(self):
        """get_name returns geometry.name when element has no own name."""
        seg = Segment(Point(0, 0), Point(1, 0), name="geo-name")
        elem = PatternElement(geometry=seg)
        self.assertEqual(elem.get_name(), "geo-name")

    def test_get_name_none_when_both_absent(self):
        """get_name returns None when neither element nor geometry has a name."""
        p = Point(0, 0)  # Point has no name attribute
        elem = PatternElement(geometry=p)
        self.assertIsNone(elem.get_name())


# ---------------------------------------------------------------------------
# PatternPart – basic collection operations
# ---------------------------------------------------------------------------


class TestPatternPartBasics(unittest.TestCase):
    """Tests for PatternPart creation and element management."""

    def test_creation_empty(self):
        """A freshly created PatternPart has no elements."""
        part = PatternPart(name="Bodice")
        self.assertEqual(part.name, "Bodice")
        self.assertEqual(len(part.elements), 0)

    def test_append_returns_element(self):
        """append() returns the created PatternElement."""
        part = PatternPart(name="Body")
        p = Point(1, 2)
        elem = part.append(p)
        self.assertIsInstance(elem, PatternElement)
        self.assertIs(elem.geometry, p)
        self.assertEqual(len(part.elements), 1)

    def test_append_with_style_and_name(self):
        """append() passes style and name through to PatternElement."""
        part = PatternPart(name="Body")
        style = StyleOptions(stroke_color="blue")
        elem = part.append(Point(0, 0), style=style, name="centre")
        self.assertIs(elem.style, style)
        self.assertEqual(elem.name, "centre")

    def test_extend(self):
        """extend() appends multiple PatternElements at once."""
        part = PatternPart(name="Body")
        elems = [
            PatternElement(Point(0, 0)),
            PatternElement(Point(1, 1)),
            PatternElement(Point(2, 2)),
        ]
        part.extend(elems)
        self.assertEqual(len(part.elements), 3)
        self.assertIs(part.elements[2].geometry, elems[2].geometry)

    def test_creation_with_elements(self):
        """PatternPart can be initialised with a pre-existing list of elements."""
        elems = [PatternElement(Point(5, 5))]
        part = PatternPart(name="Collar", elements=elems)
        self.assertEqual(len(part.elements), 1)


# ---------------------------------------------------------------------------
# PatternPart – centroid
# ---------------------------------------------------------------------------


class TestPatternPartCentroid(unittest.TestCase):
    """Tests for PatternPart.centroid."""

    def test_centroid_none_on_empty_part(self):
        """centroid returns None when the part has no geometry."""
        part = PatternPart(name="Empty")
        self.assertIsNone(part.centroid)

    def test_centroid_from_points(self):
        """centroid averages Point coordinates."""
        part = PatternPart(name="P")
        part.append(Point(0, 0))
        part.append(Point(4, 0))
        part.append(Point(0, 4))
        c = part.centroid
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.x, 4 / 3)
        self.assertAlmostEqual(c.y, 4 / 3)

    def test_centroid_from_segments(self):
        """centroid uses both endpoints of Segment objects."""
        part = PatternPart(name="S")
        part.append(Segment(Point(0, 0), Point(2, 0)))
        c = part.centroid
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.x, 1.0)
        self.assertAlmostEqual(c.y, 0.0)

    def test_centroid_from_rect(self):
        """centroid uses origin and opposite corner of Rect objects."""
        part = PatternPart(name="R")
        part.append(Rect(origin=Point(0, 0), width=4, height=6))
        c = part.centroid
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.x, 2.0)
        self.assertAlmostEqual(c.y, 3.0)

    def test_centroid_from_circle(self):
        """centroid uses Circle centre point."""
        part = PatternPart(name="C")
        part.append(Circle(Point(3, 7), radius=5 * MM))
        c = part.centroid
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.x, 3.0)
        self.assertAlmostEqual(c.y, 7.0)


# ---------------------------------------------------------------------------
# PatternPart – add_grainline
# ---------------------------------------------------------------------------


class TestAddGrainline(unittest.TestCase):
    """Tests for PatternPart.add_grainline."""

    def test_grainline_added(self):
        """add_grainline appends a Segment with STYLE_GRAINLINE."""
        part = PatternPart(name="Front")
        start = Point(0, 0)
        end = Point(0, 5 * CM)
        elem = part.add_grainline(start, end)
        self.assertIsInstance(elem.geometry, Segment)
        self.assertIs(elem.style, STYLE_GRAINLINE)

    def test_grainline_default_name(self):
        """Default grainline name contains 'grainline'."""
        part = PatternPart(name="Front")
        elem = part.add_grainline(Point(0, 0), Point(0, 10))
        self.assertIn("grainline", elem.get_name().lower())

    def test_grainline_custom_name(self):
        """Custom grainline name is stored."""
        part = PatternPart(name="Back")
        elem = part.add_grainline(Point(0, 0), Point(0, 10), name="Grain")
        self.assertEqual(elem.get_name(), "Grain")


# ---------------------------------------------------------------------------
# PatternPart – add_info_box
# ---------------------------------------------------------------------------


class TestAddInfoBox(unittest.TestCase):
    """Tests for PatternPart.add_info_box."""

    def test_returns_none_without_geometry(self):
        """add_info_box returns None when the part has no centroid."""
        part = PatternPart(name="Empty")
        result = part.add_info_box()
        self.assertIsNone(result)

    def test_info_box_position_is_centroid(self):
        """The InfoBox is placed at the centroid of the part."""
        part = PatternPart(name="Sleeve")
        part.append(Point(0, 0))
        part.append(Point(10, 0))
        part.append(Point(0, 10))
        centroid = part.centroid
        elem = part.add_info_box()
        self.assertIsInstance(elem.geometry, InfoBox)
        ib: InfoBox = elem.geometry
        self.assertAlmostEqual(ib.position.x, centroid.x)
        self.assertAlmostEqual(ib.position.y, centroid.y)

    def test_info_box_default_header_is_part_name(self):
        """Default header equals the part name."""
        part = PatternPart(name="Sleeve")
        part.append(Point(5, 5))
        elem = part.add_info_box()
        self.assertEqual(elem.geometry.header, "Sleeve")

    def test_info_box_custom_header(self):
        """Custom header overrides the part name."""
        part = PatternPart(name="Sleeve")
        part.append(Point(5, 5))
        elem = part.add_info_box(header="Custom Header")
        self.assertEqual(elem.geometry.header, "Custom Header")

    def test_info_box_notes(self):
        """Notes are stored on the InfoBox."""
        part = PatternPart(name="Cuff")
        part.append(Point(5, 5))
        notes = ["1 cm seam allowance", "Cut 2×"]
        elem = part.add_info_box(notes=notes)
        self.assertEqual(elem.geometry.notes, notes)


# ---------------------------------------------------------------------------
# PatternPart – add_precision_points
# ---------------------------------------------------------------------------


class TestAddPrecisionPoints(unittest.TestCase):
    """Tests for PatternPart.add_precision_points."""

    def test_two_circles_per_point(self):
        """Each precision point adds exactly two Circle elements."""
        part = PatternPart(name="Body")
        part.add_precision_points(Point(5, 5))
        circles = [e for e in part.elements if isinstance(e.geometry, Circle)]
        self.assertEqual(len(circles), 2)

    def test_multiple_points(self):
        """Multiple precision points each add two circles."""
        part = PatternPart(name="Body")
        part.add_precision_points(Point(0, 0), Point(10, 10), Point(20, 20))
        circles = [e for e in part.elements if isinstance(e.geometry, Circle)]
        self.assertEqual(len(circles), 6)

    def test_circle_radii(self):
        """Circles have the correct radii (5 mm outer, 0.5 mm inner)."""
        part = PatternPart(name="Body")
        part.add_precision_points(Point(0, 0))
        radii = sorted(
            e.geometry.radius for e in part.elements if isinstance(e.geometry, Circle)
        )
        self.assertAlmostEqual(radii[0], 0.2 * MM)
        self.assertAlmostEqual(radii[1], 2.0 * MM)


# ---------------------------------------------------------------------------
# PatternPart – add_notches
# ---------------------------------------------------------------------------


class TestAddNotches(unittest.TestCase):
    """Tests for PatternPart.add_notches."""

    def test_notch_without_segment_adds_triangle(self):
        """Without a segment, a Triangle element is added for each point."""
        part = PatternPart(name="Body")
        part.add_notches(Point(5, 0))
        triangles = [e for e in part.elements if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_notch_without_segment_tip_above_base(self):
        """Without a segment the tip is above the base (negative y offset)."""
        part = PatternPart(name="Body")
        pt = Point(10, 10)
        part.add_notches(pt)
        tri = cast(Triangle, part.elements[-1].geometry)
        # Tip y should be lower (smaller y) than base
        base_y = (tri.p1.y + tri.p2.y) / 2
        self.assertLess(tri.p3.y, base_y)

    def test_multiple_notches(self):
        """Multiple point arguments each produce one Triangle."""
        part = PatternPart(name="Body")
        part.add_notches(Point(0, 0), Point(5, 0), Point(10, 0))
        triangles = [e for e in part.elements if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 3)

    def test_notch_with_segment_adds_triangle(self):
        """With a segment, a Triangle is still produced."""
        part = PatternPart(name="Body")
        # Build a rectangle so centroid is well-defined and lies above the
        # bottom edge.
        part.append(Rect(origin=Point(0, 0), width=10 * CM, height=10 * CM))
        seg = Segment(Point(0, 10 * CM), Point(10 * CM, 10 * CM))
        mid = Point(5 * CM, 10 * CM)
        part.add_notches(mid, seam_edge=seg)
        triangles = [e for e in part.elements if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_notch_with_segment_tip_points_inward(self):
        """Notch tip points toward the centroid (inward), not outward."""
        part = PatternPart(name="Body")
        # Rect with centroid at (5 cm, 5 cm)
        part.append(Rect(origin=Point(0, 0), width=10 * CM, height=10 * CM))
        # Bottom edge: y = 10 cm  →  centroid is at y = 5 cm  →  inward = up (negative y)
        seg = Segment(Point(0, 10 * CM), Point(10 * CM, 10 * CM))
        mid = Point(5 * CM, 10 * CM)
        part.add_notches(mid, seam_edge=seg)
        tri = cast(Triangle, part.elements[-1].geometry)
        # Tip (p3) should have a smaller y-coordinate than the midpoint (closer to centroid)
        self.assertLess(tri.p3.y, mid.y)

    def test_notch_custom_length_and_width(self):
        """Custom length and width change the triangle dimensions."""
        part = PatternPart(name="Body")
        pt = Point(10, 0)
        part.add_notches(pt, length=1.5 * CM, width=0.6 * CM)
        tri = cast(Triangle, part.elements[-1].geometry)
        base_width = tri.p1.distance_to(tri.p2)
        tip_dist = ((tri.p1.x + tri.p2.x) / 2 - tri.p3.x) ** 2 + (
            (tri.p1.y + tri.p2.y) / 2 - tri.p3.y
        ) ** 2
        self.assertAlmostEqual(base_width, 0.6 * CM, places=6)
        self.assertAlmostEqual(math.sqrt(tip_dist), 1.5 * CM, places=6)


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class TestPattern(unittest.TestCase):
    """Tests for the Pattern class."""

    def test_creation_defaults(self):
        """Pattern has an empty parts list and default anchor by default."""
        pat = Pattern(name="My Pattern")
        self.assertEqual(pat.name, "My Pattern")
        self.assertEqual(len(pat.parts), 0)
        self.assertIsNone(pat.reference_square)
        # Default anchor = (1.5 cm, 1.5 cm)
        self.assertAlmostEqual(pat.anchor.x, 1.5 * CM)
        self.assertAlmostEqual(pat.anchor.y, 1.5 * CM)

    def test_custom_anchor(self):
        """Pattern respects a custom anchor."""
        anchor = Point(2 * CM, 3 * CM)
        pat = Pattern(name="P", anchor=anchor)
        self.assertIs(pat.anchor, anchor)

    def test_add_part(self):
        """add_part appends the part and returns it."""
        pat = Pattern(name="P")
        part = PatternPart(name="Front")
        returned = pat.add_part(part)
        self.assertIs(returned, part)
        self.assertEqual(len(pat.parts), 1)
        self.assertIs(pat.parts[0], part)

    def test_get_part_found(self):
        """get_part returns the correct part by name."""
        pat = Pattern(name="P")
        front = PatternPart(name="Front")
        back = PatternPart(name="Back")
        pat.add_part(front)
        pat.add_part(back)
        self.assertIs(pat.get_part("Back"), back)

    def test_get_part_not_found(self):
        """get_part raises KeyError for an unknown name."""
        pat = Pattern(name="P")
        with self.assertRaises(KeyError):
            pat.get_part("NonExistent")

    def test_add_reference_square_default(self):
        """add_reference_square creates a square element with the right size."""
        pat = Pattern(name="P")
        origin = Point(0, 0)
        elem = pat.add_reference_square(origin)
        self.assertIsNotNone(pat.reference_square)
        self.assertIs(pat.reference_square, elem)
        rect = cast(Rect, elem.geometry)
        self.assertAlmostEqual(rect.width, 3 * CM)
        self.assertAlmostEqual(rect.height, 3 * CM)

    def test_add_reference_square_custom_edge_length(self):
        """add_reference_square uses the provided edge_length."""
        pat = Pattern(name="P")
        elem = pat.add_reference_square(Point(0, 0), edge_length=5 * CM)
        rect = cast(Rect, elem.geometry)
        self.assertAlmostEqual(rect.width, 5 * CM)
        self.assertAlmostEqual(rect.height, 5 * CM)

    def test_add_reference_square_custom_style(self):
        """add_reference_square uses a custom style when provided."""
        pat = Pattern(name="P")
        style = StyleOptions(stroke_color="red")
        elem = pat.add_reference_square(Point(0, 0), style=style)
        self.assertIs(elem.style, style)

    def test_creation_with_parts(self):
        """Pattern can be initialised with a pre-existing list of parts."""
        parts = [PatternPart(name="Front"), PatternPart(name="Back")]
        pat = Pattern(name="P", parts=parts)
        self.assertEqual(len(pat.parts), 2)


if __name__ == "__main__":
    unittest.main()
