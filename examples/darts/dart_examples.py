#!/usr/bin/env python3
"""Dart Examples — sewpat library showcase.

This script generates seven SVG files, each demonstrating a different aspect
of dart support in sewpat:

    01_outer_dart_explicit_depth.svg   — Outer seam dart, depth given directly
    02_outer_dart_reference_point.svg  — Outer dart aimed at a reference point
                                         (bust-point style)
    03_inner_dart_rhombus.svg          — Inner/reverse dart, rhombus rendering
    04_dart_split.svg                  — One dart split into two sub-darts
    05_dart_transfer.svg               — Dart translated along the seam edge
    06_curved_dart.svg                 — Bust dart with curved CubicBezier stitch
                                         legs (curved-seam / princess-style dart)
    07_dart_seam_allowance.svg         — Bust dart with 10 mm seam allowance

Each file uses the same simple rectangular bodice-front block with a
construction grid so the geometry is easy to follow.

Usage (run from repo root):
    python examples/darts/dart_examples.py
"""

from pathlib import Path

import numpy as np

from sewpat import (
    MM,
    STYLE_DART_FOLD,
    STYLE_DART_STITCH,
    STYLE_FOLD,
    STYLE_PRECISION_POINT,
    STYLE_STITCH,
    Dart,
    DartType,
    Pattern,
    PatternElement,
    PatternPart,
    Point,
    Segment,
)
from sewpat.geometry import CubicBezier, intersect
from sewpat.pattern import ConstructionGrid
from sewpat.render import export_pattern_svg_mm
from sewpat.style import (
    STYLE_CONSTRUCTION_GRID,
    STYLE_GRAINLINE,
    StyleOptions,
)

# DIN A4 canvas size in mm
_A4_W, _A4_H = 210.0, 297.0

OUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Stroke-width scaling
# The pattern block is small (120 × 180 mm on an A4 canvas), so the default
# 0.5 mm strokes look disproportionately thick.  All styles used in these
# examples are scaled to half their original width.
# ---------------------------------------------------------------------------


def _scaled(style: StyleOptions, factor: float = 0.5) -> StyleOptions:
    """Return a copy of *style* with stroke_width multiplied by *factor*."""
    import copy

    s = copy.copy(style)
    s.stroke_width = round(style.stroke_width * factor, 4)
    return s


# Halved presets used throughout all examples
_FOLD = _scaled(STYLE_FOLD)
_STITCH = _scaled(STYLE_STITCH)
_DART_STITCH = _scaled(STYLE_DART_STITCH)
_DART_FOLD = _scaled(STYLE_DART_FOLD)
_PRECISION = _scaled(STYLE_PRECISION_POINT)
_GRAINLINE = _scaled(STYLE_GRAINLINE)
_AUX = _scaled(STYLE_CONSTRUCTION_GRID)
_REF_STYLE = StyleOptions(stroke_color="#bbbbbb", stroke_width=0.15, dash_array=[3.0, 3.0])

# ---------------------------------------------------------------------------
# Shared bodice-front dimensions (mm)
# ---------------------------------------------------------------------------
PIECE_W = 120 * MM  # half-front width
PIECE_H = 180 * MM  # front length (shoulder → hem)
WAIST_Y = 110 * MM  # distance from top to waist line
BUST_Y = 65 * MM  # distance from top to bust line
BUST_X = 45 * MM  # bust point x from left edge (CF)

ANCHOR = Point(15 * MM, 15 * MM)


# ---------------------------------------------------------------------------
# Helper: build the base block with construction grid
# ---------------------------------------------------------------------------


