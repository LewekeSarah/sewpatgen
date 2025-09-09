"""
SVG Rendering module for sewing patterns.

This module provides functions to render pattern parts and geometric elements
using the drawSvg library.
"""
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any

import drawsvg as draw

from sewpat.geometry import Point, Line, Segment, Ray, Circle, CubicBezier, intersect
from sewpat.part import PatternPart

class LineEndStyle(Enum):
    arrow = "arrow"

class StyleOptions:
    """Style options for rendering pattern elements."""

    def __init__(
        self,
        stroke_color: str = "black",
        stroke_width: float = 0.5,
        fill_color: str = "none",
        dash_array: Optional[List[float]] = None,
        opacity: float = 1.0,
        marker_end: Optional[str] = None,
        text_anchor: str = "start",
        font_size: float = 12,
    ):
        """Initialize style options.

        Args:
            stroke_color: Color of the stroke (outline).
            stroke_width: Width of the stroke in SVG units.
            fill_color: Fill color for closed shapes.
            dash_array: List of values defining the dash pattern, or None for solid line.
            opacity: Opacity value between 0.0 (transparent) and 1.0 (opaque).
            marker_end: Line end style
            text_anchor: Anchor style
            font_size: Font size
        """
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.dash_array = dash_array
        self.opacity = opacity
        self.marker_end = LineEndStyle(marker_end).value if marker_end else None
        self.font_size = font_size
        self.text_anchor = text_anchor

    def as_dict(self) -> Dict[str, Any]:
        """Convert style options to a dictionary for drawSvg.

        Returns:
            Dictionary with style attributes.
        """
        style_dict = {
            "stroke": self.stroke_color,
            "stroke-width": self.stroke_width,
            "fill": self.fill_color,
            "opacity": self.opacity,
            "marker_end": self.marker_end,
            "font_size": self.font_size,
            "text_anchor": self.text_anchor,
        }

        if self.dash_array:
            style_dict["stroke-dasharray"] = ",".join(map(str, self.dash_array))

        return style_dict


