"""Tests for construction-grid functionality.

Covers:
  - ConstructionGridPart subclass
  - PatternPart.add_construction_line
  - PatternPart.add_grid_notches  (including horizontal-priority dedup)
  - ConstructionGrid.build
  - parts= name-based grid inclusion in the renderer
"""

import tempfile
from pathlib import Path

import pytest

from sewpat.element import PatternElement
from sewpat.geometry import Point, Segment, Triangle
from sewpat.pattern import (
    ConstructionGrid,
    ConstructionGridPart,
    Pattern,
    PatternPart,
)
from sewpat.render import _build_svg, export_pattern_svg_mm
from sewpat.style import STYLE_CONSTRUCTION_GRID, StyleOptions

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


def test_construction_grid_part_is_instance_of_pattern_part():
    grid = ConstructionGridPart()
    assert isinstance(grid, PatternPart)


def test_construction_grid_part_is_instance_of_construction_grid_part():
    grid = ConstructionGridPart()
    assert isinstance(grid, ConstructionGridPart)


def test_regular_part_is_not_construction_grid_part():
    part = PatternPart(name="Piece")
    assert not isinstance(part, ConstructionGridPart)


def test_non_construction_part_rendered_by_default():
    part = PatternPart(name="p")
    part.append(Segment(Point(0, 0), Point(10, 0)))
    svg = _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )
    assert "<line " in svg


def test_grid_part_shown_when_passed_to_grids():
    grid = ConstructionGridPart()
    grid.append(Segment(Point(0, 0), Point(50, 0)))
    svg = _build_svg(
        title="t",
        element_groups=[grid.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=True,
        show_bezier_control_points=False,
    )
    assert "<line " in svg


def test_grid_absent_when_not_passed():
    part = PatternPart(name="p")
    part.append(Segment(Point(0, 0), Point(10, 0)))
    grid = ConstructionGridPart()
    grid.append(Segment(Point(0, 0), Point(50, 50)))
    svg = _build_svg(
        title="t",
        element_groups=[part.elements],
        width_mm=100,
        height_mm=100,
        margin_mm=5,
        show_construction=False,
        show_bezier_control_points=False,
    )
    assert "<line " in svg


# ---------------------------------------------------------------------------
# PatternPart.add_construction_line
# ---------------------------------------------------------------------------


def test_add_construction_line_returns_pattern_element():
    part = ConstructionGridPart()
    elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
    assert isinstance(elem, PatternElement)


def test_add_construction_line_element_added_to_part():
    part = ConstructionGridPart()
    part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
    assert len(part.elements) == 1


def test_add_construction_line_default_style_is_construction_grid():
    part = ConstructionGridPart()
    elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
    assert elem.style.stroke_color == STYLE_CONSTRUCTION_GRID.stroke_color


def test_add_construction_line_custom_style_respected():
    part = ConstructionGridPart()
    custom = StyleOptions(stroke_color="blue")
    elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)), style=custom)
    assert elem.style.stroke_color == "blue"


def test_add_construction_line_not_is_outline():
    part = ConstructionGridPart()
    elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
    assert not elem.is_outline


def test_add_construction_line_is_construction_on_grid_part():
    """Elements added via add_construction_line are always is_construction=True."""
    part = ConstructionGridPart()
    elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
    assert elem.is_construction


def test_add_construction_line_is_construction_on_plain_part():
    """is_construction=True even when the host part is a plain PatternPart."""
    part = PatternPart(name="Block")
    elem = part.add_construction_line(Segment(Point(0, 0), Point(10, 0)))
    assert elem.is_construction


# ---------------------------------------------------------------------------
# ConstructionGrid.build
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_grid() -> ConstructionGridPart:
    return ConstructionGrid(
        anchor=Point(0, 0),
        verticals=[("left", 0), ("right", 50.0)],
        horizontals=[("top", 0), ("bottom", 80.0)],
    ).build()


def test_construction_grid_build_returns_construction_grid_part(simple_grid):
    assert isinstance(simple_grid, ConstructionGridPart)


def test_construction_grid_build_correct_element_count(simple_grid):
    assert len(simple_grid.elements) == 4


def test_construction_grid_build_all_elements_are_segments(simple_grid):
    for elem in simple_grid.elements:
        assert isinstance(elem.geometry, Segment)


def test_construction_grid_build_vertical_line_is_vertical(simple_grid):
    seg: Segment = simple_grid.elements[0].geometry
    assert seg.p1.x == pytest.approx(seg.p2.x, abs=1e-6)


def test_construction_grid_build_horizontal_line_is_horizontal(simple_grid):
    seg: Segment = simple_grid.elements[2].geometry
    assert seg.p1.y == pytest.approx(seg.p2.y, abs=1e-6)


def test_construction_grid_build_custom_part_name():
    grid = ConstructionGrid(anchor=Point(0, 0), verticals=[("v", 0)], part_name="MyGrid")
    assert grid.build().name == "MyGrid"


