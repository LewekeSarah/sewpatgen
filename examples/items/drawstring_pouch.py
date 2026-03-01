from dataclasses import dataclass
from pathlib import Path

from sewpat import Pattern, PatternPart, Point, Segment, STYLE_HEM, STYLE_WAISTBAND, STYLE_STITCH
from sewpat.geometry import Rect, intersect
from sewpat.part import ConstructionGrid
from sewpat.units import CM
from sewpat.style import StyleOptions
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
    pattern = Pattern(name="Drawstring Pouch", anchor=Point(1.2 * CM, 1.2 * CM))

    # -----------------------------------------------------------------------
    # Construction grid
    # -----------------------------------------------------------------------
    grid = ConstructionGrid(
        anchor=pattern.anchor,
        horizontals=[
            ("Oberkante",          0),
            ("Tunnelzug oben",     model.drawstring_margin),
            ("Tunnelzug unten",    model.drawstring_margin + model.drawstring_height),
            ("Unterkante",         model.height),
        ],
        verticals=[
            ("linke Kante",        0),
            ("rechte Kante",       model.width),
        ],
        part_name="Konstruktionsgitter Beutel",
    )
    grid_part = grid.build()
    pattern.add_part(grid_part)

    # Named grid lines
    g_top    = grid_part.get_element("Oberkante").geometry
    g_ds_top = grid_part.get_element("Tunnelzug oben").geometry
    g_ds_bot = grid_part.get_element("Tunnelzug unten").geometry
    g_bot    = grid_part.get_element("Unterkante").geometry
    g_left   = grid_part.get_element("linke Kante").geometry
    g_right  = grid_part.get_element("rechte Kante").geometry

    # Key points derived from grid intersections
    top_left     = intersect(g_top,  g_left)[0]
    top_right    = intersect(g_top,  g_right)[0]
    bottom_left  = intersect(g_bot,  g_left)[0]
    bottom_right = intersect(g_bot,  g_right)[0]

    # -----------------------------------------------------------------------
    # Part 1: Main body
    # -----------------------------------------------------------------------
    body = PatternPart(name="body")
    pattern.add_part(body)

    left_edge = body.append(
        Segment(bottom_left, top_left),
        style=STYLE_STITCH,
        is_outline=True,
    )
    body.append(
        Segment(top_left, top_right),
        style=STYLE_HEM,
        is_outline=True,
    )
    right_edge = body.append(
        Segment(top_right, bottom_right),
        style=STYLE_STITCH,
        is_outline=True,
    )
    body.append(
        Segment(bottom_right, bottom_left, name="Wendeöffnung (Futterstoff)"),
        style=STYLE_STITCH,
        is_outline=True,
    )

    # Virtual edge segments for mark-intersection arithmetic (not rendered)
    flip_left = bottom_right.translate(-(model.width - model.flip_opening) / 2, 0)
    flip_right = flip_left.translate(-model.flip_opening, 0)
    body.append(Segment(flip_left, flip_right), style=STYLE_WAISTBAND)

    body.add_precision_points(bottom_left, bottom_right)

    ## Reference square — placed after outline is built so auto-placement works
    pattern.add_reference_square(
        origin=Point(top_left.x + 0.2 * model.width, top_left.y + 0.5 * model.height),
        part=body,
    )

    ## Grainline
    grain_padding = 2 * CM
    grain_x = top_left.x + model.width / 4 * 3
    body.add_grainline(
        start=Point(grain_x, top_left.y + grain_padding),
        end=Point(grain_x, bottom_left.y - grain_padding),
    )

    ## Seam Allowance
    body.add_seam_allowance(model.seam_allowance)

    body.add_info_box(
        notes=[
            f"Nahtzugabe {model.seam_allowance / CM:.0f} cm",
            "2x gegengleich Außenstoff",
            "2x gegengleich Futterstoff, optional",
            f"Höhe {model.height / CM:.0f} cm",
            f"Breite {model.width / CM:.0f} cm",
        ]
    )

    ## Notches — automatically placed where outline edges cross grid lines
    body.add_grid_notches(grid_part, corner_clearance = 0.0,)

    # -----------------------------------------------------------------------
    # Part 2: Drawstring channel
    # -----------------------------------------------------------------------
    drawstring = PatternPart(name="drawstring")
    pattern.add_part(drawstring)

    drawstring.append(
        Rect(
            origin=intersect(g_ds_top, g_left)[0],
            width=model.width,
            height=model.drawstring_height,
            name="drawstring / Tunnelzug",
        ),
        style=StyleOptions(dash_array=[5.0, 2.0]),
    )

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
        filename=str(Path(__file__).parent / "drawstring_pouch.svg"),
        width_mm=DinA4.height,
        height_mm=DinA4.width,
    )

    # Export body only (without drawstring channel markings)
    export_pattern_svg_mm(
        pattern,
        filename=str(Path(__file__).parent / "drawstring_pouch_body_only.svg"),
        width_mm=DinA4.height,
        height_mm=DinA4.width,
        parts=["body"],
    )

    # Export complete pattern without seam allowance lines
    export_pattern_svg_mm(
        pattern,
        filename=str(Path(__file__).parent / "drawstring_pouch_no_sa.svg"),
        width_mm=DinA4.height,
        height_mm=DinA4.width,
        show_seam_allowance=False,
    )
