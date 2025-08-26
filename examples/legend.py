from sewpat import PatternPart, Point
from sewpat.basic_shapes import get_square
from sewpat.geometry import Segment, MM, CM
from sewpat.line_styles import (
    get_grainline_style,
    get_fold_style,
    get_hem_style,
    get_seam_style,
)
from sewpat.pages import DinA4
from sewpat.render import render_pattern_part


def make_legend():
    sep = 5 * MM
    ## STEP 1.1
    # Anchor: top left
    left_p1 = Point(-0.5 * DinA4.width + sep, 0, "p1")
    right_p1 = left_p1.translate(0.75 * DinA4.width, 0)

    size_box_start = Point(-0.5 * DinA4.width + sep, - 4.5 * CM)
    size_box = get_square(size_box_start)
    elems = [
        Segment(left_p1, right_p1, name="grainline", style=get_grainline_style()),
        Segment(
            left_p1.translate(0, 1.5 * CM),
            right_p1.translate(0, 1.5 * CM),
            name="fold of fabric",
            style=get_fold_style(),
        ),
        Segment(
            left_p1.translate(0, 3 * CM),
            right_p1.translate(0, 3 * CM),
            name="hem",
            style=get_hem_style(),
        ),
        Segment(
            left_p1.translate(0, 4.5 * CM),
            right_p1.translate(0, 4.5 * CM),
            name="seam / stitch",
            style=get_seam_style(),
        ),
    ]

    return PatternPart(name="Legend", elements=size_box + elems)


if __name__ == "__main__":
    part = make_legend()

    d = render_pattern_part(part, DinA4.width, DinA4.height, font_size=10)
    d.save_svg("legend.svg")