def test_construction_grid_build_default_part_name():
    assert ConstructionGrid(anchor=Point(0, 0)).build().name == "Grid"


def test_construction_grid_build_element_names_match_labels():
    grid = ConstructionGrid(
        anchor=Point(0, 0),
        verticals=[("Hintermitte", 0)],
        horizontals=[("Bundlinie", 0)],
    ).build()
    names = [e.geometry.name for e in grid.elements]
    assert "Hintermitte" in names
    assert "Bundlinie" in names


def test_construction_grid_build_all_elements_use_construction_style():
    grid = ConstructionGrid(
        anchor=Point(0, 0), verticals=[("v", 0)], horizontals=[("h", 10)]
    ).build()
    for elem in grid.elements:
        assert elem.style.stroke_color == STYLE_CONSTRUCTION_GRID.stroke_color


# ---------------------------------------------------------------------------
# PatternPart.add_grid_notches
# ---------------------------------------------------------------------------


@pytest.fixture
def square_with_grid():
    """100×100 square (all edges role="side") + horizontal grid at y=50."""
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="Mitte"))
    return part, grid


# ── Basic behaviour ──────────────────────────────────────────────────────────


def test_add_grid_notches_returns_list_of_pattern_elements(square_with_grid):
    part, grid = square_with_grid
    created = part.add_grid_notches(grid, role_map={"side": ["Mitte"]})
    assert isinstance(created, list)
    for e in created:
        assert isinstance(e, PatternElement)


def test_add_grid_notches_notches_created_at_intersections(square_with_grid):
    part, grid = square_with_grid
    before = len(part.elements)
    part.add_grid_notches(grid, role_map={"side": ["Mitte"]})
    assert len(part.elements) > before


def test_add_grid_notches_correct_intersection_count_for_simple_case(square_with_grid):
    """Horizontal at y=50 crosses left and right edges → 2 notch triangles."""
    part, grid = square_with_grid
    created = part.add_grid_notches(grid, role_map={"side": ["Mitte"]})
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 2


def test_add_grid_notches_deduplication_prevents_double_notch(square_with_grid):
    part, grid = square_with_grid
    part.add_grid_notches(grid, role_map={"side": ["Mitte"]})
    count_first = sum(1 for e in part.elements if isinstance(e.geometry, Triangle))
    part.add_grid_notches(grid, role_map={"side": ["Mitte"]})
    count_second = sum(1 for e in part.elements if isinstance(e.geometry, Triangle))
    assert count_first == count_second


def test_add_grid_notches_no_notches_when_grid_does_not_intersect():
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 200), Point(200, 200), name="Far"))
    assert len(part.add_grid_notches(grid, role_map={"side": ["Far"]})) == 0


def test_add_grid_notches_no_notches_when_role_not_on_part():
    """If no elements carry the mapped role, no notches are placed."""
    part = _square_part(side=100.0)  # elements have no role
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="Mitte"))
    assert len(part.add_grid_notches(grid, role_map={"side": ["Mitte"]})) == 0


def test_add_grid_notches_empty_grid_name_list_places_no_notches():
    """role_map with empty list for a role → role explicitly suppressed."""
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="Mitte"))
    assert len(part.add_grid_notches(grid, role_map={"side": []})) == 0


def test_add_grid_notches_vertical_grid_line_intersects_top_bottom():
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(50, -200), Point(50, 200), name="V"))
    created = part.add_grid_notches(grid, role_map={"side": ["V"]}, min_spacing=1.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 2


def test_add_grid_notches_multiple_grid_lines():
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 25), Point(200, 25), name="L25"))
    grid.add_construction_line(Segment(Point(-200, 75), Point(200, 75), name="L75"))
    created = part.add_grid_notches(grid, role_map={"side": ["L25", "L75"]})
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 4


def test_add_grid_notches_notch_elements_are_not_outline(square_with_grid):
    part, grid = square_with_grid
    for e in part.add_grid_notches(grid, role_map={"side": ["Mitte"]}):
        assert not e.is_outline


def test_add_grid_notches_notch_position_near_intersection():
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(50, -200), Point(50, 200), name="V"))
    part.add_grid_notches(grid, role_map={"side": ["V"]}, min_spacing=1.0)
    triangles = [e for e in part.elements if isinstance(e.geometry, Triangle)]
    xs = [(t.geometry.p1.x + t.geometry.p2.x + t.geometry.p3.x) / 3 for t in triangles]
    for cx in xs:
        assert cx == pytest.approx(50.0, abs=2.0)


def test_add_grid_notches_unknown_grid_name_warns():
    """Referencing a non-existent grid element name emits a UserWarning."""
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="Real"))
    with pytest.warns(UserWarning):
        part.add_grid_notches(grid, role_map={"side": ["NoSuchLine"]})