def _build_block(name: str) -> tuple[Pattern, dict[str, Point]]:
    """Return a (Pattern, key_points_dict) for a simple bodice-front block."""
    pattern = Pattern(name=name, anchor=ANCHOR)

    # ── Construction grid ────────────────────────────────────────────────────
    grid = ConstructionGrid(
        anchor=ANCHOR,
        horizontals=[
            ("Shoulder", 0),
            ("Bust", BUST_Y),
            ("Waist", WAIST_Y),
            ("Hem", PIECE_H),
        ],
        verticals=[
            ("Centre Front", 0),
            ("Side Seam", PIECE_W),
        ],
        part_name="Grid",
    )
    grid_part = grid.build()
    pattern.add_part(grid_part)

    # Resolve named grid elements
    g_shoulder = grid_part.get_element("Shoulder").geometry
    g_bust = grid_part.get_element("Bust").geometry
    g_waist = grid_part.get_element("Waist").geometry
    g_hem = grid_part.get_element("Hem").geometry
    g_cf = grid_part.get_element("Centre Front").geometry
    g_side = grid_part.get_element("Side Seam").geometry

    # Key corner points
    pts = {
        "shoulder_cf": intersect(g_shoulder, g_cf)[0],
        "shoulder_side": intersect(g_shoulder, g_side)[0],
        "bust_cf": intersect(g_bust, g_cf)[0],
        "bust_side": intersect(g_bust, g_side)[0],
        "waist_cf": intersect(g_waist, g_cf)[0],
        "waist_side": intersect(g_waist, g_side)[0],
        "hem_cf": intersect(g_hem, g_cf)[0],
        "hem_side": intersect(g_hem, g_side)[0],
        "bust_point": ANCHOR + Point(BUST_X, BUST_Y),
    }
    return pattern, pts


def _add_outline(part: PatternPart, pts: dict[str, Point]) -> dict[str, PatternElement]:
    """Add the four closed outline segments to *part* and return them by name."""
    segs = {
        "cf": part.append(
            Segment(pts["hem_cf"], pts["shoulder_cf"]),
            style=_FOLD,
            is_outline=True,
        ),
        "shoulder": part.append(
            Segment(pts["shoulder_cf"], pts["shoulder_side"]),
            style=_STITCH,
            is_outline=True,
        ),
        "side": part.append(
            Segment(pts["shoulder_side"], pts["hem_side"]),
            style=_STITCH,
            is_outline=True,
        ),
        "hem": part.append(
            Segment(pts["hem_side"], pts["hem_cf"]),
            style=_STITCH,
            is_outline=True,
        ),
    }
    return segs


# ---------------------------------------------------------------------------
# Example 1 — Outer dart, explicit depth
# ---------------------------------------------------------------------------


def example_01_outer_explicit_depth() -> None:
    """Side-seam and centre-front waist dart; depth given as an explicit mm value."""
    pattern, pts = _build_block("Example 1 – Outer Dart (explicit depth)")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    dart_right = Dart.from_edge_at_t(
        segs["side"],
        t=0.25,
        width=22 * MM,
        depth=90 * MM,
        dart_type=DartType.TRIANGLE,
        name="Side Seam Dart",
    )
    part.add_dart(
        dart_right,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )

    dart_left = Dart.from_edge_at_t(
        segs["cf"],
        t=0.25,
        width=22 * MM,
        depth=90 * MM,
        dart_type=DartType.TRIANGLE,
        name="Centre Front Dart",
    )
    part.add_dart(dart_left, notches=True, precision_tip=True)

    part.add_info_box(
        header="Example 1",
        notes=["Outer seam dart", "Depth: 90 mm  |  Width: 22 mm"],
        offset=(0, -20 * MM),
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "01_outer_dart_explicit_depth.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  01_outer_dart_explicit_depth.svg")


# ---------------------------------------------------------------------------
# Example 2 — Outer dart aimed at a reference point (bust point)
# ---------------------------------------------------------------------------


