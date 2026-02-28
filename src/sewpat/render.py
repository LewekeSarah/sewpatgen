"""
SVG Rendering module for sewing patterns.

This module provides functions to render pattern parts and geometric elements
to SVG files.
"""

import warnings
from typing import Any, Callable

import numpy as np

from sewpat.geometry import Point, Segment, Circle, Rect, Triangle, InfoBox, CubicBezier

from sewpat.part import PatternPart, PatternElement, Pattern
from sewpat.style import (
    StyleOptions,
    Marker,
    DEFAULT_FONT_SIZE_MM,
)
from sewpat.markers import ARROW_DEFS, SCISSOR_BLADE_OVERHANG

__all__ = [
    "StyleOptions",
    "Marker",
    "export_pattern_part_svg_mm",
    "export_pattern_svg_mm",
]


# ---------------------------------------------------------------------------
# Default style registry
# ---------------------------------------------------------------------------

_DEFAULT_STYLES: dict[str, StyleOptions] = {
    "segment": StyleOptions(),
    "point": StyleOptions(fill_color="black", stroke_width=0.1),
    "circle": StyleOptions(),
    "cubicbezier": StyleOptions(),
}


# ---------------------------------------------------------------------------
# Private per-element rendering helpers
# ---------------------------------------------------------------------------


def _svg_text(x: float, y: float, font_size_mm: float, text: str, **extra: str) -> str:
    """Return an SVG ``<text>`` element."""
    attrs = f'x="{x}" y="{y}" font-size="{font_size_mm}" fill="black"'
    for key, value in extra.items():
        attrs += f' {key}="{value}"'
    return f"<text {attrs}>{text}</text>"


def _common_stroke_attrs(
    style_dict: dict[str, Any], *, force_fill: str | None = None
) -> str:
    """Build common stroke/fill/opacity SVG attribute string from a style dict."""
    stroke = style_dict.get("stroke", "black") or "black"
    stroke_width = style_dict.get("stroke-width", 0.5)
    stroke_linejoin = style_dict.get("stroke-linejoin", "miter")
    stroke_miterlimit = style_dict.get("stroke-miterlimit", 4)
    fill = force_fill if force_fill is not None else style_dict.get("fill", "none")
    opacity = style_dict.get("opacity", 1.0)
    dasharray = style_dict.get("stroke-dasharray")
    dashoffset = style_dict.get("stroke-dashoffset", 0)

    attrs = (
        f'stroke="{stroke}" stroke-width="{stroke_width}mm" '
        f'stroke-linejoin="{stroke_linejoin}" stroke-miterlimit="{stroke_miterlimit}" '
        f'fill="{fill}" opacity="{opacity}"'
    )
    if dasharray:
        attrs += f' stroke-dasharray="{dasharray}" stroke-dashoffset="{dashoffset}"'
    return attrs


