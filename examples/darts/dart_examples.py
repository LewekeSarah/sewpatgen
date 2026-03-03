#!/usr/bin/env python3
"""Dart (Abnäher) Examples — sewpat library showcase.

This script generates six SVG files, each demonstrating a different aspect
of dart support in sewpat:

    01_outer_dart_explicit_depth.svg   — Outer seam dart, depth given directly
    02_outer_dart_reference_point.svg  — Outer dart aimed at a reference point
                                         (bust-point style)
    03_inner_dart_rhombus.svg          — Inner/reverse dart, rhombus rendering
    04_dart_split.svg                  — One dart split into two sub-darts
    05_dart_transfer.svg               — Dart transferred to a new edge via the
                                         pivot method (Schwenkverfahren)
    06_curved_dart.svg                 — Bust dart with curved CubicBezier stitch
                                         legs (curved-seam / princess-style dart)

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


# Halved presets used throughout all five examples
_FOLD = _scaled(STYLE_FOLD)
_STITCH = _scaled(STYLE_STITCH)
_DART_STITCH = _scaled(STYLE_DART_STITCH)
_DART_FOLD = _scaled(STYLE_DART_FOLD)
_PRECISION = _scaled(STYLE_PRECISION_POINT)
_GRAINLINE = _scaled(STYLE_GRAINLINE)
_AUX = _scaled(STYLE_CONSTRUCTION_GRID)
_REF_STYLE = StyleOptions(
    stroke_color="#bbbbbb", stroke_width=0.15, dash_array=[3.0, 3.0]
)

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
            ("Schulterlinie", 0),
            ("Brustlinie", BUST_Y),
            ("Taillenlinie", WAIST_Y),
            ("Saumlinie", PIECE_H),
        ],
        verticals=[
            ("Mitte-Vorne", 0),
            ("Seitennaht", PIECE_W),
        ],
        part_name="Konstruktionsgitter",
    )
    grid_part = grid.build()
    pattern.add_part(grid_part)

    # Resolve named grid elements
    g_shoulder = grid_part.get_element("Schulterlinie").geometry
    g_bust = grid_part.get_element("Brustlinie").geometry
    g_waist = grid_part.get_element("Taillenlinie").geometry
    g_hem = grid_part.get_element("Saumlinie").geometry
    g_cf = grid_part.get_element("Mitte-Vorne").geometry
    g_side = grid_part.get_element("Seitennaht").geometry

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


def _add_outline(part: PatternPart, pts: dict[str, Point]) -> dict[str, Segment]:
    """Add the four closed outline segments to *part* and return them by name."""
    segs = {
        "cf": part.append(
            Segment(pts["hem_cf"], pts["shoulder_cf"]), style=_FOLD, is_outline=True
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
            Segment(pts["hem_side"], pts["hem_cf"]), style=_STITCH, is_outline=True
        ),
    }
    return segs


# ---------------------------------------------------------------------------
# Example 1 — Outer dart, explicit depth
# ---------------------------------------------------------------------------


def example_01_outer_explicit_depth() -> None:
    """Side-seam waist dart; depth given as an explicit mm value."""
    pattern, pts = _build_block("Beispiel 1 – Außennaht-Abnäher (Tiefe explizit)")
    part = PatternPart("Vorderteil")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    dart_right = Dart.from_edge_at_t(
        segs["side"],
        t=0.25,
        width=22 * MM,
        depth=90 * MM,
        dart_type=DartType.TRIANGLE,
        name="Seitennaht",
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
        name="Mittelnaht",
    )
    part.add_dart(dart_left, notches=True, precision_tip=True)

    part.add_info_box(
        header="Beispiel 1",
        notes=["Außennaht-Abnäher", "Tiefe 90 mm, Breite 22 mm"],
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
    pattern, pts = _build_block("Beispiel 2 – Bustnaht-Abnäher (Referenzpunkt)")
    part = PatternPart("Vorderteil")
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
        name="Bustnaht",
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
        header="Vorderteil",
        notes=[
            "Bustnaht-Abnäher",
            "Referenz: Bustpunkt",
            "Kurzfall: 25 mm",
            "Breite: 28 mm",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
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
    """Princess-seam inner dart rendered as a rhombus (Raute)."""
    pattern, pts = _build_block("Beispiel 3 – Innennaht-Abnäher (Raute)")
    part = PatternPart("Vorderteil")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    bust_line_elem = PatternElement(
        Segment(pts["bust_cf"], pts["bust_side"]), style=_STITCH
    )
    dart = Dart.from_edge_at_t(
        bust_line_elem,
        t=0.5,
        width=24 * MM,
        depth=55 * MM,
        dart_type=DartType.RHOMBUS,
        name="Raute",
    )
    part.add_dart(dart, stitch_style=_DART_STITCH, notches=True, precision_tip=True)

    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
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
    pattern, pts = _build_block("Beispiel 4 – Abnäher aufteilen (Split)")
    part = PatternPart("Vorderteil")
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
        header="Vorderteil",
        notes=[
            "Ursprünglicher Abnäher: 36 mm",
            "→ aufgeteilt in 2 × 18 mm",
            "(grau = Original als Referenz)",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
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

    In practice a fitter may need to slide a dart along a seam edge to sit
    in a better position — for example to move a side-seam waist dart closer
    to the bust level, or simply to clear a pocket.  Because a dart is an
    immutable value object, ``Dart.translate(dx, dy)`` returns a new dart with
    all four key points shifted by the given offset while the shape and intake
    angle remain exactly the same.

    This example places the original dart at t=0.45 on the side seam
    (just below bust level) and translates it 20 mm upward (dy = -20 mm in
    SVG coordinates where y increases downward).  Both darts sit on the side
    seam so the result makes immediate sense to a sewer.  Positioning both
    darts in the upper third of the piece keeps them clear of the info box.
    """
    pattern, pts = _build_block(
        "Beispiel 5 – Abnäher verschieben (translate, 20 mm nach oben)"
    )
    part = PatternPart("Vorderteil")
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
        name="Verschoben (+20 mm)",
    )

    part.add_dart(
        moved,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )

    part.add_info_box(
        header="Vorderteil",
        notes=[
            "Abnäher verschoben: 20 mm nach oben",
            f"Breite: {moved.width:.0f} mm  |  Tiefe: {moved.depth:.0f} mm",
            f"Einzug: {moved.intake_angle_deg:.1f}°  (unverändert)",
            "(grau = ursprüngliche Position)",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
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
    """Bust dart with curved stitch legs — the classic Schnittkurvenverfahren.

    Real garment patterns often use gently curved stitch lines instead of
    straight ones to improve the three-dimensional fit around the bust.
    In sewpat this is achieved by assigning ``CubicBezier`` objects to
    ``stitch_curve_a`` and ``stitch_curve_b`` on the ``Dart``.

    Construction recipe:
    1.  Build a standard straight dart with ``Dart.from_edge_free_tip()``.
    2.  Offset each stitch leg slightly inward at its midpoint to create
        a concave curve that pulls the seam toward the bust apex.
    3.  Construct two ``CubicBezier`` objects (tip → leg) whose control
        points lie on the inward-offset mid-points.
    4.  Assign them as ``stitch_curve_a / b`` via the ``Dart`` constructor.
    5.  Call ``part.add_dart()`` as usual — it automatically uses the
        curved geometry for the stitch elements.

    The straight reference lines are shown in light grey so the curvature
    is easy to see.
    """
    pattern, pts = _build_block(
        "Beispiel 6 – Bustnaht-Abnäher (geschwungene Stichlinien)"
    )
    part = PatternPart("Vorderteil")
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
        name="Bustnaht",
    )

    # Show the straight stitch lines as a faint reference
    part.append(straight.stitch_line_a, style=_REF_STYLE)
    part.append(straight.stitch_line_b, style=_REF_STYLE)
    part.append(straight.fold_line, style=_REF_STYLE)

    # ── 2. Build curved stitch legs via CubicBezier ─────────────────────────
    # Each leg runs tip → leg (consistent with the straight-leg direction).
    # We pull the control points inward (toward the fold axis) to create a
    # gentle concave curve that hugs the bust contour.

    tip = straight.tip
    leg_a = straight.leg_a
    leg_b = straight.leg_b
    fold_dir = straight.fold_line.unit_direction  # unit vector center → tip
    # Inward normal (toward the dart interior) — perpendicular to fold,
    # pointing from leg_a side toward leg_b side.
    inward = np.array([-fold_dir[1], fold_dir[0]])  # rotate 90° CCW

    # Mid-point of each straight leg
    mid_a = Point((tip.x + leg_a.x) / 2, (tip.y + leg_a.y) / 2)
    mid_b = Point((tip.x + leg_b.x) / 2, (tip.y + leg_b.y) / 2)

    # Offset the mid-points inward by 8 mm to create a clearly visible curve
    CURVE_OFFSET = 8.0
    mid_a_curved = Point(
        mid_a.x + inward[0] * CURVE_OFFSET, mid_a.y + inward[1] * CURVE_OFFSET
    )
    mid_b_curved = Point(
        mid_b.x - inward[0] * CURVE_OFFSET, mid_b.y - inward[1] * CURVE_OFFSET
    )

    # Cubic Bézier: tip → cp1 → cp2 → leg
    # To make the curve pass near the offset midpoint we place both control
    # points AT the offset midpoint (symmetric tent).  This gives a parabola-
    # like arc that visibly bows inward by ~3/4 of CURVE_OFFSET at its peak.
    curve_a = CubicBezier(tip, mid_a_curved, mid_a_curved, leg_a)
    curve_b = CubicBezier(tip, mid_b_curved, mid_b_curved, leg_b)

    # ── 3. Build the curved dart ────────────────────────────────────────────
    curved = Dart(
        leg_a=leg_a,
        leg_b=leg_b,
        center=straight.center,
        tip=tip,
        dart_type=DartType.TRIANGLE,
        name="Bustnaht (kurvig)",
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

    # Mark the bust point
    part.add_precision_points(pts["bust_point"])
    part.append(Segment(straight.center, pts["bust_point"]), style=_AUX)

    part.add_info_box(
        header="Vorderteil",
        notes=[
            "Bustnaht — geschwungene Stichlinien",
            f"Einzug: {curved.intake_angle_deg:.1f}°",
            f"Tiefe: {curved.depth:.0f} mm",
            "Kurvenversatz: 8 mm inward",
            "(grau = gerade Linien als Referenz)",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
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
    """Bust dart on a bodice-front piece with full seam allowance.

    Real patterns are cut with seam allowance (Nahtzugabe).  This example
    shows how ``PatternPart.add_seam_allowance()`` works alongside a dart:

    * **10 mm** SA on shoulder, side seam and hem (stitch lines).
    * **0 mm** SA on the centre-front edge (fold / Fadenlauf — no seam here).
    * The dart itself sits on the side seam and is rendered with notches
      and a precision tip marker as usual.

    The dashed outer rectangle is the cutting line; the inner solid rectangle
    is the sewing line.  Sewers can see exactly where to place notches and
    how the SA wraps around the dart legs.
    """
    pattern, pts = _build_block("Beispiel 7 – Bustnaht-Abnäher mit Nahtzugabe")
    part = PatternPart("Vorderteil")
    pattern.add_part(part)

    SA = 10 * MM  # standard seam allowance

    # ── Outline: CF with seam_allowance=0 (fold, no seam), rest with 10 mm ──
    _FOLD_SA = StyleOptions(
        stroke_color=_FOLD.stroke_color,
        stroke_width=_FOLD.stroke_width,
        dash_array=_FOLD.dash_array,
        seam_allowance=0.0,  # no SA on fold edge
    )
    _SA_STITCH = StyleOptions(
        stroke_color=_STITCH.stroke_color,
        stroke_width=_STITCH.stroke_width,
        dash_array=_STITCH.dash_array,
        seam_allowance=SA,
    )

    cf = part.append(
        Segment(pts["hem_cf"], pts["shoulder_cf"]), style=_FOLD_SA, is_outline=True
    )
    shldr = part.append(
        Segment(pts["shoulder_cf"], pts["shoulder_side"]),
        style=_SA_STITCH,
        is_outline=True,
    )
    side = part.append(
        Segment(pts["shoulder_side"], pts["hem_side"]),
        style=_SA_STITCH,
        is_outline=True,
    )
    hem = part.append(
        Segment(pts["hem_side"], pts["hem_cf"]), style=_SA_STITCH, is_outline=True
    )

    # ── Dart ─────────────────────────────────────────────────────────────────
    dart = Dart.from_edge_free_tip(
        side,
        t=0.40,
        width=26 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=20 * MM,
        dart_type=DartType.TRIANGLE,
        name="Bustnaht",
    )
    part.add_dart(
        dart,
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        notches=True,
        precision_tip=True,
    )

    # ── Seam allowance ───────────────────────────────────────────────────────
    # add_dart() has already split the side edge at the dart legs and marked
    # the two outer stubs as is_outline=True, so passing outline_elements=None
    # lets add_seam_allowance() pick up the correct polygon automatically.
    part.add_seam_allowance(distance=SA)

    part.add_precision_points(pts["bust_point"])
    part.append(Segment(dart.tip, pts["bust_point"]), style=_AUX)

    part.add_info_box(
        header="Vorderteil",
        notes=[
            "Bustnaht-Abnäher mit Nahtzugabe",
            f"Nahtzugabe: {SA / MM:.0f} mm (Seiten-/Schulter-/Saum)",
            "Fadenlauf (CF): keine Nahtzugabe",
            f"Einzug: {dart.intake_angle_deg:.1f}°  |  Tiefe: {dart.depth / MM:.0f} mm",
        ],
    )
    part.add_grainline(
        ANCHOR + Point(10 * MM, 10 * MM),
        ANCHOR + Point(10 * MM, PIECE_H - 10 * MM),
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
# README — embed SVGs as inline base64 data URIs
# ---------------------------------------------------------------------------


def embed_svgs_in_readme() -> None:
    """Embed the four example SVGs as base64 data URIs into README.md.

    Each ``![alt](filename.svg)`` tag is replaced with an inline
    ``![alt](data:image/svg+xml;base64,…)`` tag so the images display
    in JetBrains Markdown preview (and other viewers that block relative
    file references but allow data URIs).
    """
    import base64
    import re

    _SVG_ORDER = [
        "01_outer_dart_explicit_depth.svg",
        "02_outer_dart_reference_point.svg",
        "03_inner_dart_rhombus.svg",
        "04_dart_split.svg",
        "05_dart_transfer.svg",
        "06_curved_dart.svg",
        "07_dart_seam_allowance.svg",
    ]

    readme = OUT_DIR / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")

    tag_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    matches = list(tag_re.finditer(text))

    result = text
    offset = 0
    embedded = 0
    for i, m in enumerate(matches):
        if i >= len(_SVG_ORDER):
            break
        svg_path = OUT_DIR / _SVG_ORDER[i]
        if not svg_path.exists():
            continue
        b64 = base64.b64encode(svg_path.read_bytes()).decode()
        new_tag = f"![{m.group(1)}](data:image/svg+xml;base64,{b64})"
        start, end = m.start() + offset, m.end() + offset
        result = result[:start] + new_tag + result[end:]
        offset += len(new_tag) - (end - start)
        embedded += 1

    readme.write_text(result, encoding="utf-8")
    print(f"↺  README.md — {embedded} SVG(s) embedded as data URIs")


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
    print(f"\nAll SVGs written to: {OUT_DIR.resolve()}\n")
    embed_svgs_in_readme()