# ── Corner / endpoint skipping ───────────────────────────────────────────────


def test_add_grid_notches_sharp_corner_skipped():
    """Intersection exactly at a boundary vertex (corner) is suppressed."""
    part = PatternPart(name="Corner")
    part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True, role="side")
    part.append(Segment(Point(50, 0), Point(50, 100)), is_outline=True)
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-50, 0), Point(150, 0), name="H"))
    created = part.add_grid_notches(grid, role_map={"side": ["H"]})
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 0


def test_add_grid_notches_collinear_join_not_skipped():
    """Internal vertex between two same-role edges → notch kept."""
    part = PatternPart(name="Chain")
    part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True, role="side")
    part.append(Segment(Point(50, 0), Point(100, 0)), is_outline=True, role="side")
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(25, -50), Point(25, 50), name="V"))
    created = part.add_grid_notches(grid, role_map={"side": ["V"]}, min_spacing=1.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 1


def test_add_grid_notches_near_corner_within_tolerance_skipped():
    part = PatternPart(name="Corner")
    part.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True, role="side")
    part.append(Segment(Point(50, 0), Point(50, 100)), is_outline=True)
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(49.5, -50), Point(49.5, 50), name="V"))
    created = part.add_grid_notches(grid, role_map={"side": ["V"]}, min_spacing=1.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 1


# ── min_spacing deduplication ────────────────────────────────────────────────


def test_add_grid_notches_widely_spaced_intersections_both_kept():
    """Two intersections farther than min_spacing apart are both placed."""
    part = _square_part(side=100.0)
    for e in part.elements:
        e.role = "side"
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 25), Point(200, 25), name="L25"))
    grid.add_construction_line(Segment(Point(-200, 75), Point(200, 75), name="L75"))
    created = part.add_grid_notches(grid, role_map={"side": ["L25", "L75"]}, min_spacing=8.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 4


# ── corner_clearance ─────────────────────────────────────────────────────────


def test_add_grid_notches_corner_clearance_suppresses_nearby_vertex_notch():
    part = PatternPart(name="p")
    o = Point(0, 0)
    part.append(Segment(o, Point(100, 0)), is_outline=True)
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True, role="side")
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), o), is_outline=True, role="side")
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 15), Point(200, 15), name="L"))
    created = part.add_grid_notches(grid, role_map={"side": ["L"]}, min_spacing=1.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 2


def test_add_grid_notches_corner_clearance_keeps_notch_beyond_clearance():
    """Intersection away from vertices is kept."""
    part = PatternPart(name="p")
    o = Point(0, 0)
    part.append(Segment(o, Point(100, 0)), is_outline=True)
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True, role="side")
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), o), is_outline=True, role="side")
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 50), Point(200, 50), name="Mid"))
    created = part.add_grid_notches(grid, role_map={"side": ["Mid"]}, min_spacing=1.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) == 2


def test_add_grid_notches_corner_clearance_zero_disables_guard():
    """Notches are placed even close to vertices with min_spacing."""
    part = PatternPart(name="p")
    o = Point(0, 0)
    part.append(Segment(o, Point(100, 0)), is_outline=True)
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True, role="side")
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(Segment(Point(0, 100), o), is_outline=True, role="side")
    grid = ConstructionGridPart()
    grid.add_construction_line(Segment(Point(-200, 5), Point(200, 5), name="L"))
    created = part.add_grid_notches(grid, role_map={"side": ["L"]}, min_spacing=1.0)
    triangles = [e for e in created if isinstance(e.geometry, Triangle)]
    assert len(triangles) > 0


# ---------------------------------------------------------------------------
# Integration: parts= name-based grid inclusion in export_pattern_svg_mm
# ---------------------------------------------------------------------------


@pytest.fixture
def pattern_and_grid():
    pat = Pattern(name="Test")
    piece = _square_part(side=50.0)
    pat.add_part(piece)
    grid = ConstructionGrid(
        anchor=Point(0, 0),
        horizontals=[("Mitte", 25.0)],
    ).build()
    pat.add_part(grid)
    return pat, grid


def _export(pat: Pattern, parts=None) -> str:
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname, width_mm=200, height_mm=200, parts=parts)
    return Path(fname).read_text()


def test_grids_export_grid_label_in_svg_when_included_by_name(pattern_and_grid):
    pat, grid = pattern_and_grid
    assert "Mitte" in _export(pat, parts=["Square", grid.name])


def test_grids_export_grid_label_absent_by_default(pattern_and_grid):
    pat, grid = pattern_and_grid
    assert "Mitte" not in _export(pat)


def test_grids_export_piece_still_rendered_without_grid(pattern_and_grid):
    pat, grid = pattern_and_grid
    assert "<line " in _export(pat)


def test_grids_export_grid_part_in_pattern_parts(pattern_and_grid):
    pat, grid = pattern_and_grid
    assert grid in pat.parts
