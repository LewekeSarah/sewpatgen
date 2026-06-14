"""
Spielbeispiel: Dreiecksabnäher im Rechteck, basierend auf
example_02_outer_reference_point

Dieses Beispiel erzeugt ein einfaches Rechteck mit einem Dreiecksabnäher,
analog zu Example 2 aus dart_examples.py, ohne SVG-Export und mit
Fokus auf die Objekterzeugung.

Das Beispiel dient als Ausgangspunkt für Transformationsexperimente.
"""

import copy
from pathlib import Path

from sewpat import (
    CM,
    MM,
    Dart,
    DartType,
    Pattern,
    PatternPart,
    Point,
    Ray,
    Segment,
)
from sewpat.render import export_pattern_svg_mm

# DIN A4 canvas size in mm
_A4_W, _A4_H = 210.0, 297.0
OUT_DIR = Path(__file__).parent

# Rechteck-Dimensionen
PIECE_W = 120 * MM
PIECE_H = 180 * MM
BUST_Y = 65 * MM
BUST_X = 45 * MM
ANCHOR = Point(25 * MM, 25 * MM)
SEAM_ALLOWANCE = 1 * CM


def build_rectangle_with_dart():
    pattern = Pattern(name="Toy Rectangle with Dart", anchor=ANCHOR)
    part = PatternPart("Rectangle")
    pattern.add_part(part)

    # Eckpunkte
    pts = {
        "A": ANCHOR,
        "B": ANCHOR + Point(PIECE_W, 0),
        "C": ANCHOR + Point(PIECE_W, PIECE_H),
        "D": ANCHOR + Point(0, PIECE_H),
        "bust_point": ANCHOR + Point(BUST_X, BUST_Y),
    }

    # Umriss
    segs = {
        "left": part.append(Segment(pts["A"], pts["D"]), is_outline=True),
        "top": part.append(Segment(pts["D"], pts["C"]), is_outline=True),
        "right": part.append(Segment(pts["C"], pts["B"]), is_outline=True),
        "bottom": part.append(Segment(pts["B"], pts["A"]), is_outline=True),
    }

    # Abnäher an der rechten Kante, auf Brustpunkt gerichtet
    t_bust = (pts["bust_point"].y - pts["C"].y) / (pts["B"].y - pts["C"].y)
    dart = Dart.from_edge_free_tip(
        segs["right"],
        t=t_bust,
        width=28 * MM,
        reference_point=pts["bust_point"],
        tip_shortfall=0 * MM,
        dart_type=DartType.TRIANGLE,
        name="Toy Dart",
    )
    part.add_dart(dart)
    part.add_seam_allowance(distance=SEAM_ALLOWANCE)
    return pattern, part, pts, dart


def transfer_dart_example(
    part_orig: PatternPart,
    dart: Dart,
    cut_direction: Point,
) -> tuple[PatternPart, Dart]:
    """Transfer *dart* to the new position defined by *cut_direction*.

    *cut_direction* is a direction vector from ``dart.tip`` toward the new dart
    position on the outline.  Returns the transformed part and the new dart.
    """
    part = copy.deepcopy(part_orig)
    part.name = part.name + " (transferred)"

    cut_ray = Ray(dart.tip, cut_direction.coords, name="Transfer cut")
    print(f"Cut ray from tip {dart.tip} in direction {cut_direction}")
    print(f"Original dart: tip={dart.tip}, leg_a={dart.leg_a}, leg_b={dart.leg_b}")
    print(f"Original intake angle: {dart.intake_angle_deg:.2f}°")

    new_dart = part.transfer_dart(dart, cut_ray, sa_distance=SEAM_ALLOWANCE)

    print(f"New dart:      tip={new_dart.tip}, leg_a={new_dart.leg_a}, leg_b={new_dart.leg_b}")
    print(f"New intake angle: {new_dart.intake_angle_deg:.2f}°")

    return part, new_dart


if __name__ == "__main__":
    pattern, part, pts, dart = build_rectangle_with_dart()
    print("Eckpunkte:", pts)
    print("Abnäher:", dart)

    # Transfer the dart toward the top edge (cut line pointing upward from tip)
    new_part, new_dart = transfer_dart_example(part, dart, cut_direction=Point(0, 1))

    # A part has either the original dart and outline, or the transferred
    # ones, never both -- place the transferred part next to the original
    # instead of on top of it so the two outlines don't overlap in the SVG.
    gap = 25 * MM
    orig_min, orig_max = part.bounding_box()
    new_part = new_part.translated(Point(orig_max.x - orig_min.x + gap, 0))

    pattern.add_part(new_part)
    export_pattern_svg_mm(
        pattern,
        parts=["Rectangle", "Rectangle (transferred)"],
        filename=str(OUT_DIR / "08_outer_dart_reference_point.svg"),
        width_mm=2 * _A4_W,
        height_mm=_A4_H,
        show_seam_allowance=True,
        dark_mode=False,
    )
