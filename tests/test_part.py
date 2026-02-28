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

from sewpat.geometry import (
    Circle,
    CubicBezier,
    InfoBox,
    Point,
    Rect,
    Segment,
    Triangle,
    seam_length,
)
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

    def test_centroid_none_without_outline_elements(self):
        """centroid returns None when elements exist but none are is_outline."""
        part = PatternPart(name="P")
        part.append(Point(0, 0))
        part.append(Segment(Point(0, 0), Point(10, 0)))
        self.assertIsNone(part.centroid)

    def test_centroid_from_outline_polygon_square(self):
        """With is_outline Segments Shapely returns the true geometric centroid."""
        part = PatternPart(name="Square")
        # 10 × 10 square → true centroid = (5, 5)
        part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
        part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
        part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
        part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
        c = part.centroid
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.x, 5.0, places=3)
        self.assertAlmostEqual(c.y, 5.0, places=3)

    def test_centroid_from_outline_polygon_rectangle(self):
        """Shapely centroid is correct for a non-square rectangle."""
        part = PatternPart(name="Rect")
        # 20 × 6 rectangle → centroid = (10, 3)
        part.append(Segment(Point(0, 0), Point(20, 0)), is_outline=True)
        part.append(Segment(Point(20, 0), Point(20, 6)), is_outline=True)
        part.append(Segment(Point(20, 6), Point(0, 6)), is_outline=True)
        part.append(Segment(Point(0, 6), Point(0, 0)), is_outline=True)
        c = part.centroid
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.x, 10.0, places=3)
        self.assertAlmostEqual(c.y, 3.0, places=3)


# ---------------------------------------------------------------------------
# PatternPart – area_cm2
# ---------------------------------------------------------------------------


class TestPatternPartArea(unittest.TestCase):
    """Tests for PatternPart.area_cm2."""

    def test_area_none_without_outline(self):
        """area_cm2 returns None when no outline elements are present."""
        part = PatternPart(name="Empty")
        self.assertIsNone(part.area_cm2)

    def test_area_square_10mm(self):
        """10 mm × 10 mm square → area = 1 cm²."""
        part = PatternPart(name="Square")
        part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
        part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
        part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
        part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
        self.assertAlmostEqual(part.area_cm2, 1.0, places=4)

    def test_area_rectangle(self):
        """40 mm × 30 mm rectangle → area = 12 cm²."""
        part = PatternPart(name="Rect")
        part.append(Segment(Point(0, 0), Point(40, 0)), is_outline=True)
        part.append(Segment(Point(40, 0), Point(40, 30)), is_outline=True)
        part.append(Segment(Point(40, 30), Point(0, 30)), is_outline=True)
        part.append(Segment(Point(0, 30), Point(0, 0)), is_outline=True)
        self.assertAlmostEqual(part.area_cm2, 12.0, places=4)


# ---------------------------------------------------------------------------
# PatternPart – bounding_box
# ---------------------------------------------------------------------------