def _render_cubic_bezier(
    element: CubicBezier,
    style_dict: dict[str, Any],
    show_control_points: bool,
) -> list[str]:
    """Return SVG elements for a CubicBezier curve."""
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)

    path_data = (
        f"M {element.p0.x},{element.p0.y} "
        f"C {element.p1.x},{element.p1.y} "
        f"{element.p2.x},{element.p2.y} "
        f"{element.p3.x},{element.p3.y}"
    )
    attrs = _common_stroke_attrs(style_dict, force_fill="none")
    nodes.append(f'<path d="{path_data}" {attrs} />')

    if getattr(element, "name", None):
        nodes.append(_svg_text(element.p0.x, element.p0.y, font_size_mm, element.name))

    if show_control_points:
        c_stroke = "red"
        c_fill = "red"
        c_width = 0.3
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
    style_dict: dict[str, Any],
) -> list[str]:
    """Return SVG elements for a Segment."""
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    attrs = _common_stroke_attrs(style_dict, force_fill="none")

    # marker-start: arrows use a dedicated reversed marker id; distance uses its
    # own start variant; others use the enum value directly.
    ms = style_dict.get("marker-start")
    if ms == "arrow":
        attrs += ' marker-start="url(#arrow)"'
    elif ms == "distance":
        attrs += ' marker-start="url(#distance-start)"'
    elif ms:
        attrs += f' marker-start="url(#{ms})"'

    # marker-end: arrows use a dedicated "arrow-end" marker id; distance uses its
    # own end variant; others use the enum value directly.
    me = style_dict.get("marker-end")
    if me == "arrow":
        attrs += ' marker-end="url(#arrow-end)"'
    elif me == "distance":
        attrs += ' marker-end="url(#distance-end)"'
    elif me:
        attrs += f' marker-end="url(#{me})"'

    # For the scissor marker the refX is at the blade crossing, but the blade
    # tips reach back _SCISSOR_BLADE_OVERHANG mm into the line. Shorten p2 so
    # the visible line terminates exactly at the blade tips.
    x2, y2 = element.p2.x, element.p2.y
    if me == "scissor":
        dx = element.p2.x - element.p1.x
        dy = element.p2.y - element.p1.y
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            x2 -= SCISSOR_BLADE_OVERHANG * dx / length
            y2 -= SCISSOR_BLADE_OVERHANG * dy / length

    nodes.append(
        f'<line x1="{element.p1.x}" y1="{element.p1.y}" '
        f'x2="{x2}" y2="{y2}" {attrs} />'
    )
    if getattr(element, "name", None):
        mid_x = (element.p1.x + element.p2.x) / 2
        mid_y = (element.p1.y + element.p2.y) / 2
        # Offset the label above the line by half a font-size so it sits close
        # but doesn't overlap with the line itself.
        nodes.append(
            _svg_text(
                mid_x,
                mid_y - font_size_mm * 0.5,
                font_size_mm,
                element.name,
                **{
                    "text-anchor": "middle",
                    "font-weight": style_dict.get("font-weight", "normal"),
                    "font-style": style_dict.get("font-style", "normal"),
                },
            )
        )
    return nodes


def _render_circle(element: Circle, style_dict: dict[str, Any]) -> list[str]:
    """Return SVG elements for a Circle."""
    attrs = _common_stroke_attrs(style_dict)
    return [
        f'<circle cx="{element.center.x}" cy="{element.center.y}" r="{element.radius}mm" {attrs} />'
    ]


def _render_triangle(element: Triangle, style_dict: dict[str, Any]) -> list[str]:
    """Return an SVG polygon element for a filled Triangle (e.g. a notch)."""
    stroke = style_dict.get("stroke", "black") or "black"
    stroke_width = style_dict.get("stroke-width", 0.3)
    fill = style_dict.get("fill", "none")
    # Triangles used as notches should be filled by default
    if fill == "none":
        fill = "black"
    opacity = style_dict.get("opacity", 1.0)
    pts = (
        f"{element.p1.x},{element.p1.y} "
        f"{element.p2.x},{element.p2.y} "
        f"{element.p3.x},{element.p3.y}"
    )
    return [
        f'<polygon points="{pts}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}mm" '
        f'fill="{fill}" opacity="{opacity}" />'
    ]


def _render_info_box(element: InfoBox, style_dict: dict[str, Any]) -> list[str]:
    """Render an InfoBox as SVG text: header in bold, notes below."""
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    line_height = font_size_mm * 1.6
    x = element.position.x
    # Start y so the block is vertically centred on position
    total_lines = 1 + len(element.notes)
    y_start = element.position.y - (total_lines - 1) * line_height / 2

    # Header — slightly larger and bold via font-weight
    nodes.append(
        f'<text x="{x}" y="{y_start}" '
        f'font-size="{font_size_mm * 1.2}" font-weight="bold" fill="black" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f"{element.header}</text>"
    )
    # Notes
    for i, note in enumerate(element.notes):
        y = y_start + (i + 1) * line_height
        nodes.append(
            f'<text x="{x}" y="{y}" '
            f'font-size="{font_size_mm}" fill="black" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f"{note}</text>"
        )
    return nodes


