from dataclasses import dataclass

from sewpat import Pattern, PatternPart, Point
from sewpat.geometry import Rect, Segment
from sewpat.units import CM
from sewpat.style import STYLE_HEM, STYLE_SEAM, StyleOptions
from sewpat.pages import DinA4
from sewpat.render import export_pattern_svg_mm


@dataclass
class DrawstringPouchConfig:
    height: float
    width: float
    drawstring_height: float
    drawstring_margin: float
    seam_allowance: float
    flip_opening: float


def make_drawstring_pouch(model: DrawstringPouchConfig) -> Pattern:
    pattern = Pattern(name="Drawstring Pouch")

    # -----------------------------------------------------------------------
    # Part 1: Main body
    # -----------------------------------------------------------------------
    body = PatternPart(name="body")
    pattern.add_part(body)

    ## STEP 0: Reference square for print-scale verification
    pattern.set_reference_square(
        origin=Point(0.2 * model.width, 0.5 * model.height),
    )

    # SVG coordinates: x increases right, y increases down

    ## STEP 1: Anchor: top left
    top_left = pattern.anchor

    ## STEP 2: Basic Rectangle
    bottom_left = top_left.translate(0, model.height)
    top_right = top_left.translate(model.width, 0)
    bottom_right = bottom_left.translate(model.width, 0)

    body.append(
        Segment(bottom_left, top_left),
        style=STYLE_SEAM,
    )
    body.append(
        Segment(top_left, top_right),
        style=STYLE_HEM,
    )
    body.append(Segment(top_right, bottom_right), style=STYLE_SEAM)
    body.append(
        Segment(bottom_right, bottom_left, name="Wendeöffnung"), style=STYLE_SEAM
    )

    body.add_precision_points(bottom_left, bottom_right)

    ## STEP 3: Grainline
    grain_padding = 2 * CM
    grain_x = top_left.x + model.width / 4 * 3
    body.add_grainline(
        start=Point(grain_x, top_left.y + grain_padding),
        end=Point(grain_x, bottom_left.y - grain_padding),
    )

    ## STEP 4: Seam Allowance
    top_left_sa = top_left.translate(-model.seam_allowance, -model.seam_allowance)
    bottom_left_sa = bottom_left.translate(-model.seam_allowance, model.seam_allowance)
    top_right_sa = top_right.translate(model.seam_allowance, -model.seam_allowance)
    bottom_right_sa = bottom_right.translate(model.seam_allowance, model.seam_allowance)

    sa_width = model.width + 2 * model.seam_allowance
    sa_height = model.height + 2 * model.seam_allowance
    body.append(
        Rect(
            origin=top_left_sa,
            width=sa_width,
            height=sa_height,
        ),
    )

    body.add_info_box(
        notes=[
            f"Nahtzugabe {model.seam_allowance / CM:.0f} cm",
            "2x gegengleich Außenstoff",
            "2x gegengleich Futterstoff, optional",
            f"Höhe {model.height / CM:.0f} cm",
            f"Breite {model.width / CM:.0f} cm",
        ]
    )

    # Virtual edge segments for mark-intersection arithmetic (not rendered)
    left_edge = Segment(bottom_left_sa, top_left_sa)
    right_edge = Segment(top_right_sa, bottom_right_sa)
    bottom_edge = Segment(bottom_right_sa, bottom_left_sa)

    # Add marks
    ds1_top_left = top_left.translate(0, model.drawstring_margin)
    ds1_top_right = top_right.translate(0, model.drawstring_margin)
    ds1_bottom_left = top_left.translate(
        0, model.drawstring_margin + model.drawstring_height
    )
    ds1_bottom_right = top_right.translate(
        0, model.drawstring_margin + model.drawstring_height
    )

    flip_left = bottom_right_sa.translate(
        -(model.width - model.flip_opening) / 2 - model.seam_allowance, 0
    )
    flip_right = flip_left.translate(-model.flip_opening, 0)

    body.add_notches(flip_left, flip_right, segment=bottom_edge)

    # -----------------------------------------------------------------------
    # Part 2: Drawstring channel
    # -----------------------------------------------------------------------
    drawstring = PatternPart(name="drawstring")
    pattern.add_part(drawstring)

    drawstring.append(
        Rect(
            origin=ds1_top_left,
            width=model.width,
            height=model.drawstring_height,
            name="drawstring / Tunnelzug",
        ),
        style=StyleOptions(dash_array=[5.0, 2.0]),
    )

    drawstring.add_notches(ds1_bottom_left, ds1_top_left, segment=left_edge)
    drawstring.add_notches(ds1_bottom_right, ds1_top_right, segment=right_edge)
    return pattern


if __name__ == "__main__":
    drawstring_pouch = DrawstringPouchConfig(
        height=18.5 * CM,
        width=20 * CM,
        drawstring_height=2.5 * CM,
        drawstring_margin=1.5 * CM,
        seam_allowance=1 * CM,
        flip_opening=9 * CM,
    )
    pattern = make_drawstring_pouch(drawstring_pouch)

    # Export complete pattern (body + drawstring channel)
    export_pattern_svg_mm(
        pattern,
        filename="items/drawstring_pouch.svg",
        width_mm=DinA4.height,
        height_mm=DinA4.width,
    )

    # Export body only (without drawstring channel markings)
    export_pattern_svg_mm(
        pattern,
        filename="items/drawstring_pouch_body_only.svg",
        width_mm=DinA4.height,
        height_mm=DinA4.width,
        parts=["body"],
    )
