#!/usr/bin/env python3
"""Dart (Abnäher) Examples — sewpat library showcase.

This script generates five SVG files, each demonstrating a different aspect
of dart support in sewpat:

    01_outer_dart_explicit_depth.svg   — Outer seam dart, depth given directly
    02_outer_dart_reference_point.svg  — Outer dart aimed at a reference point
                                         (bust-point style)
    03_inner_dart_rhombus.svg          — Inner/reverse dart, rhombus rendering
    04_dart_split.svg                  — One dart split into two sub-darts
    05_dart_transfer.svg               — Dart transferred to a new edge via the
                                         pivot method

Each file uses the same simple rectangular bodice-front block with a
construction grid so the geometry is easy to follow.

Usage (run from repo root):
    python examples/darts/dart_examples.py
"""

from pathlib import Path

from sewpat import (
    CM,
    MM,
    STYLE_DART_FOLD,
    STYLE_DART_STITCH,
    STYLE_FOLD,
    STYLE_STITCH,
    STYLE_SEAM_ALLOWANCE,
    Dart,
    DartElements,
    Pattern,
    PatternElement,
    PatternPart,
    Point,
    Segment,
    transfer_dart,
)
from sewpat.geometry import CubicBezier, intersect
from sewpat.pattern import ConstructionGrid
from sewpat.render import export_pattern_svg_mm
from sewpat.style import (
    STYLE_CENTER_LINE,
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
_FOLD        = _scaled(STYLE_FOLD)
_STITCH      = _scaled(STYLE_STITCH)
_DART_STITCH = _scaled(STYLE_DART_STITCH)
_DART_FOLD   = _scaled(STYLE_DART_FOLD)
_DART_PP     = _scaled(STYLE_SEAM_ALLOWANCE)
_GRAINLINE   = _scaled(STYLE_GRAINLINE)
_AUX         = _scaled(STYLE_CONSTRUCTION_GRID)
_REF_STYLE   = StyleOptions(stroke_color="#bbbbbb", stroke_width=0.15, dash_array=[3.0, 3.0])

# ---------------------------------------------------------------------------
# Shared bodice-front dimensions (mm)
# ---------------------------------------------------------------------------
PIECE_W = 120 * MM   # half-front width
PIECE_H = 180 * MM   # front length (shoulder → hem)
WAIST_Y = 110 * MM   # distance from top to waist line
BUST_Y  =  65 * MM   # distance from top to bust line
BUST_X  =  45 * MM   # bust point x from left edge (CF)

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
            ("Schulterlinie",  0),
            ("Brustlinie",     BUST_Y),
            ("Taillenlinie",   WAIST_Y),
            ("Saumlinie",      PIECE_H),
        ],
        verticals=[
            ("Mitte-Vorne",    0),
            ("Seitennaht",     PIECE_W),
        ],
        part_name="Konstruktionsgitter",
    )
    grid_part = grid.build()
    pattern.add_part(grid_part)

    # Resolve named grid elements
    g_shoulder = grid_part.get_element("Schulterlinie").geometry
    g_bust     = grid_part.get_element("Brustlinie").geometry
    g_waist    = grid_part.get_element("Taillenlinie").geometry
    g_hem      = grid_part.get_element("Saumlinie").geometry
    g_cf       = grid_part.get_element("Mitte-Vorne").geometry
    g_side     = grid_part.get_element("Seitennaht").geometry

    # Key corner points
    pts = {
        "shoulder_cf":   intersect(g_shoulder, g_cf)[0],
        "shoulder_side": intersect(g_shoulder, g_side)[0],
        "bust_cf":       intersect(g_bust,     g_cf)[0],
        "bust_side":     intersect(g_bust,     g_side)[0],
        "waist_cf":      intersect(g_waist,    g_cf)[0],
        "waist_side":    intersect(g_waist,    g_side)[0],
        "hem_cf":        intersect(g_hem,       g_cf)[0],
        "hem_side":      intersect(g_hem,       g_side)[0],
        "bust_point":    ANCHOR.translate(BUST_X, BUST_Y),
    }
    return pattern, pts


def _add_outline(part: PatternPart, pts: dict[str, Point]) -> dict[str, Segment]:
    """Add the four closed outline segments to *part* and return them by name."""
    segs = {
        "cf":       part.append(Segment(pts["hem_cf"],        pts["shoulder_cf"]),   style=_FOLD,   is_outline=True),
        "shoulder": part.append(Segment(pts["shoulder_cf"],   pts["shoulder_side"]), style=_STITCH, is_outline=True),
        "side":     part.append(Segment(pts["shoulder_side"], pts["hem_side"]),       style=_STITCH, is_outline=True),
        "hem":      part.append(Segment(pts["hem_side"],       pts["hem_cf"]),        style=_STITCH, is_outline=True),
    }
    return segs