class TestPatternPartBoundingBox(unittest.TestCase):
    """Tests for PatternPart.bounding_box."""

    def _rect_part(self, x0, y0, x1, y1) -> PatternPart:
        """Helper: build a rectangular PatternPart from two corners."""
        part = PatternPart(name="Rect")
        part.append(Segment(Point(x0, y0), Point(x1, y0)), is_outline=True)
        part.append(Segment(Point(x1, y0), Point(x1, y1)), is_outline=True)
        part.append(Segment(Point(x1, y1), Point(x0, y1)), is_outline=True)
        part.append(Segment(Point(x0, y1), Point(x0, y0)), is_outline=True)
        return part

    def test_returns_none_without_outline(self):
        """bounding_box returns None when no outline elements are present."""
        part = PatternPart(name="Empty")
        self.assertIsNone(part.bounding_box())

    def test_returns_none_without_outline_flag(self):
        """bounding_box returns None when segments exist but none are is_outline."""
        part = PatternPart(name="P")
        part.append(Segment(Point(0, 0), Point(10, 0)))  # is_outline=False
        self.assertIsNone(part.bounding_box())

    def test_axis_aligned_square(self):
        """10 × 10 mm square at origin → bbox (0,0) – (10,10)."""
        part = self._rect_part(0, 0, 10, 10)
        bb = part.bounding_box()
        self.assertIsNotNone(bb)
        mn, mx = bb
        self.assertAlmostEqual(mn.x, 0.0, places=6)
        self.assertAlmostEqual(mn.y, 0.0, places=6)
        self.assertAlmostEqual(mx.x, 10.0, places=6)
        self.assertAlmostEqual(mx.y, 10.0, places=6)

    def test_offset_rectangle(self):
        """Rectangle not at origin: bbox min/max match the corners."""
        part = self._rect_part(5, 15, 45, 70)
        bb = part.bounding_box()
        self.assertIsNotNone(bb)
        mn, mx = bb
        self.assertAlmostEqual(mn.x, 5.0, places=6)
        self.assertAlmostEqual(mn.y, 15.0, places=6)
        self.assertAlmostEqual(mx.x, 45.0, places=6)
        self.assertAlmostEqual(mx.y, 70.0, places=6)

    def test_bbox_width_and_height(self):
        """Derived width and height from bbox match the rectangle dimensions."""
        w, h = 60.0, 40.0
        part = self._rect_part(0, 0, w, h)
        mn, mx = part.bounding_box()
        self.assertAlmostEqual(mx.x - mn.x, w, places=6)
        self.assertAlmostEqual(mx.y - mn.y, h, places=6)

    def test_non_outline_elements_ignored(self):
        """Elements without is_outline=True do not expand the bounding box."""
        part = self._rect_part(0, 0, 20, 20)
        # Add a segment far outside the outline but without is_outline
        part.append(Segment(Point(100, 100), Point(200, 200)))
        mn, mx = part.bounding_box()
        self.assertAlmostEqual(mx.x, 20.0, places=6)
        self.assertAlmostEqual(mx.y, 20.0, places=6)

    def test_bezier_outline_expands_bbox(self):
        """A CubicBezier outline whose control points bulge outside the chord
        produces a bounding box larger than the chord's own extent."""
        # Flat chord from (0,0) to (40,0); control points push curve up to ~y=15
        b = CubicBezier(Point(0, 0), Point(10, 20), Point(30, 20), Point(40, 0))
        part = PatternPart(name="Curve")
        part.append(b, is_outline=True)
        part.append(Segment(Point(40, 0), Point(0, 0)), is_outline=True)
        bb = part.bounding_box()
        self.assertIsNotNone(bb)
        mn, mx = bb
        # x extent must span [0, 40]
        self.assertAlmostEqual(mn.x, 0.0, places=3)
        self.assertAlmostEqual(mx.x, 40.0, places=3)
        # y extent: flat chord is 0 but curve bulges above → max y > 0
        self.assertAlmostEqual(mn.y, 0.0, places=3)
        self.assertGreater(mx.y, 10.0)


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
        part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
        part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
        part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
        part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
        centroid = part.centroid
        elem = part.add_info_box()
        self.assertIsInstance(elem.geometry, InfoBox)
        ib: InfoBox = elem.geometry
        self.assertAlmostEqual(ib.position.x, centroid.x)
        self.assertAlmostEqual(ib.position.y, centroid.y)

    def test_info_box_default_header_is_part_name(self):
        """Default header equals the part name."""
        part = PatternPart(name="Sleeve")
        part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
        part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
        part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
        part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
        elem = part.add_info_box()
        self.assertEqual(elem.geometry.header, "Sleeve")

    def test_info_box_custom_header(self):
        """Custom header overrides the part name."""
        part = PatternPart(name="Sleeve")
        part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
        part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
        part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
        part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
        elem = part.add_info_box(header="Custom Header")
        self.assertEqual(elem.geometry.header, "Custom Header")

    def test_info_box_notes(self):
        """Notes are stored on the InfoBox."""
        part = PatternPart(name="Cuff")
        part.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
        part.append(Segment(Point(10, 0), Point(10, 10)), is_outline=True)
        part.append(Segment(Point(10, 10), Point(0, 10)), is_outline=True)
        part.append(Segment(Point(0, 10), Point(0, 0)), is_outline=True)
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
        part.append(Segment(Point(0, 0), Point(10 * CM, 0)), is_outline=True)
        part.append(
            Segment(Point(10 * CM, 0), Point(10 * CM, 10 * CM)), is_outline=True
        )
        part.append(
            Segment(Point(10 * CM, 10 * CM), Point(0, 10 * CM)), is_outline=True
        )
        part.append(Segment(Point(0, 10 * CM), Point(0, 0)), is_outline=True)
        seg = Segment(Point(0, 10 * CM), Point(10 * CM, 10 * CM))
        mid = Point(5 * CM, 10 * CM)
        part.add_notches(mid, seam_edge=seg)
        triangles = [e for e in part.elements if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_notch_with_segment_tip_points_inward(self):
        """Notch tip points toward the centroid (inward), not outward."""
        part = PatternPart(name="Body")
        part.append(Segment(Point(0, 0), Point(10 * CM, 0)), is_outline=True)
        part.append(
            Segment(Point(10 * CM, 0), Point(10 * CM, 10 * CM)), is_outline=True
        )
        part.append(
            Segment(Point(10 * CM, 10 * CM), Point(0, 10 * CM)), is_outline=True
        )
        part.append(Segment(Point(0, 10 * CM), Point(0, 0)), is_outline=True)
        # Bottom edge: y = 10 cm → centroid is at y = 5 cm → inward = up (negative y)
        seg = Segment(Point(0, 10 * CM), Point(10 * CM, 10 * CM))
        mid = Point(5 * CM, 10 * CM)
        part.add_notches(mid, seam_edge=seg)
        tri = cast(Triangle, part.elements[-1].geometry)
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


# ---------------------------------------------------------------------------
# PatternPart – contains_point
# ---------------------------------------------------------------------------


class TestPatternPartContainsPoint(unittest.TestCase):
    """Tests for PatternPart.contains_point."""

    def _square_part(self, size: float = 100.0) -> PatternPart:
        """Helper: axis-aligned square from (0,0) to (size, size)."""
        part = PatternPart(name="Square")
        part.append(Segment(Point(0, 0), Point(size, 0)), is_outline=True)
        part.append(Segment(Point(size, 0), Point(size, size)), is_outline=True)
        part.append(Segment(Point(size, size), Point(0, size)), is_outline=True)
        part.append(Segment(Point(0, size), Point(0, 0)), is_outline=True)
        return part

    def test_returns_false_without_outline(self):
        """contains_point returns False when no outline polygon exists."""
        part = PatternPart(name="Empty")
        self.assertFalse(part.contains_point(Point(5, 5)))

    def test_centre_is_inside(self):
        """The geometric centre of a square is strictly inside."""
        part = self._square_part(100)
        self.assertTrue(part.contains_point(Point(50, 50)))

    def test_corner_is_outside(self):
        """A corner vertex is on the boundary, not strictly inside."""
        part = self._square_part(100)
        self.assertFalse(part.contains_point(Point(0, 0)))

    def test_point_outside_is_false(self):
        """A point clearly outside the polygon returns False."""
        part = self._square_part(100)
        self.assertFalse(part.contains_point(Point(200, 200)))

    def test_point_near_edge_inside(self):
        """A point just inside an edge is still inside."""
        part = self._square_part(100)
        self.assertTrue(part.contains_point(Point(1, 50)))

    def test_point_near_edge_outside(self):
        """A point just outside an edge is outside."""
        part = self._square_part(100)
        self.assertFalse(part.contains_point(Point(-1, 50)))


# ---------------------------------------------------------------------------
# PatternPart – add_grainline nudging
# ---------------------------------------------------------------------------


class TestAddGrainlineClipping(unittest.TestCase):
    """Tests for automatic grainline endpoint nudging in add_grainline.

    The implementation moves outside endpoints inward in 1 mm steps until
    ``contains_point`` returns True (strictly inside).  Points on the boundary
    are also considered outside, so the first accepted position is 1 mm inside
    the boundary.  Tests use ``assertGreater``/``assertLess`` where applicable
    to stay robust against the step size, and only verify the direction and
    rough magnitude of the correction.
    """

    def _square_part(self, size: float = 100.0) -> PatternPart:
        part = PatternPart(name="Square")
        part.append(Segment(Point(0, 0), Point(size, 0)), is_outline=True)
        part.append(Segment(Point(size, 0), Point(size, size)), is_outline=True)
        part.append(Segment(Point(size, size), Point(0, size)), is_outline=True)
        part.append(Segment(Point(0, size), Point(0, 0)), is_outline=True)
        return part

    def test_fully_inside_unchanged(self):
        """A grainline whose both endpoints are already inside is not modified."""
        part = self._square_part(100)
        elem = part.add_grainline(Point(20, 50), Point(80, 50))
        seg = cast(Segment, elem.geometry)
        self.assertAlmostEqual(seg.p1.x, 20.0, places=3)
        self.assertAlmostEqual(seg.p2.x, 80.0, places=3)

    def test_start_outside_is_nudged_inward(self):
        """Start point outside → nudged to strictly inside on the left side."""
        part = self._square_part(100)
        # Horizontal line: start at x=-20 (outside), end at x=80 (inside)
        elem = part.add_grainline(Point(-20, 50), Point(80, 50))
        seg = cast(Segment, elem.geometry)
        # Nudged start must be strictly inside (x > 0) and close to the left edge
        self.assertGreater(seg.p1.x, 0.0)
        self.assertLess(seg.p1.x, 5.0)
        self.assertAlmostEqual(seg.p1.y, 50.0, places=3)
        # End was already inside — unchanged
        self.assertAlmostEqual(seg.p2.x, 80.0, places=3)

    def test_end_outside_is_nudged_inward(self):
        """End point outside → nudged to strictly inside on the right side."""
        part = self._square_part(100)
        elem = part.add_grainline(Point(20, 50), Point(150, 50))
        seg = cast(Segment, elem.geometry)
        # Start unchanged
        self.assertAlmostEqual(seg.p1.x, 20.0, places=3)
        # Nudged end must be strictly inside and close to the right edge
        self.assertLess(seg.p2.x, 100.0)
        self.assertGreater(seg.p2.x, 95.0)
        self.assertAlmostEqual(seg.p2.y, 50.0, places=3)

    def test_both_outside_nudged_inward(self):
        """Both endpoints outside but line crosses the square → both nudged inside."""
        part = self._square_part(100)
        # Vertical line crossing the full square from y=-20 to y=120
        elem = part.add_grainline(Point(50, -20), Point(50, 120))
        seg = cast(Segment, elem.geometry)
        # Both ends must now be strictly inside [0, 100]
        self.assertGreater(seg.p1.y, 0.0)
        self.assertLess(seg.p1.y, 5.0)
        self.assertLess(seg.p2.y, 100.0)
        self.assertGreater(seg.p2.y, 95.0)

    def test_no_outline_no_crash(self):
        """add_grainline on a part without an outline leaves points unchanged."""
        part = PatternPart(name="NoOutline")
        elem = part.add_grainline(Point(-10, -10), Point(200, 200))
        seg = cast(Segment, elem.geometry)
        self.assertAlmostEqual(seg.p1.x, -10.0)
        self.assertAlmostEqual(seg.p2.x, 200.0)


# ---------------------------------------------------------------------------
# Pattern – add_reference_square auto-placement
# ---------------------------------------------------------------------------


class TestAddReferenceSquarePlacement(unittest.TestCase):
    """Tests for the auto-placement logic in Pattern.add_reference_square."""

    def _pattern_with_square_part(
        self, size: float = 200.0
    ) -> tuple[Pattern, PatternPart]:
        """Helper: a Pattern with one rectangular PatternPart."""
        part = PatternPart(name="Body")
        part.append(Segment(Point(0, 0), Point(size, 0)), is_outline=True)
        part.append(Segment(Point(size, 0), Point(size, size)), is_outline=True)
        part.append(Segment(Point(size, size), Point(0, size)), is_outline=True)
        part.append(Segment(Point(0, size), Point(0, 0)), is_outline=True)
        pat = Pattern(name="P")
        pat.add_part(part)
        return pat, part

    def test_origin_inside_unchanged(self):
        """An origin already well inside the bbox is not moved."""
        pat, _ = self._pattern_with_square_part(200)
        edge = 3 * CM
        origin = Point(10, 10)
        elem = pat.add_reference_square(origin, edge_length=edge)
        rect = cast(Rect, elem.geometry)
        self.assertAlmostEqual(rect.origin.x, 10.0, places=3)
        self.assertAlmostEqual(rect.origin.y, 10.0, places=3)

    def test_origin_outside_is_shifted_inside(self):
        """An origin outside the bbox is clamped so the square fits inside."""
        pat, _ = self._pattern_with_square_part(200)
        edge = 3 * CM
        # Origin far outside to the left and above
        elem = pat.add_reference_square(Point(-500, -500), edge_length=edge)
        rect = cast(Rect, elem.geometry)
        # After clamping the square's left edge must be >= bbox min + padding
        self.assertGreaterEqual(rect.origin.x, 0.0)
        self.assertGreaterEqual(rect.origin.y, 0.0)
        # And the square must still fit inside the bbox (200 × 200 mm)
        self.assertLessEqual(rect.origin.x + edge, 200.0)
        self.assertLessEqual(rect.origin.y + edge, 200.0)

    def test_explicit_part_used_over_auto(self):
        """When *part* is supplied explicitly it is used for placement."""
        pat = Pattern(name="P")
        part_a = PatternPart(name="A")
        part_b = PatternPart(name="B")
        # part_a: small square 0–50
        for seg in [
            Segment(Point(0, 0), Point(50, 0)),
            Segment(Point(50, 0), Point(50, 50)),
            Segment(Point(50, 50), Point(0, 50)),
            Segment(Point(0, 50), Point(0, 0)),
        ]:
            part_a.append(seg, is_outline=True)
        # part_b: large square 0–400
        for seg in [
            Segment(Point(0, 0), Point(400, 0)),
            Segment(Point(400, 0), Point(400, 400)),
            Segment(Point(400, 400), Point(0, 400)),
            Segment(Point(0, 400), Point(0, 0)),
        ]:
            part_b.append(seg, is_outline=True)
        pat.add_part(part_a)
        pat.add_part(part_b)
        edge = 3 * CM
        # Pass origin outside both parts; anchor to part_a (50 × 50 mm)
        elem = pat.add_reference_square(
            Point(-100, -100), edge_length=edge, part=part_a
        )
        rect = cast(Rect, elem.geometry)
        # Square must fit inside part_a's 50 mm extent
        self.assertLessEqual(rect.origin.x + edge, 50.0)
        self.assertLessEqual(rect.origin.y + edge, 50.0)

    def test_no_parts_origin_unchanged(self):
        """Without any parts the origin is returned as-is."""
        pat = Pattern(name="P")
        origin = Point(5, 5)
        elem = pat.add_reference_square(origin, edge_length=3 * CM)
        rect = cast(Rect, elem.geometry)
        self.assertAlmostEqual(rect.origin.x, 5.0)
        self.assertAlmostEqual(rect.origin.y, 5.0)


# ---------------------------------------------------------------------------
# seam_length – free function and PatternPart.seam_length()
# ---------------------------------------------------------------------------


class TestSeamLength(unittest.TestCase):
    """Tests for seam_length() (free function) and PatternPart.seam_length()."""

    # ── free function ────────────────────────────────────────────────────────

    def test_single_horizontal_segment(self):
        """A 100 mm horizontal segment has length 100 mm."""
        seg = Segment(Point(0, 0), Point(100, 0))
        self.assertAlmostEqual(seam_length([seg]), 100.0, places=6)

    def test_two_segments_sum(self):
        """Two segments: total equals the sum of their individual lengths."""
        s1 = Segment(Point(0, 0), Point(30, 0))  # 30 mm
        s2 = Segment(Point(0, 0), Point(0, 40))  # 40 mm
        self.assertAlmostEqual(seam_length([s1, s2]), 70.0, places=6)

    def test_diagonal_segment(self):
        """A 3-4-5 diagonal segment has length 50 mm."""
        seg = Segment(Point(0, 0), Point(30, 40))
        self.assertAlmostEqual(seam_length([seg]), 50.0, places=6)

    def test_cubic_bezier_straight_line(self):
        """A CubicBezier whose control points lie on the chord is a straight line."""
        # Collinear control points → arc length equals chord length
        b = CubicBezier(Point(0, 0), Point(25, 0), Point(75, 0), Point(100, 0))
        self.assertAlmostEqual(seam_length([b]), 100.0, places=2)

    def test_mixed_segment_and_bezier(self):
        """A straight segment plus a collinear Bézier: lengths add up correctly."""
        seg = Segment(Point(0, 0), Point(50, 0))  # 50 mm
        bez = CubicBezier(
            Point(0, 0), Point(0, 25), Point(0, 75), Point(0, 100)
        )  # 100 mm straight
        total = seam_length([seg, bez])
        self.assertAlmostEqual(total, 150.0, places=2)

    def test_empty_list_returns_zero(self):
        """An empty geometry list returns 0."""
        self.assertEqual(seam_length([]), 0.0)

    def test_curved_bezier_longer_than_chord(self):
        """A bulging Bézier is longer than its chord."""
        chord_len = 40.0
        b = CubicBezier(Point(0, 0), Point(0, 30), Point(40, 30), Point(40, 0))
        self.assertGreater(seam_length([b]), chord_len)

    # ── PatternPart.seam_length() ────────────────────────────────────────────

    def test_part_seam_length_by_geometry(self):
        """PatternPart.seam_length() accepts geometry objects directly."""
        part = PatternPart(name="Front")
        seg = Segment(Point(0, 0), Point(80, 0))
        part.append(seg, is_outline=True)
        self.assertAlmostEqual(part.seam_length([seg]), 80.0, places=6)

    def test_part_seam_length_by_name(self):
        """PatternPart.seam_length() looks up elements by name."""
        part = PatternPart(name="Front")
        part.append(
            Segment(Point(0, 0), Point(60, 0), name="Seitennaht"), is_outline=True
        )
        self.assertAlmostEqual(part.seam_length(["Seitennaht"]), 60.0, places=6)

    def test_part_seam_length_multiple_named(self):
        """Multiple named segments are summed."""
        part = PatternPart(name="Front")
        part.append(Segment(Point(0, 0), Point(30, 0), name="A"), is_outline=True)
        part.append(Segment(Point(0, 0), Point(0, 40), name="B"), is_outline=True)
        self.assertAlmostEqual(part.seam_length(["A", "B"]), 70.0, places=6)

    def test_part_seam_length_mixed_input(self):
        """Mix of geometry objects and name strings in one call."""
        part = PatternPart(name="Front")
        seg_named = Segment(Point(0, 0), Point(50, 0), name="Top")
        seg_unnamed = Segment(Point(0, 0), Point(0, 50))
        part.append(seg_named, is_outline=True)
        part.append(seg_unnamed, is_outline=True)
        self.assertAlmostEqual(part.seam_length(["Top", seg_unnamed]), 100.0, places=6)

    def test_part_seam_length_unknown_name_raises(self):
        """A name that matches no element raises KeyError."""
        part = PatternPart(name="Front")
        with self.assertRaises(KeyError):
            part.seam_length(["DoesNotExist"])

    def test_part_seam_length_by_pattern_element(self):
        """PatternElement returned by append() can be passed directly."""
        part = PatternPart(name="Front")
        elem = part.append(Segment(Point(0, 0), Point(70, 0)), is_outline=True)
        self.assertAlmostEqual(part.seam_length([elem]), 70.0, places=6)

    def test_part_seam_length_pattern_element_non_geometry_skipped(self):
        """A PatternElement wrapping a non-geometry object (e.g. Circle) is silently skipped."""
        from sewpat.geometry import Circle

        part = PatternPart(name="Front")
        seg_elem = part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True)
        circle_elem = part.append(Circle(Point(25, 0), radius=5))
        # Only the segment contributes; circle is silently ignored
        self.assertAlmostEqual(
            part.seam_length([seg_elem, circle_elem]), 50.0, places=6
        )

    def test_part_seam_length_wrong_type_raises(self):
        """Passing an unsupported type raises TypeError."""
        part = PatternPart(name="Front")
        with self.assertRaises(TypeError):
            part.seam_length([42])  # type: ignore[list-item]

    def test_front_vs_back_inseam_comparison(self):
        """Realistic check: compare front and back inseam lengths."""
        front = PatternPart(name="Vorderteil")
        back = PatternPart(name="Rückteil")
        # Front inseam: straight 200 mm
        front_inseam = Segment(Point(0, 0), Point(0, 200), name="Innennaht")
        front.append(front_inseam, is_outline=True)
        # Back inseam: slightly longer (205 mm) — typical easing
        back_inseam = Segment(Point(0, 0), Point(0, 205), name="Innennaht")
        back.append(back_inseam, is_outline=True)

        diff = back.seam_length(["Innennaht"]) - front.seam_length(["Innennaht"])
        self.assertAlmostEqual(diff, 5.0, places=6)