def render_geometric_element(
    element: Union[Point, Line, Segment, Ray, Circle, CubicBezier],
    drawing: draw.Drawing,
    style: StyleOptions = StyleOptions(),
    viewport_bounds: Optional[Tuple[float, float, float, float]] = None,
    point_radius: float = 5.0,
    show_bezier_control_points: bool = False,
    control_point_style: Optional[StyleOptions] = None,
) -> None:
    """Render a geometric element to the SVG drawing.

    Args:
        element: The geometric element to render.
        drawing: The drawSvg drawing to render to.
        style: Style options for rendering.
        viewport_bounds: Optional (min_x, min_y, max_x, max_y) defining the visible area.
        point_radius: Radius to use when rendering points.
        show_bezier_control_points: Whether to show control points and lines for Bezier curves.
        control_point_style: Style for control points and control lines.
    """
    style_dict = style.as_dict()

    if isinstance(element, Point):
        drawing.append(draw.Circle(element.x, element.y, point_radius, **style_dict))

    elif isinstance(element, Segment):
        if style_dict["marker_end"] == LineEndStyle.arrow.value:
            arrow = draw.Marker(-0.1, -0.51, 1.8 , 1, scale=4, orient='auto')
            arrow.append(draw.Lines(-0.1 , 1, -0.1 , -1, 1.8 , 0, fill=style_dict["stroke"], close=True))
            style_dict["marker_end"] = arrow

        p = draw.Line(
            element.p1.x, element.p1.y, element.p2.x, element.p2.y, **style_dict
        )
        drawing.append(p)
        if element.name:
            drawing.append(
                draw.Text(
                    element.name,
                    style_dict["font_size"],
                    text_anchor=style_dict["text_anchor"],
                    fill="black",
                    path=p,
                )
            )

    elif isinstance(element, Circle):
        drawing.append(
            draw.Circle(
                element.center.x, element.center.y, element.radius, **style_dict
            )
        )

    elif isinstance(element, CubicBezier):
        # Render cubic Bezier curve as SVG path
        path_data = f"M {element.p0.x},{element.p0.y} C {element.p1.x},{element.p1.y} {element.p2.x},{element.p2.y} {element.p3.x},{element.p3.y}"

        # Remove fill from style for curves (keep stroke only)
        bezier_style = style_dict.copy()
        if bezier_style.get("fill", "none") != "none":
            bezier_style["fill"] = "none"

        drawing.append(draw.Path(d=path_data, **bezier_style))

        if element.name:
            drawing.append(
                draw.Text(
                    element.name,
                    style_dict["font_size"],
                    text_anchor=style_dict["text_anchor"],
                    fill="black",
                    path=draw.Line(element.p0.x, element.p0.y, element.p3.x, element.p3.y),
                )
            )

        # Optionally show control points and control lines
        if show_bezier_control_points:
            if control_point_style is None:
                control_point_style = StyleOptions(
                    stroke_color="red",
                    fill_color="red",
                    stroke_width=0.5
                )

            control_style_dict = control_point_style.as_dict()
            line_style_dict = control_point_style.as_dict()
            line_style_dict["fill"] = "none"
            line_style_dict["stroke_dasharray"] = "2,2"

            # Draw control lines
            drawing.append(draw.Line(
                element.p0.x, element.p0.y,
                element.p1.x, element.p1.y,
                **line_style_dict
            ))
            drawing.append(draw.Line(
                element.p2.x, element.p2.y,
                element.p3.x, element.p3.y,
                **line_style_dict
            ))

            # Draw control points
            drawing.append(draw.Circle(element.p0.x, element.p0.y, point_radius, **control_style_dict))
            drawing.append(draw.Circle(element.p1.x, element.p1.y, point_radius, **control_style_dict))
            drawing.append(draw.Circle(element.p2.x, element.p2.y, point_radius, **control_style_dict))
            drawing.append(draw.Circle(element.p3.x, element.p3.y, point_radius, **control_style_dict))

    elif isinstance(element, Line) or isinstance(element, Ray):
        # For infinite or semi-infinite lines, we need to clip to viewport
        if viewport_bounds is None:
            # Use drawing dimensions as default viewport
            min_x, min_y = -drawing.width / 2, -drawing.height / 2
            max_x, max_y = drawing.width / 2, drawing.height / 2
        else:
            min_x, min_y, max_x, max_y = viewport_bounds

        # Extend viewport slightly to ensure lines reach edges
        padding = 10
        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding

        if isinstance(element, Line):
            # For infinite line, find intersections with viewport bounds
            points = []

            # Create viewport edges as segments
            edges = [
                Segment(Point(min_x, min_y), Point(max_x, min_y)),  # bottom
                Segment(Point(max_x, min_y), Point(max_x, max_y)),  # right
                Segment(Point(max_x, max_y), Point(min_x, max_y)),  # top
                Segment(Point(min_x, max_y), Point(min_x, min_y)),  # left
            ]

            # Find intersections with each edge
            for edge in edges:
                intersection = intersect(element, edge)
                if intersection:
                    points.extend(intersection)

            # If we found at least 2 points, draw the line segment between them
            if len(points) >= 2:
                drawing.append(
                    draw.Line(
                        points[0].x, points[0].y, points[1].x, points[1].y, **style_dict
                    )
                )

        elif isinstance(element, Ray):
            # For ray, start at origin and find intersection with viewport
            origin = element.origin

            # Create viewport edges as segments
            edges = [
                Segment(Point(min_x, min_y), Point(max_x, min_y)),  # bottom
                Segment(Point(max_x, min_y), Point(max_x, max_y)),  # right
                Segment(Point(max_x, max_y), Point(min_x, max_y)),  # top
                Segment(Point(min_x, max_y), Point(min_x, min_y)),  # left
            ]

            # Find the first intersection
            for edge in edges:
                intersection = intersect(element, edge)
                if len(intersection) > 0:
                    drawing.append(
                        draw.Line(
                            origin.x,
                            origin.y,
                            intersection[0].x,
                            intersection[0].y,
                            **style_dict,
                        )
                    )
                    break