# ---------------------------------------------------------------------------
# Example 1 — Outer dart, explicit depth
# ---------------------------------------------------------------------------

def example_01_outer_explicit_depth() -> None:
    """Side-seam waist dart; depth given as an explicit mm value."""
    pattern, pts = _build_block("Beispiel 1 – Abnäher an PatternElement")
    part = PatternPart("Example")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    # Dart placed at t=0.35 along the side seam. The side-seam PatternElement
    # is passed directly so DartElements.from_edge inherits its style.
    dart_right = DartElements.from_edge(
        segs["side"],
        position_t=0.25,
        width=22 * MM,
        depth=90 * MM,
        fold_direction="inward",
        name="Stitch Line",
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
    )
    result = part.add_dart(dart_right, notches=True, precision_tip=True)

    # Second dart derived from the fold edge of to highlight different edge styles
    dart_left = DartElements.from_edge(
        segs["cf"],
        position_t=0.25,
        width=22 * MM,
        depth=90 * MM,
        fold_direction="inward",
        name="Fold Line",
    )
    result2 = part.add_dart(dart_left, notches=True, precision_tip=True)

    # Info box
    part.add_info_box(
        header="Example 1",
        notes=[
            "Außennaht-Abnäher",
            "Abnäher: Tiefe 90 mm, Breite 22 mm",
            "PatternElement + Edge Style",
        ],
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

    # Mark the bust point as a precision mark on the construction grid
    grid_part = pattern.parts[0]
    grid_part.add_precision_points(pts["bust_point"])

    factory = DartElements.from_edge(
        segs["side"],
        position_t=0.38,         # at bust-line height
        width=28 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=25 * MM,   # stop 2.5 cm short of bust point
        fold_direction="inward",
        name="Bustnaht",
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
        precision_style=_DART_PP
    )
    result = part.add_dart(factory, notches=True, precision_tip=True)
    result = part.append(Segment(factory.dart.center, pts["bust_point"]), style=_AUX)
    # Label the bust point on the part too
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
        ANCHOR.translate(10 * MM, 10 * MM),
        ANCHOR.translate(10 * MM, PIECE_H - 10 * MM),
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
    """Princess-seam style inner dart rendered as a rhombus (Raute)."""
    pattern, pts = _build_block("Beispiel 3 – Innennaht-Abnäher (Raute)")
    part = PatternPart("Vorderteil")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    # Inner dart sits on the bust line, in the middle of the front panel.
    # The bust line is not part of the outline, so we create a styled
    # PatternElement for it explicitly and pass it to from_edge.
    bust_line_elem = PatternElement(
        Segment(pts["bust_cf"], pts["bust_side"]), style=_STITCH
    )
    factory = DartElements.from_edge(
        bust_line_elem,
        position_t=0.5,
        width=24 * MM,
        depth=55 * MM,
        fold_direction="outward",
        name="Eingriff",
        stitch_style=_DART_STITCH,
        fold_style=_DART_FOLD,
    )
    result = part.add_dart(factory, notches=True, precision_tip=True)

    part.add_info_box(
        header="Vorderteil",
        notes=[
            "Innennaht-Abnäher",
            "Rendering: Raute",
            "Tiefe: 55 mm",
            "Breite: 24 mm",
        ],
    )
    part.add_grainline(
        ANCHOR.translate(10 * MM, 10 * MM),
        ANCHOR.translate(10 * MM, PIECE_H - 10 * MM),
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
    """One large waist dart split into two equal sub-darts via Dart.split()."""
    pattern, pts = _build_block("Beispiel 4 – Abnäher aufteilen (Split)")
    part = PatternPart("Vorderteil")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    # Build the original (large) dart first — shown faint as reference.
    # Pass the side-seam PatternElement so edge_style is propagated to sub-darts.
    original_factory = DartElements.from_edge(
        segs["side"],
        position_t=0.55,
        width=36 * MM,
        depth=65 * MM,
        fold_direction="inward",
        name="Original",
    )
    original = original_factory.dart

    # Show the original dart outline very lightly for reference
    part.append(original.stitch_line_a, style=_REF_STYLE)
    part.append(original.stitch_line_b, style=_REF_STYLE)
    part.append(original.fold_line,     style=_REF_STYLE)

    # Split into two equal sub-darts (ratio=0.5) — edge_style is propagated
    dart_a, dart_b = original.split(ratio=0.5)

    result_a = part.add_dart(
        DartElements(dart_a, stitch_style=_DART_STITCH, fold_style=_DART_FOLD),
        notches=True, precision_tip=True,
    )
    result_b = part.add_dart(
        DartElements(dart_b, stitch_style=_DART_STITCH, fold_style=_DART_FOLD),
        notches=True, precision_tip=True,
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
        ANCHOR.translate(10 * MM, 10 * MM),
        ANCHOR.translate(10 * MM, PIECE_H - 10 * MM),
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
# Example 5 — Dart transfer via pivot method
# ---------------------------------------------------------------------------

def example_05_dart_transfer() -> None:
    """Transfer a side-seam dart to the shoulder seam using the pivot method."""
    pattern, pts = _build_block("Beispiel 5 – Abnäher verschieben (Pivot)")
    part = PatternPart("Vorderteil")
    pattern.add_part(part)
    segs = _add_outline(part, pts)

    # ── Original dart on the side seam ───────────────────────────────────────
    # Pass the side-seam PatternElement so edge_style is inherited automatically.
    original_factory = DartElements.from_edge(
        segs["side"],
        position_t=0.38,
        width=26 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=20 * MM,
        fold_direction="inward",
        name="Seitennaht (Original)",
    )
    original = original_factory.dart

    # Show original dart lightly as reference
    part.append(original.stitch_line_a, style=_REF_STYLE)
    part.append(original.stitch_line_b, style=_REF_STYLE)
    part.append(original.fold_line,     style=_REF_STYLE)

    # ── Transferred dart on the shoulder seam ────────────────────────────────
    # transfer_dart propagates edge_style from original automatically.
    # We only need to update the name via a direct Dart() call.
    transferred = transfer_dart(
        original,
        new_edge=segs["shoulder"].geometry,
        new_position_t=0.55,
    )
    transferred = Dart(
        leg_a=transferred.leg_a,
        leg_b=transferred.leg_b,
        center=transferred.center,
        tip=transferred.tip,
        fold_direction=transferred.fold_direction,
        name="Schulternaht (Übertragen)",
    )
    result = part.add_dart(
        DartElements(transferred, stitch_style=_DART_STITCH, fold_style=_DART_FOLD),
        notches=True, precision_tip=True,
    )

    # Mark the bust point (pivot) on the part
    part.add_precision_points(pts["bust_point"])

    part.add_info_box(
        header="Vorderteil",
        notes=[
            "Pivot-Methode:",
            "Seitennaht → Schulternaht",
            "(grau = Original als Referenz)",
            "• = Bustpunkt (Pivot)",
        ],
    )
    part.add_grainline(
        ANCHOR.translate(10 * MM, 10 * MM),
        ANCHOR.translate(10 * MM, PIECE_H - 10 * MM),
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
# README maintenance — embed SVGs as base64 data URIs
# ---------------------------------------------------------------------------

def embed_svgs_in_readme() -> None:
    """Replace every ``![…](…)`` image tag in README.md with a fresh inline
    base64 data URI read from the corresponding SVG file on disk.

    Works whether the README currently contains plain filenames *or* stale
    data URIs from a previous run — the replacement is always positional
    (first image tag ↔ first SVG file in *_SVG_ORDER*).

    The SVG files themselves are kept on disk as the canonical source;
    this function is called automatically after every SVG regeneration.
    """
    import base64
    import re

    _SVG_ORDER = [
        "01_outer_dart_explicit_depth.svg",
        "02_outer_dart_reference_point.svg",
        "03_inner_dart_rhombus.svg",
        "04_dart_split.svg",
        "05_dart_transfer.svg",
    ]

    readme = OUT_DIR / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")

    # Match every ![alt](anything) tag — captures prefix, uri, and suffix separately
    tag_re = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")
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
        new_tag = m.group(1) + "data:image/svg+xml;base64," + b64 + m.group(3)
        start, end = m.start() + offset, m.end() + offset
        result = result[:start] + new_tag + result[end:]
        offset += len(new_tag) - (end - start)
        embedded += 1

    readme.write_text(result, encoding="utf-8")
    print(f"↺  README.md updated — {embedded} SVG(s) embedded as data URIs")


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
    print(f"\nAll SVGs written to: {OUT_DIR.resolve()}")
    print()
    embed_svgs_in_readme()