def _render_rect(element: Rect, style_dict: dict[str, Any]) -> list[str]:
    """Return SVG elements for a Rect.

    SVG has no native ``stroke-alignment: inside``, but the same result is
    achieved by clipping the element to its own bounding box: the stroke is
    painted centred on the boundary as usual, but everything outside the
    declared rectangle is cut away, so the *outer* edge of the visible stroke
    coincides exactly with the declared width/height.

    A unique ``clipPath`` id is derived from the element's pixel-exact origin
    so that multiple rects on the same canvas don't collide.
    """
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    stroke_attrs = _common_stroke_attrs(style_dict)

    x, y = element.origin.x, element.origin.y
    w, h = element.width, element.height

    # Unique clip id — use integer representation of coords to avoid dots in ids
    clip_id = f"rc_{int(round(x * 100))}_{int(round(y * 100))}_{int(round(w * 100))}_{int(round(h * 100))}"

    nodes.append(
        f'<clipPath id="{clip_id}">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" /></clipPath>'
    )
    nodes.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'clip-path="url(#{clip_id})" {stroke_attrs} />'
    )

    if element.name:
        cx = x + w / 2
        cy = y + h / 2
        nodes.append(
            _svg_text(
                cx,
                cy,
                font_size_mm,
                element.name,
                **{"text-anchor": "middle", "dominant-baseline": "middle"},
            )
        )
    return nodes


def _render_point(element: Point, style_dict: dict[str, Any]) -> list[str]:
    """Return SVG elements for a Point."""
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    attrs = _common_stroke_attrs(style_dict, force_fill=style_dict.get("fill", "black"))
    nodes.append(f'<circle cx="{element.x}" cy="{element.y}" r="1mm" {attrs} />')
    if element.name:
        nodes.append(_svg_text(element.x, element.y, font_size_mm, element.name))
    return nodes


# ---------------------------------------------------------------------------
# Renderer registry
# ---------------------------------------------------------------------------


def _make_renderers(
    show_bezier_control_points: bool,
) -> dict[type, Callable[[Any, dict[str, Any]], list[str]]]:
    """Build a mapping from geometry type to its render callable."""
    return {
        CubicBezier: lambda el, sd: _render_cubic_bezier(
            el, sd, show_bezier_control_points
        ),
        Segment: lambda el, sd: _render_segment(el, sd),
        Circle: lambda el, sd: _render_circle(el, sd),
        Triangle: lambda el, sd: _render_triangle(el, sd),
        InfoBox: lambda el, sd: _render_info_box(el, sd),
        Rect: lambda el, sd: _render_rect(el, sd),
        Point: lambda el, sd: _render_point(el, sd),
    }


def _geoms_to_path_data(geoms: list[Segment | CubicBezier]) -> str:
    """Serialize a chain of Segment/CubicBezier geometries into an SVG path string.

    The chain is assumed to be sorted (end of element i == start of element i+1).
    A closing ``Z`` is appended when the last endpoint equals the first start point
    within 0.01 mm.

    Args:
        geoms: Ordered list of Segment or CubicBezier objects forming the chain.

    Returns:
        SVG path ``d`` attribute string (e.g. ``"M x,y L x,y C ... Z"``).
    """
    if not geoms:
        return ""

    def _start(g: Segment | CubicBezier) -> Point:
        return g.p1 if isinstance(g, Segment) else g.p0

    def _end(g: Segment | CubicBezier) -> Point:
        return g.p2 if isinstance(g, Segment) else g.p3

    parts: list[str] = []
    first_pt = _start(geoms[0])
    parts.append(f"M {first_pt.x},{first_pt.y}")

    for g in geoms:
        if isinstance(g, Segment):
            parts.append(f"L {g.p2.x},{g.p2.y}")
        else:  # CubicBezier
            parts.append(f"C {g.p1.x},{g.p1.y} {g.p2.x},{g.p2.y} {g.p3.x},{g.p3.y}")

    last_pt = _end(geoms[-1])
    if float(np.linalg.norm(last_pt.coords - first_pt.coords)) < 0.01:
        parts.append("Z")

    return " ".join(parts)