def render_pattern_part(
    pattern_part: PatternPart,
    width: float = 500,
    height: float = 500,
    margin: float = 20,
    show_points: bool = True,
    style_map: Optional[Dict[str, StyleOptions]] = None,
    font_size: int = 24,
    show_bezier_control_points: bool = False,
) -> draw.Drawing:
    """Render a pattern part to an SVG drawing.

    Args:
        pattern_part: The pattern part to render.
        width: Width of the SVG canvas in units.
        height: Height of the SVG canvas in units.
        margin: Margin around the pattern in units.
        show_points: Whether to show control points.
        style_map: Dictionary mapping element types to style options.
        font_size: Font size to use.
        show_bezier_control_points: Whether to show Bezier control points and control lines.

    Returns:
        A drawSvg Drawing object with the rendered pattern.
    """
    # Create a new drawing with origin at center
    drawing = draw.Drawing(width, height, origin="center")

    # Default styles if not provided
    default_styles = {
        "segment": StyleOptions(stroke_color="black", stroke_width=1.0),
        "point": StyleOptions(
            stroke_color="black", fill_color="black", stroke_width=0.1
        ),
        "circle": StyleOptions(stroke_color="black", stroke_width=1.0),
        "line": StyleOptions(stroke_color="gray", stroke_width=0.75, dash_array=[5, 5]),
        "ray": StyleOptions(stroke_color="gray", stroke_width=0.75, dash_array=[5, 5]),
        "cubicbezier": StyleOptions(stroke_color="black", stroke_width=1.0),
        "bezier_control": StyleOptions(stroke_color="red", fill_color="red", stroke_width=0.5),
    }

    # Override with provided styles
    if style_map:
        for k, v in style_map.items():
            if k in default_styles:
                default_styles[k] = v

    # Calculate viewport bounds
    # In a real implementation, you'd calculate this based on the actual pattern elements
    viewport_bounds = (
        -width / 2 + margin,
        -height / 2 + margin,
        width / 2 - margin,
        height / 2 - margin,
    )

    # Render each element with appropriate style
    for element in pattern_part.elements:
        element_type = element.__class__.__name__.lower()
        if isinstance(element, Segment):
            if element.style is not None:
                style = element.style
            else:
                style = default_styles.get(element_type, default_styles["segment"])
        else:
            style = default_styles.get(element_type, default_styles["segment"])

        # Get control point style for Bezier curves
        control_style = default_styles.get("bezier_control", None)

        render_geometric_element(
            element,
            drawing,
            style,
            viewport_bounds,
            show_bezier_control_points=show_bezier_control_points,
            control_point_style=control_style
        )

    # Add title/name
    drawing.append(
        draw.Text(
            pattern_part.name,
            font_size,
            -width / 2 + margin,
            height / 2 - margin,
            fill="black",
        )
    )

    return drawing


def save_pattern_part_svg(pattern_part: PatternPart, filename: str, **kwargs) -> None:
    """Render a pattern part and save it to an SVG file.

    Args:
        pattern_part: The pattern part to render.
        filename: Output filename for the SVG.
        **kwargs: Additional arguments passed to render_pattern_part.
    """
    drawing = render_pattern_part(pattern_part, **kwargs)
    drawing.save_svg(filename)


def bezier_to_svg_path(bezier: CubicBezier) -> str:
    """Convert a cubic Bezier curve to SVG path data string.

    Args:
        bezier: The cubic Bezier curve to convert.

    Returns:
        SVG path data string in the format "M x,y C x1,y1 x2,y2 x,y"
    """
    return f"M {bezier.p0.x},{bezier.p0.y} C {bezier.p1.x},{bezier.p1.y} {bezier.p2.x},{bezier.p2.y} {bezier.p3.x},{bezier.p3.y}"


def create_bezier_path_element(bezier: CubicBezier, style: StyleOptions) -> draw.Path:
    """Create a drawSvg Path element from a cubic Bezier curve.

    Args:
        bezier: The cubic Bezier curve to convert.
        style: Style options for the path.

    Returns:
        A drawSvg Path element.
    """
    path_data = bezier_to_svg_path(bezier)
    style_dict = style.as_dict()

    # Ensure fill is set to none for curves
    if style_dict.get("fill", "none") != "none":
        style_dict["fill"] = "none"

    return draw.Path(d=path_data, **style_dict)


