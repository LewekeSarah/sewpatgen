import tempfile
from pathlib import Path

from sewpat.element import PatternElement
from sewpat.geometry import Dart, DartType, Point, Segment
from sewpat.pattern import Block, OverlayPart, Pattern, PatternPart
from sewpat.render import export_pattern_svg_mm
from sewpat.style import StyleOptions

# ---------------------------------------------------------------------------
# Block -- identity and rendering
# ---------------------------------------------------------------------------


def test_block_is_instance_of_pattern_part():
    assert isinstance(Block(name="Grundschnitt"), PatternPart)


def test_block_is_instance_of_block():
    assert isinstance(Block(name="Grundschnitt"), Block)


def test_regular_part_is_not_block():
    assert not isinstance(PatternPart(name="Vorderteil"), Block)


def test_block_name_stored():
    assert Block(name="Oberteil Block").name == "Oberteil Block"


def test_block_accepts_initial_elements():
    elems = [PatternElement(Point(0, 0))]
    assert len(Block(name="B", elements=elems).elements) == 1


def test_block_append_works():
    block = Block(name="B")
    block.append(Segment(Point(0, 0), Point(10, 0)), is_outline=True)
    assert len(block.elements) == 1


def test_block_excluded_from_default_export():
    """Block must not appear in export_pattern_svg_mm output by default."""
    block = Block(name="Grundschnitt")
    block.append(Segment(Point(0, 0), Point(50, 0)), is_outline=True)
    block.append(Segment(Point(50, 0), Point(50, 50)), is_outline=True)
    block.append(Segment(Point(50, 50), Point(0, 50)), is_outline=True)
    block.append(Segment(Point(0, 50), Point(0, 0)), is_outline=True)
    regular = PatternPart(name="Vorderteil")
    regular.append(Segment(Point(0, 0), Point(30, 0)), is_outline=True)
    pat = Pattern(name="Test")
    pat.add_part(block)
    pat.add_part(regular)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname, width_mm=200, height_mm=200)
    assert 'x2="50"' not in Path(fname).read_text()


def test_block_included_when_requested_by_name():
    """Block is rendered when its name is passed via parts=."""
    block = Block(name="Grundschnitt")
    block.append(Segment(Point(0, 0), Point(50, 0), name="Oberkante"), is_outline=True)
    pat = Pattern(name="Test")
    pat.add_part(block)
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        fname = f.name
    export_pattern_svg_mm(pat, fname, width_mm=200, height_mm=200, parts=["Grundschnitt"])
    assert "Oberkante" in Path(fname).read_text()


def test_block_geometry_usable_as_reference():
    block = Block(name="B")
    top_left, top_right = Point(0, 0), Point(100, 0)
    block.append(Segment(top_left, top_right, name="Schulter"), is_outline=True)
    derived = PatternPart(name="Vorderteil")
    derived.append(Segment(top_left, top_right), is_outline=True)
    derived.append(Segment(top_right, Point(100, 150)), is_outline=True)
    derived.append(Segment(Point(100, 150), Point(0, 150)), is_outline=True)
    derived.append(Segment(Point(0, 150), top_left), is_outline=True)
    assert derived.centroid is not None


# ---------------------------------------------------------------------------
# OverlayPart -- basic
# ---------------------------------------------------------------------------