def example_02_outer_reference_point() -> None:
    """Side-seam bust dart directed at the bust point."""
    pattern, pts = _build_block("Example 2 – Bust Dart (reference point)")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    grid_part = pattern.parts[0]
    grid_part.add_precision_points(pts["bust_point"])

    dart = Dart.from_edge_free_tip(
        segs["side"],
        t=0.38,
        width=28 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=25 * MM,
        dart_type=DartType.TRIANGLE,
        name="Bust Dart",
    )
    part.add_dart(
        dart,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        precision_style=_PRECISION,
        notches=True,
        precision_tip=True,
    )
    part.append(Segment(dart.center, pts["bust_point"]), style=_AUX)
    part.add_precision_points(pts["bust_point"])

    part.add_info_box(
        header="Bust Dart — Reference Point",
        notes=[
            "Reference: bust point",
            "Tip shortfall: 25 mm",
            "Width: 28 mm",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
        name="Grain",
        style=_GRAINLINE,
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "02_outer_dart_reference_point.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  02_outer_dart_reference_point.svg")


# ---------------------------------------------------------------------------
# Example 3 — Inner / reverse dart (rhombus)
# ---------------------------------------------------------------------------


def example_03_inner_dart_rhombus() -> None:
    """Princess-seam inner dart rendered as a rhombus."""
    pattern, pts = _build_block("Example 3 – Inner Dart (Rhombus)")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)
    _add_outline(part, pts)

    bust_line_elem = PatternElement(
        Segment(pts["bust_cf"], pts["bust_side"]),
        style=_STITCH,
    )
    dart = Dart.from_edge_at_t(
        bust_line_elem,
        t=0.5,
        width=24 * MM,
        depth=55 * MM,
        dart_type=DartType.RHOMBUS,
        name="Rhombus Dart",
    )
    part.add_dart(dart, stitch_style=_DART_STITCH, notches=True, precision_tip=True)

    part.add_info_box(
        header="Inner Dart — Rhombus",
        notes=[
            "Placed on bust line at t = 0.5",
            f"Width: {dart.width:.0f} mm  |  Depth: {dart.depth:.0f} mm",
        ],
        offset=(0, 55 * MM),
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
        name="Grain",
        style=_GRAINLINE,
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "03_inner_dart_rhombus.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  03_inner_dart_rhombus.svg")


# ---------------------------------------------------------------------------
# Example 4 — Dart split into two sub-darts
# ---------------------------------------------------------------------------


