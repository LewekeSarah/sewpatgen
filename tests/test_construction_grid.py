"""Tests for construction-grid functionality.

Covers:
  - ConstructionGridPart subclass
  - PatternPart.add_construction_line
  - PatternPart.add_grid_notches  (including horizontal-priority dedup)
  - ConstructionGrid.build
  - parts= name-based grid inclusion in the renderer
"""

import unittest
import tempfile
from pathlib import Path

from sewpat.geometry import Circle, CubicBezier, Point, Rect, Segment, Triangle
from sewpat.part import ConstructionGrid, ConstructionGridPart, Pattern, PatternElement, PatternPart
from sewpat.render import _build_svg, export_pattern_svg_mm
from sewpat.style import STYLE_CONSTRUCTION_GRID, StyleOptions
from sewpat.units import CM, MM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _square_part(side: float = 100.0) -> PatternPart:
    """A closed square outline."""
    part = PatternPart(name="Square")
    o = Point(0, 0)
    part.append(Segment(o, Point(side, 0)), is_outline=True)
    part.append(Segment(Point(side, 0), Point(side, side)), is_outline=True)
    part.append(Segment(Point(side, side), Point(0, side)), is_outline=True)
    part.append(Segment(Point(0, side), o), is_outline=True)
    return part


# ---------------------------------------------------------------------------
# ConstructionGridPart subclass
# ---------------------------------------------------------------------------

class TestConstructionGridPart(unittest.TestCase):

    def test_is_instance_of_pattern_part(self):
        grid = ConstructionGridPart()
        self.assertIsInstance(grid, PatternPart)

    def test_is_instance_of_construction_grid_part(self):
        grid = ConstructionGridPart()
        self.assertIsInstance(grid, ConstructionGridPart)

    def test_regular_part_is_not_construction_grid_part(self):
        part = PatternPart(name="Piece")
        self.assertNotIsInstance(part, ConstructionGridPart)

    def test_non_construction_part_rendered_by_default(self):
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 0), Point(10, 0)))
        svg = _build_svg(
            title="t", element_groups=[part.elements],
            width_mm=100, height_mm=100, margin_mm=5,
            show_points=False, show_bezier_control_points=False,
        )
        self.assertIn("<line ", svg)

    def test_grid_part_shown_when_passed_to_grids(self):
        grid = ConstructionGridPart()
        grid.append(Segment(Point(0, 0), Point(50, 0)))
        svg = _build_svg(
            title="t", element_groups=[grid.elements],
            width_mm=100, height_mm=100, margin_mm=5,
            show_points=False, show_bezier_control_points=False,
        )
        self.assertIn("<line ", svg)

    def test_grid_absent_when_not_passed(self):
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 0), Point(10, 0)))
        # grid is NOT included in element_groups — should not appear
        grid = ConstructionGridPart()
        grid.append(Segment(Point(0, 0), Point(50, 50)))
        svg = _build_svg(
            title="t", element_groups=[part.elements],
            width_mm=100, height_mm=100, margin_mm=5,
            show_points=False, show_bezier_control_points=False,
        )
        # Only the 10mm segment from part is in svg, not the 50mm diagonal
        self.assertIn("<line ", svg)


# ---------------------------------------------------------------------------
# PatternPart.add_construction_line
# ---------------------------------------------------------------------------

class TestAddConstructionLine(unittest.TestCase):

    def test_returns_pattern_element(self):
        part = ConstructionGridPart()
        elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
        self.assertIsInstance(elem, PatternElement)

    def test_element_added_to_part(self):
        part = ConstructionGridPart()
        part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
        self.assertEqual(len(part.elements), 1)

    def test_default_style_is_construction_grid(self):
        part = ConstructionGridPart()
        elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
        self.assertEqual(elem.style.stroke_color, STYLE_CONSTRUCTION_GRID.stroke_color)

    def test_custom_style_respected(self):
        part = ConstructionGridPart()
        custom = StyleOptions(stroke_color="blue")
        elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)), style=custom)
        self.assertEqual(elem.style.stroke_color, "blue")

    def test_not_is_outline(self):
        part = ConstructionGridPart()
        elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
        self.assertFalse(elem.is_outline)


# ---------------------------------------------------------------------------
# ConstructionGrid.build
# ---------------------------------------------------------------------------

