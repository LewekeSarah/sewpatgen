from dataclasses import dataclass

from sewpat import PatternPart, Point
from sewpat.basic_shapes import get_square, get_precision_point
from sewpat.geometry import CM, Segment, segment_to_intersection
from sewpat.line_styles import get_grainline_style, get_hem_style, get_seam_style
from sewpat.pages import DinA4
from sewpat.render import render_pattern_part, StyleOptions


@dataclass
class DrawstringPouchConfig:
    height: float
    width: float
    drawstring_height: float
    drawstring_margin: float
    seam_allowance: float
    flip_opening: float


def make_drawstring_pouch(model: DrawstringPouchConfig):
    ## STEP 0:
    # Add size control
    square_start = Point(0.2 * model.width, 0, "p1")
    elems = get_square(square_start)

    # SVG coordinates: x increases right, y increases down

    ## STEP 1
    # Anchor: top left
    bottom_left = Point(-0.5 * model.width, 0.5 * model.height, "p1")

    ## STEP 2
    # Basic Rectangle
    # top_left = bottom_left.translate(0, -2 * model.height)
    top_left = bottom_left.translate(0, -1 * model.height)
    top_right = top_left.translate(model.width, 0)
    bottom_right = bottom_left.translate(model.width, 0)
    elems.append(Segment(bottom_left, top_left, style=get_seam_style()))
    elems.append(Segment(top_left, top_right, style=get_hem_style()))
    elems.append(Segment(top_right, bottom_right, style=get_seam_style()))
    elems.append(Segment(bottom_right, bottom_left, style=get_seam_style()))
    precision_points = get_precision_point(bottom_left) + get_precision_point(bottom_right)
    elems = elems + precision_points

    ## STEP 3
    # Drawstring top part
    ds1_top_left = top_left.translate(0, model.drawstring_margin)
    ds1_top_right = top_right.translate(0, model.drawstring_margin)
    ds1_bottom_left = top_left.translate(
        0, (model.drawstring_margin + model.drawstring_height)
    )
    ds1_bottom_right = top_right.translate(
        0, (model.drawstring_margin + model.drawstring_height)
    )
    elems.append(
        Segment(
            ds1_top_left,
            ds1_top_right,
            style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
        )
    )
    elems.append(
        Segment(
            ds1_bottom_left,
            ds1_bottom_right,
            name="drawstring / Tunnelzug",
            style=StyleOptions(
                dash_array=[5.0, 2.0], stroke_width=1, text_anchor="middle"
            ),
        )
    )

    # STEP 3
    # Add grainline and marks
    elems.append(
        Segment(
            bottom_left.translate(
                model.width / 2,
                -(model.drawstring_margin + model.drawstring_height) + 3 * CM,
            ),
            top_left.translate(
                model.width / 2,
                (model.drawstring_margin + model.drawstring_height) + 3 * CM,
            ),
            name="grainline / Fadenlauf",
            style=get_grainline_style(),
        )
    )

    # STEP 4
    # Add Seam Allowance
    top_left_sa = top_left.translate(-model.seam_allowance, -model.seam_allowance)
    bottom_left_sa = bottom_left.translate(-model.seam_allowance, model.seam_allowance)
    top_right_sa = top_right.translate(model.seam_allowance, -model.seam_allowance)
    bottom_right_sa = bottom_right.translate(model.seam_allowance, model.seam_allowance)
    left_edge = Segment(bottom_left_sa, top_left_sa)
    right_edge = Segment(top_right_sa, bottom_right_sa)
    bottom_edge = Segment(bottom_right_sa, bottom_left_sa)
    elems.append(left_edge)
    elems.append(Segment(top_left_sa, top_right_sa))
    elems.append(right_edge)
    elems.append(bottom_edge)

    # Add marks
    _, s1 = segment_to_intersection(
            ds1_bottom_left.translate(- 0.5 * CM, 0), -left_edge.unit_normal, left_edge
        )
    _, s2 = segment_to_intersection(
            ds1_top_left.translate(- 0.5 * CM, 0), -left_edge.unit_normal, left_edge
        )
    _, s3 = segment_to_intersection(
            ds1_bottom_right.translate(0.5 * CM, 0), -right_edge.unit_normal, right_edge
        )
    _, s4 = segment_to_intersection(
            ds1_top_right.translate(0.5 * CM, 0), -right_edge.unit_normal, right_edge
        )
    node = bottom_right_sa.translate(- (model.width - model.flip_opening) / 2 - model.seam_allowance , -0.5 * CM)
    s5 = Segment(node, node.translate(0, 0.5 * CM))
    s6 = Segment(node.translate(- model.flip_opening , 0), node.translate(- model.flip_opening , 0.5 * CM))
    elems.append(s1)
    elems.append(s2)
    elems.append(s3)
    elems.append(s4)
    elems.append(s5)
    elems.append(s6)

    # Drawstring bottom part
    # ds2_bottom_left = bottom_left.translate(0, -model.drawstring_margin)
    # ds2_bottom_right = bottom_right.translate(0, -model.drawstring_margin)
    # ds2_top_left = bottom_left.translate(
    #     0, -(model.drawstring_margin + model.drawstring_height)
    # )
    # ds2_top_right = bottom_right.translate(
    #     0, -(model.drawstring_margin + model.drawstring_height)
    # )
    # elems.append(
    #     Segment(
    #         ds2_bottom_left,
    #         ds2_bottom_right,
    #         name="Drawstring Back",
    #         style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
    #     )
    # )
    # elems.append(
    #     Segment(
    #         ds2_top_left,
    #         ds2_top_right,
    #         style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
    #     )
    # )

    return PatternPart(name="", elements=elems)


if __name__ == "__main__":
    drawstring_pouch = DrawstringPouchConfig(
        height=19 * CM,
        width=20 * CM,
        drawstring_height=2.5 * CM,
        drawstring_margin=1.5 * CM,
        seam_allowance=1 * CM,
        flip_opening=9 * CM,
    )
    part = make_drawstring_pouch(drawstring_pouch)

    d = render_pattern_part(part, DinA4.height, DinA4.width, font_size=12)
    d.save_svg("drawstring_pouch.svg")
