from sewpat.geometry import Rect, Point, Circle
from sewpat.units import CM, MM
from sewpat.style import StyleOptions, DEFAULT_STROKE_WIDTH


def get_precision_point(center: Point) -> list[Circle]:
    return [
        Circle(center, radius=5 * MM),
        Circle(center, radius=0.5 * MM),
    ]


def get_square(
    box_start: Point,
    edge_length: float = 3 * CM,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
) -> list[Rect]:
    return [
        Rect(
            origin=box_start,
            width=edge_length,
            height=edge_length,
            name=f"{edge_length / CM:.0f}cm x {edge_length / CM:.0f}cm",
            style=StyleOptions(stroke_width=stroke_width),
        )
    ]
