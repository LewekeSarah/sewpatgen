from typing import List, Union

from sewpat import Point, Circle
from sewpat.geometry import CM, Segment, Rect, MM
from sewpat.render import StyleOptions


def get_precision_point(center: Point) -> List[Circle]:
    elems = [
        Circle(center, radius=5 * MM),
        Circle(center, radius=0.5 * MM),
    ]
    return elems

def get_square(box_start: Point, edge_length: float = 3 * CM) -> List[Union[Rect, Segment]]:
    stroke_width = 0.8
    border_style = StyleOptions(
        stroke_color="black",
        stroke_width=stroke_width,
        fill_color="none",
        font_size=10,
        text_anchor="middle",
    )
    label_bg_style = StyleOptions(
        stroke_color="none",
        stroke_width=0,
        fill_color="white",
    )
    label_height = edge_length * 0.4
    label_y = box_start.y + (edge_length - label_height) / 2

    return [
        # Outer border — draw.Rectangle places stroke centered on the geometry edge,
        # so we inset by stroke_width/2 to make the *outer* stroke edge sit at exactly
        # box_start and box_start + edge_length.
        Rect(
            origin=box_start.translate(stroke_width / 2, stroke_width / 2),
            width=edge_length - stroke_width,
            height=edge_length - stroke_width,
            style=border_style,
        ),
        # White background for the label
        Rect(
            origin=Point(box_start.x + stroke_width / 2, label_y),
            width=edge_length - stroke_width,
            height=label_height,
            style=label_bg_style,
        ),
        # Label text, rendered as a zero-length Segment so the existing text-on-path logic is reused
        Segment(
            box_start.translate(edge_length / 2, edge_length / 2),
            box_start.translate(edge_length / 2, edge_length / 2),
            style=StyleOptions(
                stroke_color="none",
                stroke_width=0,
                font_size=10,
                text_anchor="middle",
            ),
            name=f"{edge_length / CM :.0f}cm x {edge_length / CM :.0f}cm",
        ),
    ]
