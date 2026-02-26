"""
SVG Rendering module for sewing patterns.

This module provides functions to render pattern parts and geometric elements
to SVG files.
"""
from enum import Enum
from typing import Dict, List, Optional, Any

from sewpat.geometry import Point, Segment, Circle, Rect, CubicBezier
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
        stroke_linecap: str = "butt",
    ):
        """Initialize style options.

        Args:
            stroke_color: Color of the stroke (outline).
            stroke_width: Width of the stroke in SVG units.
            fill_color: Fill color for closed shapes.
            dash_array: List of values defining the dash pattern, or None for solid line.
            opacity: Opacity value between 0.0 (transparent) and 1.0 (opaque).
            marker_end: Line end style.
            text_anchor: Anchor style.
            font_size: Font size.
            stroke_linecap: Line cap style.
        """
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.dash_array = dash_array
        self.opacity = opacity
        self.marker_end = LineEndStyle(marker_end).value if marker_end else None
        self.font_size = font_size
        self.text_anchor = text_anchor
        self.stroke_linecap = stroke_linecap

    def as_dict(self) -> Dict[str, Any]:
        """Convert style options to a dictionary.

        Returns:
            Dictionary with style attributes.
        """
        style_dict: Dict[str, Any] = {
            "stroke": self.stroke_color,
            "stroke-width": self.stroke_width,
            "fill": self.fill_color,
            "opacity": self.opacity,
            "marker_end": self.marker_end,
            "font_size": self.font_size,
            "text_anchor": self.text_anchor,
            "stroke_linecap": self.stroke_linecap,
        }
        if self.dash_array:
            style_dict["stroke-dasharray"] = ",".join(map(str, self.dash_array))
        return style_dict


# ---------------------------------------------------------------------------
# Default style registry
# ---------------------------------------------------------------------------

_DEFAULT_STYLES: Dict[str, StyleOptions] = {
    "segment": StyleOptions(stroke_color="black", stroke_width=0.5),
    "point": StyleOptions(stroke_color="black", fill_color="black", stroke_width=0.1),
    "circle": StyleOptions(stroke_color="black", stroke_width=0.5),
    "line": StyleOptions(stroke_color="gray", stroke_width=0.5, dash_array=[2, 2]),
    "ray": StyleOptions(stroke_color="gray", stroke_width=0.5, dash_array=[2, 2]),
    "cubicbezier": StyleOptions(stroke_color="black", stroke_width=0.5),
    "bezier_control": StyleOptions(stroke_color="red", fill_color="red", stroke_width=0.3),
}


# ---------------------------------------------------------------------------
# Private per-element rendering helpers
# ---------------------------------------------------------------------------

def _svg_text(x: float, y: float, font_size_mm: float, text: str, **extra: str) -> str:
    """Return an SVG ``<text>`` element."""
    attrs = f'x="{x}" y="{y}" font-size="{font_size_mm}mm" fill="black"'
    for key, value in extra.items():
        attrs += f' {key}="{value}"'
    return f'<text {attrs}>{text}</text>'


def _common_stroke_attrs(style_dict: Dict[str, Any], *, force_fill: Optional[str] = None) -> str:
    """Build common stroke/fill/opacity SVG attribute string from a style dict."""
    stroke = style_dict.get("stroke", "black") or "black"
    stroke_width = style_dict.get("stroke-width", 0.5)
    fill = force_fill if force_fill is not None else style_dict.get("fill", "none")
    opacity = style_dict.get("opacity", 1.0)
    dasharray = style_dict.get("stroke-dasharray")

    attrs = f'stroke="{stroke}" stroke-width="{stroke_width}mm" fill="{fill}" opacity="{opacity}"'
    if dasharray:
        attrs += f' stroke-dasharray="{dasharray}"'
    return attrs