def _render_seam_allowance_chain(
    sa_elements: list["PatternElement"],
    style_dict: dict[str, Any],
) -> list[str]:
    """Render all seam-allowance Segment/CubicBezier elements as one SVG ``<path>``.

    Combining them into a single path ensures that SVG stroke-linejoin is
    applied at every corner, producing clean mitered/beveled joints without
    any visible gaps.

    Args:
        sa_elements: PatternElements with ``is_seam_allowance=True``.
        style_dict: Style attributes dict from the shared SA StyleOptions.

    Returns:
        List with one ``<path … />`` SVG string (or empty list if no geometry).
    """
    geoms: list[Segment | CubicBezier] = [
        e.geometry
        for e in sa_elements
        if isinstance(e.geometry, (Segment, CubicBezier))
    ]
    if not geoms:
        return []

    path_data = _geoms_to_path_data(geoms)
    if not path_data:
        return []

    attrs = _common_stroke_attrs(style_dict, force_fill="none")
    return [f'<path d="{path_data}" {attrs} />']


def _render_elements(
    elements: list["PatternElement"],
    svg_nodes: list[str],
    show_bezier_control_points: bool,
    show_points: bool,
) -> None:
    """Render a list of PatternElements into svg_nodes (in-place).

    Seam-allowance elements (``is_seam_allowance=True``) are collected and
    rendered as a single connected SVG ``<path>`` at the end so that
    ``stroke-linejoin`` is applied at every corner.
    """
    sa_elements: list["PatternElement"] = []
    sa_style_dict: dict[str, Any] | None = None

    renderers = _make_renderers(show_bezier_control_points)

    for pat_elem in elements:
        element = pat_elem.geometry

        # Collect SA geometry for grouped rendering — skip individual rendering.
        if pat_elem.is_seam_allowance and isinstance(element, (Segment, CubicBezier)):
            sa_elements.append(pat_elem)
            if sa_style_dict is None:
                sa_style_dict = pat_elem.style.as_dict()
            continue

        if not show_points and isinstance(element, Point):
            continue

        style = pat_elem.style
        effective_name = pat_elem.get_name()
        renderer = renderers.get(type(element))
        if renderer is not None:
            original_name = getattr(element, "name", None)
            try:
                (
                    object.__setattr__(element, "name", effective_name)
                    if isinstance(element, Point)
                    else setattr(element, "name", effective_name)
                )
            except (AttributeError, TypeError):
                pass
            svg_nodes.extend(renderer(element, style.as_dict()))
            try:
                (
                    object.__setattr__(element, "name", original_name)
                    if isinstance(element, Point)
                    else setattr(element, "name", original_name)
                )
            except (AttributeError, TypeError):
                pass

    # Render all SA elements as one connected path (clean corners via linejoin).
    if sa_elements and sa_style_dict is not None:
        svg_nodes.extend(_render_seam_allowance_chain(sa_elements, sa_style_dict))


# ---------------------------------------------------------------------------
# Public export functions
# ---------------------------------------------------------------------------


def _resolve_styles(
    style_map: dict[str, StyleOptions] | None,
    stacklevel: int = 3,
) -> dict[str, StyleOptions]:
    """Merge *style_map* overrides into a copy of ``_DEFAULT_STYLES``.

    Unknown keys emit a :class:`UserWarning` and are ignored.
    """
    styles = {**_DEFAULT_STYLES}
    if style_map:
        for k, v in style_map.items():
            if k in styles:
                styles[k] = v
            else:
                warnings.warn(
                    f"style_map key {k!r} does not match any known element type "
                    f"({list(styles.keys())}); it will be ignored.",
                    UserWarning,
                    stacklevel=stacklevel,
                )
    return styles


