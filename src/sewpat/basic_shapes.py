from typing import List

from sewpat import Point
from sewpat.geometry import CM, Segment
from sewpat.render import StyleOptions


def get_square(box_start: Point, edge_length: float = 3 * CM) -> List[Segment]:
    def get_size_box_style() -> StyleOptions:
        return StyleOptions(
            stroke_color="black",
            stroke_width=0.8,
            font_size=5,
            text_anchor="middle",
        )
    style = get_size_box_style()
    return [Segment(
            box_start.translate(-style.stroke_width / 2, 0),
            box_start.translate(edge_length + style.stroke_width / 2, 0),
            style=style,
        ),
        Segment(
            box_start.translate(0, edge_length / 2),
            box_start.translate(edge_length, edge_length / 2),
            style=StyleOptions(
                stroke_color="white",
                stroke_width=0.8,
                font_size=6,
                text_anchor="middle",
            ),
            name=f"{edge_length / CM :.0f}cm x {edge_length / CM :.0f}cm",
        ),
        Segment(
            box_start.translate(edge_length, 0),
            box_start.translate(edge_length, edge_length),
            style=style,
        ),
        Segment(
            box_start.translate(edge_length + style.stroke_width / 2, edge_length),
            box_start.translate(-style.stroke_width / 2, edge_length),
            style=style,
        ),
        Segment(
            box_start.translate(0, 3 * CM),
            box_start.translate(0, 0),
            style=style,
        ),
    ]