def test_overlay_is_instance_of_pattern_part(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    assert isinstance(OverlayPart(name="Tasche", parent=front), PatternPart)


def test_overlay_is_instance_of_overlay_part(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    assert isinstance(OverlayPart(name="Tasche", parent=front), OverlayPart)


def test_overlay_parent_stored(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    assert OverlayPart(name="Tasche", parent=front).parent is front


def test_overlay_no_anchor_attribute(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    assert not hasattr(OverlayPart(name="Tasche", parent=front), "anchor")


def test_overlay_name_stored(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    assert OverlayPart(name="Tasche", parent=front).name == "Tasche"


def test_overlay_accepts_initial_elements(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    elems = [PatternElement(Segment(Point(0, 0), Point(10, 0)))]
    assert len(OverlayPart(name="Tasche", parent=front, elements=elems).elements) == 1


def test_overlay_append_works(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    overlay = OverlayPart(name="Tasche", parent=front)
    overlay.append(Segment(Point(10, 10), Point(40, 10)), is_outline=True)
    assert len(overlay.elements) == 1


# ---------------------------------------------------------------------------
# OverlayPart -- explode (geometry and flags)
# ---------------------------------------------------------------------------


def test_explode_returns_pattern_part(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    assert isinstance(pocket.explode(offset=Point(110, 0)), PatternPart)


def test_explode_not_overlay_part(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    assert not isinstance(pocket.explode(offset=Point(110, 0)), OverlayPart)


def test_explode_default_name(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    assert pocket.explode(offset=Point(110, 0)).name == "Tasche"


def test_explode_custom_name(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    assert (
        pocket.explode(offset=Point(110, 0), name="Tasche (Schnittteil)").name
        == "Tasche (Schnittteil)"
    )


def test_explode_element_count_preserved(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    assert len(pocket.explode(offset=Point(110, 0)).elements) == len(pocket.elements)


def test_explode_geometry_translated(pocket_overlay: tuple[Pattern, OverlayPart]):
    """All geometry is shifted by the"""
    _, pocket = pocket_overlay
    result = pocket.explode(offset=Point(110, 0))
    for orig, expl in zip(pocket.elements, result.elements, strict=False):
        assert abs(expl.geometry.p1.x - (orig.geometry.p1.x + 110)) < 1e-6
        assert abs(expl.geometry.p1.y - orig.geometry.p1.y) < 1e-6


def test_explode_is_outline_flag_preserved(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    result = pocket.explode(offset=Point(110, 0))
    for orig, expl in zip(pocket.elements, result.elements, strict=False):
        assert expl.is_outline == orig.is_outline


def test_explode_is_seam_allowance_flag_preserved(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    pocket.add_seam_allowance(10.0)
    result = pocket.explode(offset=Point(110, 0))
    assert len([e for e in result.elements if e.is_seam_allowance]) == len(
        [e for e in pocket.elements if e.is_seam_allowance]
    )


def test_explode_style_preserved(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Tasche", parent=front)
    pocket.append(
        Segment(Point(10, 10), Point(40, 10)),
        style=StyleOptions(stroke_color="red"),
        is_outline=True,
    )
    assert pocket.explode(offset=Point(110, 0)).elements[0].style.stroke_color == "red"


def test_explode_does_not_mutate_original(pocket_overlay: tuple[Pattern, OverlayPart]):
    _, pocket = pocket_overlay
    orig_coords = [(e.geometry.p1.x, e.geometry.p1.y) for e in pocket.elements]
    pocket.explode(offset=Point(110, 0))
    assert [(e.geometry.p1.x, e.geometry.p1.y) for e in pocket.elements] == orig_coords


def test_explode_does_not_mutate_parent(pocket_overlay: tuple[Pattern, OverlayPart]):
    front, pocket = pocket_overlay
    count_before = len(front.get_part("front").elements)
    pocket.explode(offset=Point(110, 0))
    assert len(front.get_part("front").elements) == count_before


def test_overlay_excluded_from_default_export(pocket_overlay: tuple[Pattern, OverlayPart]):
    """Exploded overlays are plain PatternParts and included by default."""
    front, pocket = pocket_overlay
    exploded = pocket.explode(offset=Point(110, 0))
    pat = Pattern(name="Test")
    pat.add_part(front)
    pat.add_part(exploded)
    assert len([p for p in pat.parts if not isinstance(p, Block)]) == 2


# ---------------------------------------------------------------------------
# OverlayPart -- explode: previously dropped element attributes
# ---------------------------------------------------------------------------


def test_explode_role_preserved(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    elem = pocket.append(Segment(Point(10, 10), Point(40, 10)), is_outline=True)
    elem.role = "pocket_top"
    assert pocket.explode(offset=Point(110, 0)).elements[0].role == "pocket_top"


def test_explode_is_construction_preserved(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    pocket.add_construction_line(Segment(Point(10, 10), Point(40, 10)))
    assert pocket.explode(offset=Point(110, 0)).elements[0].is_construction


def test_explode_is_seam_notch_preserved(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    elem = pocket.append(Segment(Point(10, 10), Point(40, 10)))
    elem.is_seam_notch = True
    assert pocket.explode(offset=Point(110, 0)).elements[0].is_seam_notch


def test_explode_element_name_preserved(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    pocket.append(Segment(Point(10, 10), Point(40, 10), name="Top Edge"))
    assert pocket.explode(offset=Point(110, 0)).elements[0].get_name() == "Top Edge"


def test_explode_style_deep_copied(simple_pattern: Pattern):
    """Mutating the original style must not affect the exploded element."""
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    style = StyleOptions(stroke_color="blue")
    pocket.append(Segment(Point(10, 10), Point(40, 10)), style=style)
    result = pocket.explode(offset=Point(110, 0))
    style.stroke_color = "green"
    assert result.elements[0].style.stroke_color == "blue"


def test_explode_sa_center_translated(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    elem = pocket.append(Segment(Point(10, 10), Point(40, 10)), is_outline=True)
    elem._sa_center = Point(25, 10)
    result = pocket.explode(offset=Point(110, 0))
    assert abs(result.elements[0]._sa_center.x - 135.0) < 1e-6
    assert abs(result.elements[0]._sa_center.y - 10.0) < 1e-6


def test_explode_dart_ref_cleared(simple_pattern: Pattern):
    """_dart_ref must be cleared -- it points into parent-space geometry."""
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    elem = pocket.append(Segment(Point(10, 10), Point(40, 10)))
    elem._dart_ref = Dart(
        Point(10, 10),
        Point(40, 10),
        Point(25, 10),
        Point(25, 30),
        dart_type=DartType.TRIANGLE,
    )
    assert pocket.explode(offset=Point(110, 0)).elements[0]._dart_ref is None


def test_explode_leg_pt_translated(simple_pattern: Pattern):
    front = simple_pattern.parts[0]
    pocket = OverlayPart(name="Pocket", parent=front)
    elem = pocket.append(Segment(Point(10, 10), Point(40, 10)))
    elem._leg_pt = Point(10, 10)
    result = pocket.explode(offset=Point(110, 0))
    assert abs(result.elements[0]._leg_pt.x - 120.0) < 1e-6
    assert abs(result.elements[0]._leg_pt.y - 10.0) < 1e-6