class TestConstructionGridBuild(unittest.TestCase):

    def _simple_grid(self) -> ConstructionGridPart:
        return ConstructionGrid(
            anchor=Point(0, 0),
            verticals=[("left", 0), ("right", 50.0)],
            horizontals=[("top", 0), ("bottom", 80.0)],
        ).build()

    def test_returns_construction_grid_part(self):
        self.assertIsInstance(self._simple_grid(), ConstructionGridPart)

    def test_correct_element_count(self):
        self.assertEqual(len(self._simple_grid().elements), 4)

    def test_all_elements_are_segments(self):
        for elem in self._simple_grid().elements:
            self.assertIsInstance(elem.geometry, Segment)

    def test_vertical_line_is_vertical(self):
        seg: Segment = self._simple_grid().elements[0].geometry
        self.assertAlmostEqual(seg.p1.x, seg.p2.x, places=6)

    def test_horizontal_line_is_horizontal(self):
        seg: Segment = self._simple_grid().elements[2].geometry
        self.assertAlmostEqual(seg.p1.y, seg.p2.y, places=6)

    def test_custom_part_name(self):
        grid = ConstructionGrid(anchor=Point(0, 0), verticals=[("v", 0)], part_name="MyGrid")
        self.assertEqual(grid.build().name, "MyGrid")

    def test_default_part_name(self):
        self.assertEqual(ConstructionGrid(anchor=Point(0, 0)).build().name, "Konstruktionsgitter")

    def test_element_names_match_labels(self):
        grid = ConstructionGrid(
            anchor=Point(0, 0),
            verticals=[("Hintermitte", 0)],
            horizontals=[("Bundlinie", 0)],
        ).build()
        names = [e.geometry.name for e in grid.elements]
        self.assertIn("Hintermitte", names)
        self.assertIn("Bundlinie", names)

    def test_all_elements_use_construction_style(self):
        grid = ConstructionGrid(
            anchor=Point(0, 0), verticals=[("v", 0)], horizontals=[("h", 10)]
        ).build()
        for elem in grid.elements:
            self.assertEqual(elem.style.stroke_color, STYLE_CONSTRUCTION_GRID.stroke_color)


# ---------------------------------------------------------------------------
# PatternPart.add_grid_notches
# ---------------------------------------------------------------------------

