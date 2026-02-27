from sewpat import PatternPart, Point
from sewpat.geometry import Rect, Segment, segment_to_intersection
from sewpat.units import MM, CM
from sewpat.style import STYLE_FOLD, STYLE_HEM, STYLE_SEAM
from sewpat.pages import DinA4
from sewpat.render import export_pattern_part_svg_mm, StyleOptions


def make_legend():
    sep = 5 * MM
    ## STEP 1.1
    # Anchor: top left
    left_p1 = Point(-0.5 * DinA4.width + sep, 0, "p1")
    right_p1 = left_p1.translate(0.75 * DinA4.width, 0)

    part = PatternPart(name="Legend")

    size_box_origin = Point(-0.5 * DinA4.width + sep, -4.5 * CM)
    part.append(
        Rect(origin=size_box_origin, width=3 * CM, height=3 * CM, name="3cm × 3cm")
    )

    part.add_precision_points(left_p1.translate(6 * CM, -3 * CM))

    part.append(
        Segment(
            left_p1.translate(6.5 * CM, -4.5 * CM).translate(0, 1.5 * CM),
            left_p1.translate(6.5 * CM, -4.5 * CM).translate(5 * CM, 1.5 * CM),
            name="precision point",
        ),
        style=StyleOptions(
            stroke_color="white",
            stroke_width=0.8,
        ),
    )
    part.add_grainline(left_p1, right_p1, name="grainline")
    part.append(
        Segment(
            left_p1.translate(0, 1.5 * CM),
            right_p1.translate(0, 1.5 * CM),
            name="fold of fabric",
        ),
        style=STYLE_FOLD,
    )
    part.append(
        Segment(
            left_p1.translate(0, 3 * CM),
            right_p1.translate(0, 3 * CM),
            name="hem",
        ),
        style=STYLE_HEM,
    )
    part.append(
        Segment(
            left_p1.translate(0, 4.5 * CM),
            right_p1.translate(0, 4.5 * CM),
            name="seam / stitch",
        ),
        style=STYLE_SEAM,
    )

    s = Segment(
        left_p1.translate(0, 6 * CM),
        right_p1.translate(0, 6 * CM),
        name="nips",
    )
    _, s1 = segment_to_intersection(
        left_p1.translate(0.4 * DinA4.width, 6.5 * CM), -s.unit_normal, s
    )
    part.append(s)
    part.append(s1)
    return part


if __name__ == "__main__":
    part = make_legend()
    export_pattern_part_svg_mm(
        part, filename="legend.svg", height_mm=DinA4.height, width_mm=DinA4.width
    )