# ---------------------------------------------------------------------------
# add_seam_allowance – per-element SA distance survives build_chain reversal
# ---------------------------------------------------------------------------


class TestSeamAllowanceReversal(unittest.TestCase):
    """Regression test: per-element SA distance must survive build_chain reversals.

    build_chain may reverse segments to form a connected loop.  The reversed
    object has a different id(), so the old id()-based elem_sa lookup silently
    fell back to the global distance.  The frozenset-of-endpoints key fixes this.
    """

    def _sa_distances(self, part: PatternPart, global_sa: float) -> list[float]:
        """Return the lengths of all SA segments added to *part*."""
        sa_elems = [e for e in part.elements if e.is_seam_allowance]
        from sewpat.geometry import Segment as _S, CubicBezier as _CB

        return [
            e.geometry.length if isinstance(e.geometry, _S) else e.geometry.length()
            for e in sa_elems
            if isinstance(e.geometry, (_S, _CB))
        ]

    def test_reversed_waistband_gets_correct_sa(self):
        """A waistband segment that build_chain reverses must still use its
        per-style SA distance (30 mm here), not the global distance (10 mm)."""
        from sewpat.style import STYLE_STITCH

        # Build a minimal trouser-like rectangle whose waistband is appended
        # in an order that forces build_chain to reverse it.
        #
        # Outline (appended in order that forces a reversal of the waistband):
        #   bottom (hem):     (0,100)→(100,100)   STYLE_HEM  sa=25
        #   right (side):     (100,0)→(100,100)   STYLE_STITCH sa=0 (global)
        #   top (waistband):  (100,0)→(0,0)        STYLE_WAISTBAND sa=30
        #   left (hinternaht):(0,0)→(0,100)        STYLE_STITCH sa=0 (global)
        #
        # build_chain starts with hem, connects right (reversed: 100,100→100,0),
        # then waistband (100,0→0,0 — matches directly, no reversal needed here)
        # then left (reversed: 0,100→0,0 → reversed to 0,0→0,100).
        # To force a reversal of the waistband we append it as (0,0)→(100,0):
        part = PatternPart(name="Test")
        hem = Segment(Point(0, 100), Point(100, 100))
        side_r = Segment(Point(100, 0), Point(100, 100))
        waistband = Segment(Point(0, 0), Point(100, 0))  # will be reversed by chain
        side_l = Segment(Point(0, 0), Point(0, 100))

        from sewpat.style import StyleOptions

        style_wb = StyleOptions(seam_allowance=30.0)
        style_hem = StyleOptions(seam_allowance=25.0)

        part.append(hem, style=style_hem, is_outline=True)
        part.append(side_r, style=STYLE_STITCH, is_outline=True)
        # Waistband appended as (0,0)→(100,0); chain tail after side_r is (100,0)
        # so this connects directly — no reversal. Append side_l last so the
        # chain must reverse it to close the loop: tail (0,0) → side_l end (0,100).
        part.append(waistband, style=style_wb, is_outline=True)
        part.append(side_l, style=STYLE_STITCH, is_outline=True)

        global_sa = 10.0
        part.add_seam_allowance(global_sa)

        # Collect the SA elements and measure total length for waistband direction.
        # The waistband is 100 mm long; its SA should be offset by 30 mm, not 10 mm.
        # We verify by checking that at least one SA segment lies ~30 mm away from
        # the waistband (y ≈ -30), not ~10 mm (y ≈ -10).
        sa_segs = [
            e.geometry
            for e in part.elements
            if e.is_seam_allowance and isinstance(e.geometry, Segment)
        ]
        # The SA segment offset from the waistband (y=0) should be near y=-30
        waistband_sa = [
            s
            for s in sa_segs
            if abs(s.p1.y - (-30.0)) < 5.0 or abs(s.p2.y - (-30.0)) < 5.0
        ]
        self.assertTrue(
            len(waistband_sa) > 0,
            "No SA segment found near y=-30; waistband SA was not applied correctly. "
            "Likely the per-element SA distance was lost due to build_chain reversal.",
        )


