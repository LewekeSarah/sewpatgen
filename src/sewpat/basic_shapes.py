from typing import List

from sewpat import Point, Circle
from sewpat.geometry import CM, Rect, MM
from sewpat.render import DEFAULT_STROKE_WIDTH


def get_precision_point(center: Point) -> List[Circle]:
    elems = [
        Circle(center, radius=5 * MM),
        Circle(center, radius=0.5 * MM),
    ]
    return elems


def get_square(box_start: Point, edge_length: float = 3 * CM, stroke_width: float = DEFAULT_STROKE_WIDTH) -> List[Rect]:
    return [
        Rect(
            origin=box_start,
            width=edge_length,
            height=edge_length,
            name=f"{edge_length / CM:.0f}cm x {edge_length / CM:.0f}cm",
        )
    ]