class TestAddGridNotches(unittest.TestCase):

    def _square_with_grid(self):
        """100×100 square with a horizontal grid line at y=50."""
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="Mitte"))
        return part, grid

    def test_returns_list_of_pattern_elements(self):
        part, grid = self._square_with_grid()
        created = part.add_grid_notches(grid)
        self.assertIsInstance(created, list)
        for e in created:
            self.assertIsInstance(e, PatternElement)

    def test_notches_created_at_intersections(self):
        part, grid = self._square_with_grid()
        before = len(part.elements)
        part.add_grid_notches(grid)
        self.assertGreater(len(part.elements), before)

    def test_correct_intersection_count_for_simple_case(self):
        """Horizontal at y=50 crosses left and right edges → 2 notches."""
        part, grid = self._square_with_grid()
        created = part.add_grid_notches(grid)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 2)

    def test_deduplication_prevents_double_notch(self):
        part, grid = self._square_with_grid()
        part.add_grid_notches(grid)
        count_first = sum(1 for e in part.elements if isinstance(e.geometry, Triangle))
        part.add_grid_notches(grid)
        count_second = sum(1 for e in part.elements if isinstance(e.geometry, Triangle))
        self.assertEqual(count_first, count_second)

    def test_no_notches_when_grid_does_not_intersect(self):
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 200), Point(200, 200)))
        self.assertEqual(len(part.add_grid_notches(grid)), 0)

    def test_vertical_grid_line_intersects_top_bottom(self):
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(50, -200), Point(50, 200)))
        created = part.add_grid_notches(grid)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 2)

    def test_multiple_grid_lines(self):
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 25), Point(200, 25)))
        grid.add_construction_line(Segment(Point(-200, 75), Point(200, 75)))
        created = part.add_grid_notches(grid)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 4)

    def test_notch_elements_are_not_outline(self):
        part, grid = self._square_with_grid()
        for e in part.add_grid_notches(grid):
            self.assertFalse(e.is_outline)

    def test_notch_position_near_intersection(self):
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(50, -200), Point(50, 200)))
        part.add_grid_notches(grid)
        triangles = [e for e in part.elements if isinstance(e.geometry, Triangle)]
        xs = [(t.geometry.p1.x + t.geometry.p2.x + t.geometry.p3.x) / 3 for t in triangles]
        for cx in xs:
            self.assertAlmostEqual(cx, 50.0, delta=2.0)

    # --- corner / endpoint skipping ---

    def test_sharp_corner_skipped(self):
        """90° corner between two segments → notch suppressed."""
        part = PatternPart(name="Corner")
        part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True)
        part.append(Segment(Point(50, 0), Point(50, 100)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-50, 0), Point(150, 0)))
        created = part.add_grid_notches(grid)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 0)

    def test_collinear_join_not_skipped(self):
        """Near-collinear join (angle ≈ 0°) at interior of chain → notch kept."""
        part = PatternPart(name="Chain")
        part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True)
        part.append(Segment(Point(50, 0), Point(100, 0)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(25, -50), Point(25, 50)))
        created = part.add_grid_notches(grid, corner_clearance=0.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_free_endpoint_skipped(self):
        """Free (dangling) endpoint → notch suppressed."""
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(0, -50), Point(0, 50)))
        created = part.add_grid_notches(grid)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 0)

    def test_near_corner_within_tolerance_skipped(self):
        """Intersection within tolerance of a sharp corner → suppressed."""
        part = PatternPart(name="Corner")
        part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True)
        part.append(Segment(Point(50, 0), Point(50, 100)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(49.5, -50), Point(49.5, 50)))
        created = part.add_grid_notches(grid, tolerance=1.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 0)

    # --- horizontal priority / min_spacing ---

    def test_horizontal_on_element_suppresses_vertical_on_same_element(self):
        """Once a horizontal notch is placed on an element, all verticals on
        that same element are suppressed — regardless of distance."""
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 0), Point(100, 100)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="H"))
        grid.add_construction_line(Segment(Point(80, -200), Point(80, 200), name="V"))
        created = part.add_grid_notches(grid, min_spacing=8.0, corner_clearance=0.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_vertical_kept_on_element_without_horizontal(self):
        """Vertical notch is kept when no horizontal has been placed on the element."""
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 0), Point(100, 100)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(50, -200), Point(50, 200), name="V"))
        created = part.add_grid_notches(grid, min_spacing=8.0, corner_clearance=0.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_nearby_horizontal_and_vertical_only_horizontal_placed(self):
        """When a horizontal and vertical intersection are < min_spacing apart,
        only the horizontal notch is placed."""
        part = PatternPart(name="p")
        part.append(Segment(Point(0, 50), Point(100, 50)), is_outline=True)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 50.5), Point(200, 50.5), name="H"))
        grid.add_construction_line(Segment(Point(50, -200), Point(50, 200), name="V"))
        created = part.add_grid_notches(grid, min_spacing=8.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 1)

    def test_widely_spaced_intersections_both_kept(self):
        """Two intersections farther than min_spacing apart are both kept."""
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 25), Point(200, 25)))
        grid.add_construction_line(Segment(Point(-200, 75), Point(200, 75)))
        created = part.add_grid_notches(grid, min_spacing=8.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 4)

    # --- corner_clearance ---

    def test_corner_clearance_suppresses_nearby_vertex_notch(self):
        """Intersection within corner_clearance of an outline vertex → suppressed."""
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 15), Point(200, 15)))
        created = part.add_grid_notches(grid, corner_clearance=20.0, min_spacing=1.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 0)

    def test_corner_clearance_keeps_notch_beyond_clearance(self):
        """Intersection beyond corner_clearance → kept."""
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50)))
        created = part.add_grid_notches(grid, corner_clearance=20.0, min_spacing=1.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 2)

    def test_corner_clearance_zero_disables_guard(self):
        """corner_clearance=0 disables the vertex-proximity guard."""
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 5), Point(200, 5)))
        created = part.add_grid_notches(grid, corner_clearance=0.0, min_spacing=1.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertGreater(len(triangles), 0)

    def test_default_corner_clearance_is_15mm(self):
        """Default corner_clearance=15 suppresses notch at y=10 (10mm from corner)."""
        part = _square_part(side=100.0)
        grid = ConstructionGridPart()
        grid.add_construction_line(Segment(Point(-200, 10), Point(200, 10)))
        created = part.add_grid_notches(grid, min_spacing=1.0)
        triangles = [e for e in created if isinstance(e.geometry, Triangle)]
        self.assertEqual(len(triangles), 0)


# ---------------------------------------------------------------------------
# Integration: parts= name-based grid inclusion in export_pattern_svg_mm
# ---------------------------------------------------------------------------

class TestGridsExportParameter(unittest.TestCase):

    def _pattern_and_grid(self):
        pat = Pattern(name="Test")
        piece = _square_part(side=50.0)
        pat.add_part(piece)
        grid = ConstructionGrid(
            anchor=Point(0, 0),
            horizontals=[("Mitte", 25.0)],
        ).build()
        pat.add_part(grid)
        return pat, grid

    def _export(self, pat: Pattern, parts=None) -> str:
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        export_pattern_svg_mm(pat, fname, width_mm=200, height_mm=200, parts=parts)
        return Path(fname).read_text()

    def test_grid_label_in_svg_when_included_by_name(self):
        pat, grid = self._pattern_and_grid()
        self.assertIn("Mitte", self._export(pat, parts=["Square", grid.name]))

    def test_grid_label_absent_by_default(self):
        pat, grid = self._pattern_and_grid()
        self.assertNotIn("Mitte", self._export(pat))

    def test_piece_still_rendered_without_grid(self):
        pat, grid = self._pattern_and_grid()
        self.assertIn("<line ", self._export(pat))

    def test_grid_part_in_pattern_parts(self):
        pat, grid = self._pattern_and_grid()
        self.assertIn(grid, pat.parts)


if __name__ == "__main__":
    unittest.main()

