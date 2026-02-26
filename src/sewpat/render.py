"""
SVG Rendering module for sewing patterns.

This module provides functions to render pattern parts and geometric elements
using the drawSvg library.
"""
from enum import Enum
from typing import Dict, List, Optional, Union, Any

from sewpat.geometry import Point, Line, Segment, Ray, Circle, Rect, CubicBezier, intersect
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
        self.stroke_linecap = stroke_linecap

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
            "stroke_linecap": self.stroke_linecap,
        }

        if self.dash_array:
            style_dict["stroke-dasharray"] = ",".join(map(str, self.dash_array))

        return style_dict



def export_pattern_part_svg_mm(
    pattern_part: PatternPart,
    filename: str,
    width_mm: float = 210,
    height_mm: float = 297,
    margin_mm: float = 10,
    font_size_mm: float = 5,
    style_map: Optional[Dict[str, StyleOptions]] = None,
    show_points: bool = True,
    show_bezier_control_points: bool = False
) -> None:
    """Exportiert ein PatternPart als SVG mit mm-Einheiten und Styles für präzises Drucken.

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
    # Default styles
    default_styles = {
        "segment": StyleOptions(stroke_color="black", stroke_width=0.5),
        "point": StyleOptions(stroke_color="black", fill_color="black", stroke_width=0.1),
        "circle": StyleOptions(stroke_color="black", stroke_width=0.5),
        "line": StyleOptions(stroke_color="gray", stroke_width=0.5, dash_array=[2, 2]),
        "ray": StyleOptions(stroke_color="gray", stroke_width=0.5, dash_array=[2, 2]),
        "cubicbezier": StyleOptions(stroke_color="black", stroke_width=0.5),
        "bezier_control": StyleOptions(stroke_color="red", fill_color="red", stroke_width=0.3),
    }
    if style_map:
        for k, v in style_map.items():
            if k in default_styles:
                default_styles[k] = v

    svg_header = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" viewBox="0 0 {width_mm} {height_mm}">'  # viewBox in mm
    svg_elements = []
    # Titel
    svg_elements.append(f'<text x="{margin_mm}" y="{margin_mm}" font-size="{font_size_mm}mm" fill="black">{pattern_part.name}</text>')
    # Elemente
    for element in pattern_part.elements:
        element_type = element.__class__.__name__.lower()
        style = default_styles.get(element_type, default_styles["segment"])
        style_dict = style.as_dict()
        # SVG-Attribute
        stroke = style_dict.get("stroke", "black")
        stroke_width = style_dict.get("stroke-width", 0.5)
        fill = style_dict.get("fill", "none")
        dasharray = style_dict.get("stroke-dasharray", None)
        opacity = style_dict.get("opacity", 1.0)
        if isinstance(element, CubicBezier):
            # SVG Path
            # Sichtbarkeit sicherstellen
            stroke = style_dict.get("stroke", "black")
            stroke_width = style_dict.get("stroke-width", 0.5)
            fill = "none"  # Bezier-Kurven immer ohne Füllung
            opacity = style_dict.get("opacity", 1.0)
            # Korrektur: stroke darf nicht 'none' sein
            if stroke == "none":
                stroke = "black"
            path_data = f'M {element.p0.x},{element.p0.y} C {element.p1.x},{element.p1.y} {element.p2.x},{element.p2.y} {element.p3.x},{element.p3.y}'
            svg_path_attrs = f'stroke="{stroke}" stroke-width="{stroke_width}mm" fill="{fill}" opacity="{opacity}"'
            if dasharray:
                svg_path_attrs += f' stroke-dasharray="{dasharray}"'
            svg_elements.append(
                f'<path d="{path_data}" {svg_path_attrs} />'
            )
            if hasattr(element, 'name') and element.name:
                svg_elements.append(
                    f'<text x="{element.p0.x}" y="{element.p0.y}" font-size="{font_size_mm}mm" fill="black">{element.name}</text>'
                )
            # Kontrollpunkte/linien
            if show_bezier_control_points:
                control_style = default_styles.get("bezier_control", StyleOptions(stroke_color="red", fill_color="red", stroke_width=0.3))
                control_dict = control_style.as_dict()
                control_stroke = control_dict.get("stroke", "red")
                control_fill = control_dict.get("fill", "red")
                control_width = control_dict.get("stroke-width", 0.3)
                # Kontrolllinien
                svg_elements.append(
                    f'<line x1="{element.p0.x}" y1="{element.p0.y}" x2="{element.p1.x}" y2="{element.p1.y}" stroke="{control_stroke}" stroke-width="{control_width}mm" fill="none" stroke-dasharray="2,2" />'
                )
                svg_elements.append(
                    f'<line x1="{element.p2.x}" y1="{element.p2.y}" x2="{element.p3.x}" y2="{element.p3.y}" stroke="{control_stroke}" stroke-width="{control_width}mm" fill="none" stroke-dasharray="2,2" />'
                )
                # Kontrollpunkte
                for pt in [element.p0, element.p1, element.p2, element.p3]:
                    svg_elements.append(
                        f'<circle cx="{pt.x}" cy="{pt.y}" r="1mm" stroke="{control_stroke}" fill="{control_fill}" stroke-width="{control_width}mm" />'
                    )
        # Segment/Linie
        elif isinstance(element, Segment):
            line_attrs = f'stroke="{stroke}" stroke-width="{stroke_width}mm" fill="none" opacity="{opacity}"'
            if dasharray:
                line_attrs += f' stroke-dasharray="{dasharray}"'
            svg_elements.append(
                f'<line x1="{element.p1.x}" y1="{element.p1.y}" x2="{element.p2.x}" y2="{element.p2.y}" {line_attrs} />'
            )
            if hasattr(element, 'name') and element.name:
                svg_elements.append(
                    f'<text x="{(element.p1.x + element.p2.x)/2}" y="{(element.p1.y + element.p2.y)/2}" font-size="{font_size_mm}mm" fill="black">{element.name}</text>'
                )
        # Kreis
        elif isinstance(element, Circle):
            svg_elements.append(
                f'<circle cx="{element.center.x}" cy="{element.center.y}" r="{element.radius}mm" stroke="{stroke}" fill="{fill}" stroke-width="{stroke_width}mm" opacity="{opacity}" />'
            )
        # Rect
        elif isinstance(element, Rect):
            rect_style = element.style.as_dict() if element.style is not None else style_dict
            rect_stroke = rect_style.get("stroke", "black")
            rect_stroke_width = rect_style.get("stroke-width", 0.5)
            rect_fill = rect_style.get("fill", "none")
            rect_opacity = rect_style.get("opacity", 1.0)
            rect_dasharray = rect_style.get("stroke-dasharray", None)
            rect_attrs = f'x="{element.origin.x}" y="{element.origin.y}" width="{element.width}" height="{element.height}" stroke="{rect_stroke}" stroke-width="{rect_stroke_width}" fill="{rect_fill}" opacity="{rect_opacity}"'
            if rect_dasharray:
                rect_attrs += f' stroke-dasharray="{rect_dasharray}"'
            svg_elements.append(f'<rect {rect_attrs} />')
            if element.name:
                cx = element.origin.x + element.width / 2
                cy = element.origin.y + element.height / 2
                svg_elements.append(
                    f'<text x="{cx}" y="{cy}" font-size="{font_size_mm}mm" fill="black" text-anchor="middle" dominant-baseline="middle">{element.name}</text>'
                )
        # Punkt
        elif isinstance(element, Point) and show_points:
            svg_elements.append(
                f'<circle cx="{element.x}" cy="{element.y}" r="1mm" stroke="{stroke}" fill="{fill}" stroke-width="{stroke_width}mm" opacity="{opacity}" />'
            )
            if element.name:
                svg_elements.append(
                    f'<text x="{element.x}" y="{element.y}" font-size="{font_size_mm}mm" fill="black">{element.name}</text>'
                )
    svg_footer = '</svg>'
    svg_content = '\n'.join([svg_header] + svg_elements + [svg_footer])
    with open(filename, 'w') as f:
        f.write(svg_content)

