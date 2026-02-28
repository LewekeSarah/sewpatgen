from sewpat import Pattern, PatternPart, Point
from sewpat.geometry import Rect, Segment
from sewpat.units import MM, CM
from pathlib import Path
from sewpat.style import (
    STYLE_FOLD,
    STYLE_HEM,
    STYLE_CUT,
    STYLE_STITCH,
    STYLE_CENTER_LINE,
)
from sewpat.pages import DinA4
from sewpat.render import export_pattern_svg_mm, StyleOptions


def make_legend() -> Pattern:
    sep = 7 * MM
    ## STEP 1.1
    # Anchor: top left
    left_p1 = Point(2 * sep, sep, "p1")
    right_p1 = left_p1.translate(0.75 * DinA4.width, 0)
    legend = Pattern(name="Legend", anchor=left_p1)

    aux = PatternPart("Auxiliary Elements")
    legend.add_part(aux)
    # Reference size box
    size_box_origin = Point(-0.5 * DinA4.width + sep, -4.5 * CM)
    aux.append(
        Rect(origin=size_box_origin, width=3 * CM, height=3 * CM, name="3cm × 3cm")
    )
    aux.add_precision_points(left_p1.translate(6 * CM, -3 * CM))

    lines = PatternPart("Line Style Legend")
    legend.add_part(lines)
    lines.append(
        Segment(
            left_p1.translate(6.5 * CM, -4.5 * CM).translate(0, 1.5 * CM),
            left_p1.translate(6.5 * CM, -4.5 * CM).translate(5 * CM, 1.5 * CM),
            name="precision point",
        ),
        style=StyleOptions(stroke_color="white", stroke_width=0.8),
    )

    # ---------------------------------------------------------------------------
    # All named line style presets — one line per preset, spaced 1.5 cm apart.
    # ---------------------------------------------------------------------------
    PRESETS = [
        ("grainline", None),  # rendered via add_grainline
        ("fold of fabric", STYLE_FOLD),
        ("hem", STYLE_HEM),
        ("stitching line", STYLE_STITCH),
        ("cutting line", STYLE_CUT),
        ("center line", STYLE_CENTER_LINE),
    ]

    for i, (label, style) in enumerate(PRESETS):
        y = (i + 0) * 1.5 * CM
        p1 = left_p1.translate(0, y)
        p2 = right_p1.translate(0, y)
        if style is None:
            lines.add_grainline(p1, p2, name=label)
        else:
            lines.append(Segment(p1, p2, name=label), style=style)

    # Notch demonstration — one row below the last preset line.
    notch_y = len(PRESETS) * 1.5 * CM
    notch_p1 = left_p1.translate(0, notch_y)
    notch_p2 = right_p1.translate(0, notch_y)
    notch_seg = Segment(notch_p1, notch_p2, name="notches")
    lines.append(notch_seg)

    # Place three notches at 25 %, 50 % and 75 % along the segment.
    seg_len = notch_p2.x - notch_p1.x
    lines.add_notches(
        notch_p1.translate(0.25 * seg_len, 0),
        notch_p1.translate(0.75 * seg_len, 0),
        seam_edge=notch_seg,
    )

    return legend


if __name__ == "__main__":
    part = make_legend()
    export_pattern_svg_mm(
        part,
        filename=str(Path(__file__).parent / "legend.svg"),
        height_mm=DinA4.height,
        width_mm=DinA4.width,
    )