def _render_cubic_bezier(
    element: CubicBezier,
    style_dict: Dict[str, Any],
    font_size_mm: float,
    show_control_points: bool,
    control_style_dict: Dict[str, Any],
) -> List[str]:
    """Return SVG elements for a CubicBezier curve."""
    nodes: List[str] = []

    path_data = (
        f'M {element.p0.x},{element.p0.y} '
        f'C {element.p1.x},{element.p1.y} '
        f'{element.p2.x},{element.p2.y} '
        f'{element.p3.x},{element.p3.y}'
    )
    attrs = _common_stroke_attrs(style_dict, force_fill="none")
    nodes.append(f'<path d="{path_data}" {attrs} />')

    if getattr(element, "name", None):
        nodes.append(_svg_text(element.p0.x, element.p0.y, font_size_mm, element.name))

    if show_control_points:
        c_stroke = control_style_dict.get("stroke", "red")
        c_fill = control_style_dict.get("fill", "red")
        c_width = control_style_dict.get("stroke-width", 0.3)
        # Handle lines between anchor and control points
        for p_start, p_end in [(element.p0, element.p1), (element.p2, element.p3)]:
            nodes.append(
                f'<line x1="{p_start.x}" y1="{p_start.y}" x2="{p_end.x}" y2="{p_end.y}" '
                f'stroke="{c_stroke}" stroke-width="{c_width}mm" fill="none" stroke-dasharray="2,2" />'
            )
        for pt in [element.p0, element.p1, element.p2, element.p3]:
            nodes.append(
                f'<circle cx="{pt.x}" cy="{pt.y}" r="1mm" '
                f'stroke="{c_stroke}" fill="{c_fill}" stroke-width="{c_width}mm" />'
            )

    return nodes


def _render_segment(
    element: Segment,
    style_dict: Dict[str, Any],
    font_size_mm: float,
) -> List[str]:
    """Return SVG elements for a Segment."""
    nodes: List[str] = []
    attrs = _common_stroke_attrs(style_dict, force_fill="none")
    nodes.append(
        f'<line x1="{element.p1.x}" y1="{element.p1.y}" '
        f'x2="{element.p2.x}" y2="{element.p2.y}" {attrs} />'
    )
    if getattr(element, "name", None):
        mid_x = (element.p1.x + element.p2.x) / 2
        mid_y = (element.p1.y + element.p2.y) / 2
        nodes.append(_svg_text(mid_x, mid_y, font_size_mm, element.name))
    return nodes


def _render_circle(element: Circle, style_dict: Dict[str, Any]) -> List[str]:
    """Return SVG elements for a Circle."""
    stroke = style_dict.get("stroke", "black")
    stroke_width = style_dict.get("stroke-width", 0.5)
    fill = style_dict.get("fill", "none")
    opacity = style_dict.get("opacity", 1.0)
    return [
        f'<circle cx="{element.center.x}" cy="{element.center.y}" r="{element.radius}mm" '
        f'stroke="{stroke}" fill="{fill}" stroke-width="{stroke_width}mm" opacity="{opacity}" />'
    ]


def _render_rect(element: Rect, style_dict: Dict[str, Any], font_size_mm: float) -> List[str]:
    """Return SVG elements for a Rect."""
    nodes: List[str] = []
    # Element-level style overrides the passed style_dict when available.
    effective = element.style.as_dict() if element.style is not None else style_dict

    stroke = effective.get("stroke", "black")
    stroke_width = effective.get("stroke-width", 0.5)
    fill = effective.get("fill", "none")
    opacity = effective.get("opacity", 1.0)
    dasharray = effective.get("stroke-dasharray")

    attrs = (
        f'x="{element.origin.x}" y="{element.origin.y}" '
        f'width="{element.width}" height="{element.height}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}" '
        f'fill="{fill}" opacity="{opacity}"'
    )
    if dasharray:
        attrs += f' stroke-dasharray="{dasharray}"'
    nodes.append(f'<rect {attrs} />')

    if element.name:
        cx = element.origin.x + element.width / 2
        cy = element.origin.y + element.height / 2
        nodes.append(
            _svg_text(cx, cy, font_size_mm, element.name,
                      **{"text-anchor": "middle", "dominant-baseline": "middle"})
        )
    return nodes