def render_bezier_with_samples(
    bezier: CubicBezier,
    drawing: draw.Drawing,
    style: StyleOptions,
    num_samples: int = 50,
    show_sample_points: bool = False
) -> None:
    """Render a Bezier curve using line segments for better compatibility.

    This is useful when SVG path support is limited or for debugging purposes.

    Args:
        bezier: The cubic Bezier curve to render.
        drawing: The drawSvg drawing to render to.
        style: Style options for rendering.
        num_samples: Number of sample points to use for approximation.
        show_sample_points: Whether to show the sample points as small circles.
    """
    style_dict = style.as_dict()

    # Generate sample points along the curve
    prev_point = bezier.point_at_t(0.0)

    for i in range(1, num_samples + 1):
        t = i / num_samples
        curr_point = bezier.point_at_t(t)

        # Draw line segment
        drawing.append(draw.Line(
            prev_point.x, prev_point.y,
            curr_point.x, curr_point.y,
            **style_dict
        ))

        # Optionally show sample points
        if show_sample_points:
            point_style = style_dict.copy()
            point_style["fill"] = style_dict["stroke"]
            drawing.append(draw.Circle(
                curr_point.x, curr_point.y, 1.0, **point_style
            ))

        prev_point = curr_point


def get_bezier_bounds(bezier: CubicBezier) -> Tuple[float, float, float, float]:
    """Get the bounding box of a Bezier curve.

    Args:
        bezier: The cubic Bezier curve.

    Returns:
        Tuple of (min_x, min_y, max_x, max_y).
    """
    min_pt, max_pt = bezier.bounding_box()
    return min_pt.x, min_pt.y, max_pt.x, max_pt.y


if __name__ == "__main__":
    # Example usage

    def create_sample_pattern() -> PatternPart:
        """Create a sample pattern part for demonstration.

        Returns:
            A sample pattern part with some geometric elements.
        """
        part = PatternPart("Sample Bodice", [])

        # Add some geometric elements
        part.elements.append(Point(0, 0))
        part.elements.append(Point(100, 0))
        part.elements.append(Point(100, 150))
        part.elements.append(Point(0, 150))

        # Add segments to form a rectangle
        part.elements.append(Segment(Point(0, 0), Point(100, 0)))
        part.elements.append(Segment(Point(100, 0), Point(100, 150)))
        part.elements.append(Segment(Point(100, 150), Point(0, 150)))
        part.elements.append(Segment(Point(0, 150), Point(0, 0)))

        # Add a dart
        part.elements.append(Segment(Point(50, 0), Point(50, 40)))
        part.elements.append(Segment(Point(50, 40), Point(40, 0)))
        part.elements.append(Segment(Point(50, 40), Point(60, 0)))

        # Add a curved neckline
        c = Circle(Point(50, 150), 25)
        part.elements.append(c)

        # Add cubic Bezier curves for demonstration
        bezier1 = CubicBezier(
            Point(10, 100),   # Start point
            Point(30, 120),   # First control point
            Point(70, 120),   # Second control point
            Point(90, 100)    # End point
        )
        part.elements.append(bezier1)

        # Add another Bezier curve with different curvature
        bezier2 = CubicBezier(
            Point(10, 80),    # Start point
            Point(20, 60),    # First control point
            Point(80, 60),    # Second control point
            Point(90, 80)     # End point
        )
        part.elements.append(bezier2)

        l1 = Segment(Point(0, 50), Point(100, 50))
        l2 = Segment(Point(0, 20), Point(100, 20))
        l3 = Segment(Point(0, 0), Point(100, 100))
        l4 = Segment(Point(0, 80), Point(100, 5))

        part.elements.append(l1)
        part.elements.append(l2)
        part.elements.append(l3)
        part.elements.append(l4)

        part.elements.extend(intersect(l1, l2))
        part.elements.extend(intersect(l1, l3))
        part.elements.extend(intersect(l1, l4))
        part.elements.extend(intersect(l2, l3))
        part.elements.extend(intersect(l2, l4))
        part.elements.extend(intersect(l3, l4))

        r = Ray(Point(60, 160), [1.0, 1.0])
        part.elements.extend(intersect(c, Segment(Point(100, 150), Point(0, 150))))
        part.elements.append(r)
        part.elements.extend(intersect(c, r))
        L = Line(Point(40, 150), [1.0, -0.3])
        part.elements.append(L)
        part.elements.extend(intersect(c, L))

        L2 = Segment(Point(30, 125), Point(60, 125))
        part.elements.append(L2)
        part.elements.extend(intersect(c, L2))

        return part

    sample_part = create_sample_pattern()
    save_pattern_part_svg(sample_part, "sample_pattern.svg", show_bezier_control_points=True)
