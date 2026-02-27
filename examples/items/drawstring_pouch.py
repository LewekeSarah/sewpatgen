from dataclasses import dataclass

from sewpat import PatternPart, Point
from sewpat.basic_shapes import get_square, get_precision_point
from sewpat.geometry import Rect, Segment, segment_to_intersection
from sewpat.units import CM
from sewpat.style import STYLE_GRAINLINE, STYLE_HEM, STYLE_SEAM
from sewpat.pages import DinA4
from sewpat.render import export_pattern_part_svg_mm, StyleOptions


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
    square_start = Point(0.2 * model.width, 0.5 * model.height, "p1")
    elems = get_square(square_start, edge_length=5 * CM)

    # SVG coordinates: x increases right, y increases down

    ## STEP 1
    # Anchor: top left
    top_left = Point(1.5 * CM, 1.5 * CM, "p1")

    ## STEP 2
    # Basic Rectangle
    bottom_left = top_left.translate(0, model.height)
    top_right = top_left.translate(model.width, 0)
    bottom_right = bottom_left.translate(model.width, 0)
    elems.append(
        Segment(
            bottom_left,
            top_left,
            style=STYLE_SEAM,
            name=f"Höhe {model.height / CM:.0f} cm",
        )
    )
    elems.append(
        Segment(
            top_left,
            top_right,
            style=STYLE_HEM,
            name=f"Breite {model.width / CM:.0f} cm",
        )
    )
    elems.append(Segment(top_right, bottom_right, style=STYLE_SEAM))
    elems.append(
        Segment(bottom_right, bottom_left, style=STYLE_SEAM, name="Wendeöffnung")
    )
    precision_points = get_precision_point(bottom_left) + get_precision_point(
        bottom_right
    )
    elems = elems + precision_points

    ## STEP 3
    # Drawstring channel — shown as a dashed rectangle inset from the top edge
    ds1_top_left = top_left.translate(0, model.drawstring_margin)
    ds1_top_right = top_right.translate(0, model.drawstring_margin)
    ds1_bottom_left = top_left.translate(
        0, (model.drawstring_margin + model.drawstring_height)
    )
    ds1_bottom_right = top_right.translate(
        0, (model.drawstring_margin + model.drawstring_height)
    )
    drawstring_style = StyleOptions(dash_array=[5.0, 2.0])
    elems.append(
        Rect(
            origin=ds1_top_left,
            width=model.width,
            height=model.drawstring_height,
            name="drawstring / Tunnelzug",
            style=drawstring_style,
        )
    )

    # STEP 3
    # Add grainline and marks
    # The grainline runs vertically through the horizontal centre of the piece,
    # from 2 cm below the top edge to 2 cm above the bottom edge.
    grain_padding = 2 * CM
    grain_x = top_left.x + model.width / 2
    elems.append(
        Segment(
            Point(grain_x, top_left.y + grain_padding),
            Point(grain_x, bottom_left.y - grain_padding),
            name="grainline / Fadenlauf",
            style=STYLE_GRAINLINE,
        )
    )

    # STEP 4
    # Add Seam Allowance
    top_left_sa = top_left.translate(-model.seam_allowance, -model.seam_allowance)
    bottom_left_sa = bottom_left.translate(-model.seam_allowance, model.seam_allowance)
    top_right_sa = top_right.translate(model.seam_allowance, -model.seam_allowance)
    bottom_right_sa = bottom_right.translate(model.seam_allowance, model.seam_allowance)

    sa_width = model.width + 2 * model.seam_allowance
    sa_height = model.height + 2 * model.seam_allowance
    elems.append(
        Rect(
            origin=top_left_sa,
            width=sa_width,
            height=sa_height,
            name=f"Nahtzugabe {model.seam_allowance / CM:.0f} cm",
        )
    )

    # Keep virtual edge segments for mark-intersection arithmetic (not rendered)
    left_edge = Segment(bottom_left_sa, top_left_sa)
    right_edge = Segment(top_right_sa, bottom_right_sa)
    bottom_edge = Segment(bottom_right_sa, bottom_left_sa)

    # Add marks
    _, s1 = segment_to_intersection(
        ds1_bottom_left.translate(-0.5 * CM, 0), -left_edge.unit_normal, left_edge
    )
    _, s2 = segment_to_intersection(
        ds1_top_left.translate(-0.5 * CM, 0), -left_edge.unit_normal, left_edge
    )
    _, s3 = segment_to_intersection(
        ds1_bottom_right.translate(0.5 * CM, 0), -right_edge.unit_normal, right_edge
    )
    _, s4 = segment_to_intersection(
        ds1_top_right.translate(0.5 * CM, 0), -right_edge.unit_normal, right_edge
    )
    node = bottom_right_sa.translate(
        -(model.width - model.flip_opening) / 2 - model.seam_allowance, -0.5 * CM
    )
    s5 = Segment(node, node.translate(0, 0.5 * CM))
    s6 = Segment(
        node.translate(-model.flip_opening, 0),
        node.translate(-model.flip_opening, 0.5 * CM),
    )
    elems.append(s1)
    elems.append(s2)
    elems.append(s3)
    elems.append(s4)
    elems.append(s5)
    elems.append(s6)


    return PatternPart(name="", elements=elems)


if __name__ == "__main__":
    drawstring_pouch = DrawstringPouchConfig(
        height=18.5 * CM,
        width=20 * CM,
        drawstring_height=2.5 * CM,
        drawstring_margin=1.5 * CM,
        seam_allowance=1 * CM,
        flip_opening=9 * CM,
    )
    part = make_drawstring_pouch(drawstring_pouch)

    export_pattern_part_svg_mm(
        part,
        filename="items/drawstring_pouch.svg",
        width_mm=DinA4.height,
        height_mm=DinA4.width,
    )
