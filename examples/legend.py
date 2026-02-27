from sewpat import PatternPart, Point
from sewpat.basic_shapes import get_square, get_precision_point
from sewpat.geometry import Segment, segment_to_intersection
from sewpat.units import MM, CM
from sewpat.style import STYLE_GRAINLINE, STYLE_FOLD, STYLE_HEM, STYLE_SEAM
from sewpat.pages import DinA4
from sewpat.render import export_pattern_part_svg_mm, StyleOptions


def make_legend():
    sep = 5 * MM
    ## STEP 1.1
    # Anchor: top left
    left_p1 = Point(-0.5 * DinA4.width + sep, 0, "p1")
    right_p1 = left_p1.translate(0.75 * DinA4.width, 0)

    size_box_start = Point(-0.5 * DinA4.width + sep, - 4.5 * CM)
    size_box = get_square(size_box_start)
    precision_point = get_precision_point(left_p1.translate(6 * CM, - 3 * CM))
    elems = [
        Segment(
            left_p1.translate(6.5 * CM, -4.5 * CM).translate(0, 1.5 * CM),
            left_p1.translate(6.5 * CM, -4.5 * CM).translate(5 * CM, 1.5 * CM),
            style=StyleOptions(
                stroke_color="white",
                stroke_width=0.8,
                font_size=6,
                text_anchor="middle",
            ),
            name="precision point",
        ),
        Segment(left_p1, right_p1, name="grainline", style=STYLE_GRAINLINE),
        Segment(
            left_p1.translate(0, 1.5 * CM),
            right_p1.translate(0, 1.5 * CM),
            name="fold of fabric",
            style=STYLE_FOLD,
        ),
        Segment(
            left_p1.translate(0, 3 * CM),
            right_p1.translate(0, 3 * CM),
            name="hem",
            style=STYLE_HEM,
        ),
        Segment(
            left_p1.translate(0, 4.5 * CM),
            right_p1.translate(0, 4.5 * CM),
            name="seam / stitch",
            style=STYLE_SEAM,
        ),
    ]

    s = Segment(
            left_p1.translate(0, 6 * CM),
            right_p1.translate(0, 6 * CM),
            name="nips",
        )
    _, s1 = segment_to_intersection(
            left_p1.translate(0.4 * DinA4.width, 6.5 * CM), -s.unit_normal, s
        )
    elems.append(s)
    elems.append(s1)
    return PatternPart(name="Legend", elements=size_box + precision_point + elems)


if __name__ == "__main__":
    part = make_legend()
    export_pattern_part_svg_mm(part, filename="legend.svg", height_mm=DinA4.height, width_mm=DinA4.width)