def _build_svg(
    title: str,
    element_groups: list[list[PatternElement]],
    width_mm: float,
    height_mm: float,
    margin_mm: float,
    show_points: bool,
    show_bezier_control_points: bool,
    show_seam_allowance: bool = True,
) -> str:
    """Build and return the SVG string for one or more element groups."""
    svg_nodes: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}" style="background-color:white">',
        ARROW_DEFS,
        _svg_text(margin_mm, margin_mm, DEFAULT_FONT_SIZE_MM, title),
    ]

    for elements in element_groups:
        visible = (
            elements
            if show_seam_allowance
            else [e for e in elements if not e.is_seam_allowance]
        )
        _render_elements(
            visible,
            svg_nodes,
            show_bezier_control_points,
            show_points,
        )

    svg_nodes.append("</svg>")
    return "\n".join(svg_nodes)


def export_pattern_part_svg_mm(
    pattern_part: PatternPart,
    filename: str,
    width_mm: float = 210,
    height_mm: float = 297,
    margin_mm: float = 10,
    style_map: dict[str, StyleOptions] | None = None,
    show_points: bool = True,
    show_bezier_control_points: bool = False,
    show_seam_allowance: bool = True,
) -> None:
    """Export a PatternPart as an SVG file with mm units for precise printing.

    Args:
        pattern_part: The PatternPart to export.
        filename: Output filename for the SVG.
        width_mm: Width of the SVG canvas in mm.
        height_mm: Height of the SVG canvas in mm.
        margin_mm: Margin around the canvas in mm.
        style_map: Optional mapping of element type names to StyleOptions overrides.
            Unknown keys emit a warning and are ignored.
        show_points: Whether to render Point elements.
        show_bezier_control_points: Whether to render Bezier control point handles.
        show_seam_allowance: Whether to render seam-allowance offset lines.
            Defaults to True. Set to False to export the pattern without seam
            allowance (e.g. for a "no seam allowance" variant).
    """
    styles = _resolve_styles(style_map)
    svg = _build_svg(
        title=pattern_part.name,
        element_groups=[pattern_part.elements],
        width_mm=width_mm,
        height_mm=height_mm,
        margin_mm=margin_mm,
        show_points=show_points,
        show_bezier_control_points=show_bezier_control_points,
        show_seam_allowance=show_seam_allowance,
    )
    with open(filename, "w") as f:
        f.write(svg)


def export_pattern_svg_mm(
    pattern: Pattern,
    filename: str,
    width_mm: float = 210,
    height_mm: float = 297,
    margin_mm: float = 10,
    style_map: dict[str, StyleOptions] | None = None,
    show_points: bool = True,
    show_bezier_control_points: bool = False,
    parts: list[str] | None = None,
    show_seam_allowance: bool = True,
) -> None:
    """Export a Pattern (all or selected parts) as a single SVG file.

    Args:
        pattern: The Pattern to export.
        filename: Output filename for the SVG.
        width_mm: Width of the SVG canvas in mm.
        height_mm: Height of the SVG canvas in mm.
        margin_mm: Margin around the canvas in mm.
        style_map: Optional mapping of element type names to StyleOptions overrides.
        show_points: Whether to render Point elements.
        show_bezier_control_points: Whether to render Bezier control point handles.
        parts: Optional list of part names to include. If None, all parts are rendered.
        show_seam_allowance: Whether to render seam-allowance offset lines.
            Defaults to True. Set to False to export the pattern without seam
            allowance (e.g. for a "no seam allowance" variant).
    """
    styles = _resolve_styles(style_map)

    selected_parts = (
        [p for p in pattern.parts if p.name in parts]
        if parts is not None
        else pattern.parts
    )

    # Always render the reference square first if set, then each part in order.
    element_groups: list[list[PatternElement]] = []
    if pattern.reference_square is not None:
        element_groups.append([pattern.reference_square])
    element_groups.extend(part.elements for part in selected_parts)

    svg = _build_svg(
        title=pattern.name,
        element_groups=element_groups,
        width_mm=width_mm,
        height_mm=height_mm,
        margin_mm=margin_mm,
        show_points=show_points,
        show_bezier_control_points=show_bezier_control_points,
        show_seam_allowance=show_seam_allowance,
    )
    with open(filename, "w") as f:
        f.write(svg)