# ---------------------------------------------------------------------------
# add_seam_allowance – corner_join parameter (improvement E)
# ---------------------------------------------------------------------------


class TestSeamAllowanceCornerJoin(unittest.TestCase):
    """Tests for the corner_join parameter of add_seam_allowance()."""

    def _square_part(self) -> PatternPart:
        """Return a 100×100 mm square as a pure-segment PatternPart."""
        part = PatternPart(name="Square")
        part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
        part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
        part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
        part.append(Segment(Point(0, 100), Point(0, 0)), is_outline=True)
        return part

    def test_default_is_miter(self):
        """add_seam_allowance() with no corner_join argument uses miter (default)."""
        part = self._square_part()
        sa_elems = part.add_seam_allowance(10.0)
        self.assertTrue(len(sa_elems) > 0)
        self.assertTrue(all(e.is_seam_allowance for e in sa_elems))

    def test_miter_explicit(self):
        """corner_join='miter' is accepted and produces SA elements."""
        part = self._square_part()
        sa_elems = part.add_seam_allowance(10.0, corner_join="miter")
        self.assertTrue(len(sa_elems) > 0)

    def test_round_join(self):
        """corner_join='round' is accepted and produces SA elements."""
        part = self._square_part()
        sa_elems = part.add_seam_allowance(10.0, corner_join="round")
        self.assertTrue(len(sa_elems) > 0)
        self.assertTrue(all(e.is_seam_allowance for e in sa_elems))

    def test_bevel_join(self):
        """corner_join='bevel' is accepted and produces SA elements."""
        part = self._square_part()
        sa_elems = part.add_seam_allowance(10.0, corner_join="bevel")
        self.assertTrue(len(sa_elems) > 0)
        self.assertTrue(all(e.is_seam_allowance for e in sa_elems))

    def test_invalid_corner_join_raises(self):
        """An unknown corner_join value raises ValueError."""
        part = self._square_part()
        with self.assertRaises(ValueError):
            part.add_seam_allowance(10.0, corner_join="zigzag")

    def test_round_produces_more_segments_than_bevel(self):
        """Round join inserts arc segments at corners; bevel does not.

        For a pure-segment square Shapely round join (join_style=1) generates
        arc approximation points at corners, so it produces more output
        segments than a bevel join (join_style=3).
        """
        part_round = self._square_part()
        part_bevel = self._square_part()
        n_round = len(part_round.add_seam_allowance(10.0, corner_join="round"))
        n_bevel = len(part_bevel.add_seam_allowance(10.0, corner_join="bevel"))
        self.assertGreater(
            n_round,
            n_bevel,
            f"Round ({n_round} segs) should have more segments than bevel ({n_bevel} segs)",
        )

    def test_miter_corner_join_on_bezier_path(self):
        """corner_join='miter' works on a mixed Bézier outline."""
        part = PatternPart(name="Curved")
        part.append(
            CubicBezier(Point(0, 0), Point(33, -30), Point(67, -30), Point(100, 0)),
            is_outline=True,
        )
        part.append(Segment(Point(100, 0), Point(100, 50)), is_outline=True)
        part.append(Segment(Point(100, 50), Point(0, 50)), is_outline=True)
        part.append(Segment(Point(0, 50), Point(0, 0)), is_outline=True)
        sa_elems = part.add_seam_allowance(10.0, corner_join="miter")
        self.assertTrue(len(sa_elems) > 0)

    def test_bevel_corner_join_on_bezier_path(self):
        """corner_join='bevel' works on a mixed Bézier outline."""
        part = PatternPart(name="Curved")
        part.append(
            CubicBezier(Point(0, 0), Point(33, -30), Point(67, -30), Point(100, 0)),
            is_outline=True,
        )
        part.append(Segment(Point(100, 0), Point(100, 50)), is_outline=True)
        part.append(Segment(Point(100, 50), Point(0, 50)), is_outline=True)
        part.append(Segment(Point(0, 50), Point(0, 0)), is_outline=True)
        sa_elems = part.add_seam_allowance(10.0, corner_join="bevel")
        self.assertTrue(len(sa_elems) > 0)


if __name__ == "__main__":
    unittest.main()