def _render_point(element: Point, style_dict: Dict[str, Any], font_size_mm: float) -> List[str]:
    """Return SVG elements for a Point."""
    nodes: List[str] = []
    stroke = style_dict.get("stroke", "black")
    fill = style_dict.get("fill", "black")
    stroke_width = style_dict.get("stroke-width", 0.1)
    opacity = style_dict.get("opacity", 1.0)
    nodes.append(
        f'<circle cx="{element.x}" cy="{element.y}" r="1mm" '
        f'stroke="{stroke}" fill="{fill}" stroke-width="{stroke_width}mm" opacity="{opacity}" />'
    )
    if element.name:
        nodes.append(_svg_text(element.x, element.y, font_size_mm, element.name))
    return nodes


# ---------------------------------------------------------------------------
# Renderer registry
# ---------------------------------------------------------------------------

def _make_renderers(
    font_size_mm: float,
    show_bezier_control_points: bool,
    control_style_dict: Dict[str, Any],
    show_points: bool,
) -> Dict[type, Any]:
    """Build a mapping from geometry type to its render callable."""
    return {
        CubicBezier: lambda el, sd: _render_cubic_bezier(
            el, sd, font_size_mm, show_bezier_control_points, control_style_dict
        ),
        Segment: lambda el, sd: _render_segment(el, sd, font_size_mm),
        Circle: lambda el, sd: _render_circle(el, sd),
        Rect: lambda el, sd: _render_rect(el, sd, font_size_mm),
        Point: lambda el, sd: _render_point(el, sd, font_size_mm) if show_points else [],
    }


# ---------------------------------------------------------------------------
# Public export function
# ---------------------------------------------------------------------------

def export_pattern_part_svg_mm(
    pattern_part: PatternPart,
    filename: str,
    width_mm: float = 210,
    height_mm: float = 297,
    margin_mm: float = 10,
    font_size_mm: float = 5,
    style_map: Optional[Dict[str, StyleOptions]] = None,
    show_points: bool = True,
    show_bezier_control_points: bool = False,
) -> None:
    """Exportiert ein PatternPart als SVG mit mm-Einheiten für präzises Drucken.

    Args:
        pattern_part: Das zu exportierende PatternPart.
        filename: Dateiname für die SVG-Ausgabe.
        width_mm: Breite des SVG in mm.
        height_mm: Höhe des SVG in mm.
        margin_mm: Rand in mm.
        font_size_mm: Schriftgröße in mm.
        style_map: Optionales Mapping von Elementtypen zu StyleOptions.
        show_points: Ob Punkte angezeigt werden sollen.
        show_bezier_control_points: Ob Bezier-Kontrollpunkte angezeigt werden sollen.
    """
    # Merge caller overrides into a copy of the defaults.
    styles = {**_DEFAULT_STYLES}
    if style_map:
        styles.update({k: v for k, v in style_map.items() if k in styles})

    control_style_dict = styles["bezier_control"].as_dict()

    svg_nodes: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">',
        _svg_text(margin_mm, margin_mm, font_size_mm, pattern_part.name),
    ]

    renderers = _make_renderers(
        font_size_mm, show_bezier_control_points, control_style_dict, show_points
    )

    for element in pattern_part.elements:
        element_type = element.__class__.__name__.lower()
        style_dict = styles.get(element_type, styles["segment"]).as_dict()

        renderer = renderers.get(type(element))
        if renderer is not None:
            svg_nodes.extend(renderer(element, style_dict))

    svg_nodes.append("</svg>")

    with open(filename, "w") as f:
        f.write("\n".join(svg_nodes))

