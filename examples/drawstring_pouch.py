from dataclasses import dataclass

from sewpat import PatternPart, Point
from sewpat.geometry import CM, Segment, MM
from sewpat.line_styles import get_grainline_style, get_fold_style
from sewpat.render import render_pattern_part, StyleOptions


@dataclass
class DrawstringPouchConfig:
    height: float
    width: float
    drawstring_height: float
    drawstring_margin: float


def make_drawstring_pouch(model: DrawstringPouchConfig):
    elems = []

    # SVG coordinates: x increases right, y increases down

    ## STEP 1.1
    # Anchor: top left
    bottom_left = Point(-0.5 * model.width, model.height, "p1")

    ## STEP 1.2
    # Basic Rectangle
    top_left = bottom_left.translate(0, -2 * model.height)
    top_right = top_left.translate(model.width, 0)
    bottom_right = bottom_left.translate(model.width, 0)
    elems.append(Segment(bottom_left, top_left))
    elems.append(
        Segment(
            bottom_left.translate(
                model.width / 2,
                - (model.drawstring_margin + model.drawstring_height),
            ),
            top_left.translate(
                model.width / 2,
                (model.drawstring_margin + model.drawstring_height)
            ),
            name="grainline",
            style=get_grainline_style()
        )
    )
    elems.append(Segment(top_left, top_right))
    elems.append(Segment(top_right, bottom_right))
    elems.append(Segment(bottom_right, bottom_left))
    elems.append(
        Segment(
            bottom_right.translate(0, -model.height),
            bottom_left.translate(0, -model.height),
            name="fold of fabric",
            style=get_fold_style()
        )
    )

    ## STEP 2.1
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
            name="Drawstring Front",
            style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
        )
    )
    elems.append(
        Segment(
            ds1_bottom_left,
            ds1_bottom_right,
            style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
        )
    )

    # Drawstring bottom part
    ds2_bottom_left = bottom_left.translate(0, -model.drawstring_margin)
    ds2_bottom_right = bottom_right.translate(0, -model.drawstring_margin)
    ds2_top_left = bottom_left.translate(
        0, -(model.drawstring_margin + model.drawstring_height)
    )
    ds2_top_right = bottom_right.translate(
        0, -(model.drawstring_margin + model.drawstring_height)
    )
    elems.append(
        Segment(
            ds2_bottom_left,
            ds2_bottom_right,
            name="Drawstring Back",
            style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
        )
    )
    elems.append(
        Segment(
            ds2_top_left,
            ds2_top_right,
            style=StyleOptions(dash_array=[5.0, 2.0], stroke_width=1),
        )
    )

    return PatternPart(name="Drawstring Pouch", elements=elems)


if __name__ == "__main__":
    drawstring_pouch = DrawstringPouchConfig(
        height=21 * CM,
        width=21 * CM,
        drawstring_height=2.5 * CM,
        drawstring_margin=1.5 * CM,
    )
    part = make_drawstring_pouch(drawstring_pouch)

    d = render_pattern_part(part, 420 * MM, 595 * MM,font_size=10)
    d.save_svg("drawstring_pouch.svg")