def example_04_dart_split() -> None:
    """One large dart split into two equal sub-darts via Dart.split()."""
    pattern, pts = _build_block("Example 4 – Dart Split")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    original = Dart.from_edge_at_t(
        segs["side"],
        t=0.30,
        width=36 * MM,
        depth=65 * MM,
        dart_type=DartType.TRIANGLE,
        name="Original",
    )

    # Show the original dart lightly as reference
    part.append(original.stitch_line_a, style=_REF_STYLE)
    part.append(original.stitch_line_b, style=_REF_STYLE)
    part.append(original.fold_line, style=_REF_STYLE)

    dart_a, dart_b = original.split(ratio=0.5)
    part.add_dart(
        dart_a,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )
    part.add_dart(
        dart_b,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )

    part.add_info_box(
        header="Dart Split",
        notes=[
            "Original: 36 mm wide",
            "→ split into 2 × 18 mm",
            "(grey = original, for reference)",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
        name="Grain",
        style=_GRAINLINE,
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "04_dart_split.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  04_dart_split.svg")


# ---------------------------------------------------------------------------
# Example 5 — Moving a dart upward along the seam (Dart.translate)
# ---------------------------------------------------------------------------


def example_05_dart_transfer() -> None:
    """Reposition a side-seam dart 20 mm upward using Dart.translate().

    A fitter may need to slide a dart along a seam edge — for example to move
    a waist dart closer to the bust level, or to clear a pocket.  Because a
    dart is an immutable value object, ``Dart.translate(dx, dy)`` returns a new
    dart with all four key points shifted while the shape and intake angle stay
    exactly the same.
    """
    pattern, pts = _build_block("Example 5 – Dart Translate (20 mm upward)")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    # ── Original dart just below bust level on the side seam ───────────────
    original = Dart.from_edge_at_t(
        segs["side"],
        t=0.45,
        width=24 * MM,
        depth=55 * MM,
        dart_type=DartType.TRIANGLE,
        name="Original",
    )

    # Show original position as a faint reference
    part.append(original.stitch_line_a, style=_REF_STYLE)
    part.append(original.stitch_line_b, style=_REF_STYLE)
    part.append(original.fold_line, style=_REF_STYLE)

    # ── Translate: slide the dart 20 mm upward (negative y in SVG coords) ──
    moved = original.translate(dx=0, dy=-20 * MM)
    moved = Dart(
        leg_a=moved.leg_a,
        leg_b=moved.leg_b,
        center=moved.center,
        tip=moved.tip,
        dart_type=DartType.TRIANGLE,
        name="Translated (+20 mm)",
    )

    part.add_dart(
        moved,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )

    part.add_info_box(
        header="Dart Translate",
        notes=[
            "Dart shifted 20 mm upward",
            f"Width: {moved.width:.0f} mm  |  Depth: {moved.depth:.0f} mm",
            f"Intake angle: {moved.intake_angle_deg:.1f}°  (unchanged)",
            "(grey = original position)",
        ],
        offset=(0, 55 * MM),
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
        name="Grain",
        style=_GRAINLINE,
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "05_dart_transfer.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  05_dart_transfer.svg")


# ---------------------------------------------------------------------------
# Example 6 — Bust dart with curved CubicBezier stitch legs
# ---------------------------------------------------------------------------


def example_06_curved_dart() -> None:
    """Bust dart with curved stitch legs — the curved-seam method.

    Real garment patterns often use gently curved stitch lines instead of
    straight ones to improve the three-dimensional fit around the bust.
    In sewpat this is achieved by assigning ``CubicBezier`` objects to
    ``stitch_curve_a`` and ``stitch_curve_b`` on the ``Dart``.

    Construction recipe:
    1.  Build a standard straight dart with ``Dart.from_edge_free_tip()``.
    2.  Offset each stitch leg slightly inward at its midpoint to create
        a concave curve that pulls the seam toward the bust apex.
    3.  Construct two ``CubicBezier`` objects (tip → leg) with control
        points at the inward-offset mid-points.
    4.  Assign them as ``stitch_curve_a / b`` via the ``Dart`` constructor.
    5.  Call ``part.add_dart()`` as usual — it uses the curved geometry
        automatically.
    """
    pattern, pts = _build_block("Example 6 – Bust Dart (curved stitch legs)")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    # ── 1. Straight base dart aimed at the bust point ──────────────────────
    straight = Dart.from_edge_free_tip(
        segs["side"],
        t=0.40,
        width=26 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=20 * MM,
        dart_type=DartType.TRIANGLE,
        name="Bust Dart",
    )

    # Show the straight stitch lines as a faint reference
    part.append(straight.stitch_line_a, style=_REF_STYLE)
    part.append(straight.stitch_line_b, style=_REF_STYLE)
    part.append(straight.fold_line, style=_REF_STYLE)

    # ── 2. Build curved stitch legs via CubicBezier ─────────────────────────
    tip = straight.tip
    leg_a = straight.leg_a
    leg_b = straight.leg_b
    fold_dir = straight.fold_line.unit_direction
    inward = np.array([-fold_dir[1], fold_dir[0]])  # 90° CCW — toward dart interior

    mid_a = Point((tip.x + leg_a.x) / 2, (tip.y + leg_a.y) / 2)
    mid_b = Point((tip.x + leg_b.x) / 2, (tip.y + leg_b.y) / 2)

    CURVE_OFFSET = 8.0
    mid_a_curved = Point(mid_a.x + inward[0] * CURVE_OFFSET, mid_a.y + inward[1] * CURVE_OFFSET)
    mid_b_curved = Point(mid_b.x - inward[0] * CURVE_OFFSET, mid_b.y - inward[1] * CURVE_OFFSET)

    curve_a = CubicBezier(tip, mid_a_curved, mid_a_curved, leg_a)
    curve_b = CubicBezier(tip, mid_b_curved, mid_b_curved, leg_b)

    # ── 3. Build the curved dart ────────────────────────────────────────────
    curved = Dart(
        leg_a=leg_a,
        leg_b=leg_b,
        center=straight.center,
        tip=tip,
        dart_type=DartType.TRIANGLE,
        name="Bust Dart (curved)",
        stitch_curve_a=curve_a,
        stitch_curve_b=curve_b,
        _edge_element=straight._edge_element,
    )

    part.add_dart(
        curved,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        precision_style=_PRECISION,
        notches=True,
        precision_tip=True,
    )

    part.add_precision_points(pts["bust_point"])
    part.append(Segment(straight.center, pts["bust_point"]), style=_AUX)

    part.add_info_box(
        header="Bust Dart — Curved",
        notes=[
            "Curved stitch legs via CubicBezier",
            f"Intake angle: {curved.intake_angle_deg:.1f}°",
            f"Depth: {curved.depth:.0f} mm",
            "Curve offset: 8 mm inward",
            "(grey = straight legs, for reference)",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
        name="Grain",
        style=_GRAINLINE,
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "06_curved_dart.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  06_curved_dart.svg")


# ---------------------------------------------------------------------------
# Example 7 — Dart with seam allowance
# ---------------------------------------------------------------------------


def example_07_dart_with_seam_allowance() -> None:
    """Bust dart on a bodice-front piece with 10 mm seam allowance.

    The dart is added before ``add_seam_allowance()`` — always the correct
    order.  The dashed outer line is the cutting line; the inner solid line
    is the sewing line.
    """
    pattern, pts = _build_block("Example 7 – Bust Dart with Seam Allowance")
    part = PatternPart("Bodice Front")
    pattern.add_part(part)

    SA = 10 * MM

    # CF edge: fold line — no seam allowance here
    _FOLD_SA = StyleOptions(
        stroke_color=_FOLD.stroke_color,
        stroke_width=_FOLD.stroke_width,
        dash_array=_FOLD.dash_array,
        seam_allowance=0.0,
    )
    _SA_STITCH = StyleOptions(
        stroke_color=_STITCH.stroke_color,
        stroke_width=_STITCH.stroke_width,
        dash_array=_STITCH.dash_array,
        seam_allowance=SA,
    )

    part.append(Segment(pts["hem_cf"], pts["shoulder_cf"]), style=_FOLD_SA, is_outline=True)
    part.append(
        Segment(pts["shoulder_cf"], pts["shoulder_side"]),
        style=_SA_STITCH,
        is_outline=True,
    )
    side = part.append(
        Segment(pts["shoulder_side"], pts["hem_side"]),
        style=_SA_STITCH,
        is_outline=True,
    )
    part.append(Segment(pts["hem_side"], pts["hem_cf"]), style=_SA_STITCH, is_outline=True)

    dart = Dart.from_edge_free_tip(
        side,
        t=0.40,
        width=26 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=20 * MM,
        dart_type=DartType.TRIANGLE,
        name="Bust Dart",
    )
    part.add_dart(
        dart,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )
    part.add_seam_allowance(distance=SA)

    part.add_precision_points(pts["bust_point"])
    part.append(Segment(dart.tip, pts["bust_point"]), style=_AUX)

    part.add_info_box(
        header="Seam Allowance",
        notes=[
            f"SA: {SA / MM:.0f} mm (side, shoulder, hem)",
            "Centre front: no SA (fold edge)",
            f"Intake angle: {dart.intake_angle_deg:.1f}°  |  Depth: {dart.depth / MM:.0f} mm",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
        name="Grain",
        style=_GRAINLINE,
    )
    export_pattern_svg_mm(
        pattern,
        filename=str(OUT_DIR / "07_dart_seam_allowance.svg"),
        width_mm=_A4_W,
        height_mm=_A4_H,
    )
    print("✓  07_dart_seam_allowance.svg")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating dart examples …\n")
    example_01_outer_explicit_depth()
    example_02_outer_reference_point()
    example_03_inner_dart_rhombus()
    example_04_dart_split()
    example_05_dart_transfer()
    example_06_curved_dart()
    example_07_dart_with_seam_allowance()
    print(f"\nAll SVGs written to: {OUT_DIR.resolve()}")
