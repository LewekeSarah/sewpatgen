"""SVG rendering for sewing patterns."""

from collections.abc import Callable
from typing import Any

import numpy as np

from sewpat.element import PatternElement
from sewpat.geometry import (
    Circle,
    CubicBezier,
    InfoBox,
    Line,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
)
from sewpat.markers import ARROW_DEFS, SCISSOR_BLADE_OVERHANG
from sewpat.pattern import (
    Block,
    ConstructionGridPart,
    Pattern,
    PatternPart,
)
from sewpat.style import (
    DEFAULT_FONT_SIZE_MM,
    Marker,
    StyleOptions,
)

__all__ = [
    "StyleOptions",
    "Marker",
    "export_pattern_part_svg_mm",
    "export_pattern_svg_mm",
]


_DEFAULT_STYLES: dict[str, StyleOptions] = {
    "segment": StyleOptions(),
    "point": StyleOptions(fill_color="#000000", stroke_width=0.1),
    "circle": StyleOptions(),
    "cubicbezier": StyleOptions(),
}


def _xml_escape(text: str) -> str:
    """Escape XML special characters for safe embedding in SVG text content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _svg_text(x: float, y: float, font_size_mm: float, text: str, **extra: str) -> str:
    """Return an SVG ``<text>`` element.

    Args:
        x: X coordinate in mm.
        y: Y coordinate in mm.
        font_size_mm: Font size in mm.
        text: Text content (will be XML-escaped).
        **extra: Additional SVG attribute key-value pairs.

    Returns:
        SVG ``<text>`` element string.
    """
    attrs = f'x="{x}" y="{y}" font-size="{font_size_mm}" fill="#000000"'
    for key, value in extra.items():
        attrs += f' {key}="{value}"'
    return f"<text {attrs}>{_xml_escape(text)}</text>"


def _common_stroke_attrs(style_dict: dict[str, Any], *, force_fill: str | None = None) -> str:
    """Build common stroke/fill/opacity SVG attribute string from a style dict.

    Colour values that may contain CSS ``var(…)`` references are placed inside
    a ``style="…"`` attribute so that all SVG viewers (including Inkscape) can
    resolve them correctly.  CSS variables are **not** supported in bare SVG
    presentation attributes by Inkscape and other non-browser renderers.

    Args:
        style_dict: Resolved style attributes dict from :meth:`StyleOptions.as_dict`.
        force_fill: When given, overrides the ``fill`` value from *style_dict*.

    Returns:
        Space-separated SVG attribute string ready for embedding in an element tag.
    """
    stroke = _resolve_stroke_color(style_dict.get("stroke", "black") or "black")
    stroke_width = style_dict.get("stroke-width", 0.5)
    stroke_linejoin = style_dict.get("stroke-linejoin", "miter")
    stroke_miterlimit = style_dict.get("stroke-miterlimit", 4)
    fill = force_fill if force_fill is not None else style_dict.get("fill", "none")
    opacity = style_dict.get("opacity", 1.0)
    dasharray = style_dict.get("stroke-dasharray")
    dashoffset = style_dict.get("stroke-dashoffset", 0)

    # Colours go into style="" so CSS variables are resolved by all renderers.
    style = f"stroke:{stroke};fill:{fill}"
    attrs = (
        f'style="{style}" '
        f'stroke-width="{stroke_width}" '
        f'stroke-linejoin="{stroke_linejoin}" stroke-miterlimit="{stroke_miterlimit}" '
        f'opacity="{opacity}"'
    )
    if dasharray:
        attrs += f' stroke-dasharray="{dasharray}" stroke-dashoffset="{dashoffset}"'
    return attrs


def _render_cubic_bezier(
    element: CubicBezier,
    style_dict: dict[str, Any],
    show_control_points: bool,
) -> list[str]:
    """Return SVG elements for a CubicBezier curve.

    Args:
        element: The Bézier curve geometry to render.
        style_dict: Resolved style attributes.
        show_control_points: When ``True``, render the control-point handles
            as dashed red lines with small circles at each control point.

    Returns:
        List of SVG element strings.
    """
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
        nodes.append(_svg_text(element.p0.x, element.p0.y, font_size_mm, str(element.name)))

    if show_control_points:
        c_stroke = _resolve_stroke_color("red")
        c_fill = _resolve_stroke_color("red")
        c_width = 0.3
        for p_start, p_end in [(element.p0, element.p1), (element.p2, element.p3)]:
            nodes.append(
                f'<line x1="{p_start.x}" y1="{p_start.y}" '
                f'x2="{p_end.x}" y2="{p_end.y}" '
                f'style="stroke:{c_stroke};fill:none" stroke-width="{c_width}" '
                f'stroke-dasharray="2,2" />'
            )
        for pt in [element.p0, element.p1, element.p2, element.p3]:
            nodes.append(
                f'<circle cx="{pt.x}" cy="{pt.y}" r="1" '
                f'style="stroke:{c_stroke};fill:{c_fill}" stroke-width="{c_width}" />'
            )

    return nodes


def _render_segment(
    element: Segment,
    style_dict: dict[str, Any],
) -> list[str]:
    """Return SVG elements for a Segment.

    Args:
        element: The segment geometry to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings.
    """
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    attrs = _common_stroke_attrs(style_dict, force_fill="none")

    ms = style_dict.get("marker-start")
    if ms == "arrow":
        attrs += ' marker-start="url(#arrow)"'
    elif ms == "distance":
        attrs += ' marker-start="url(#distance-start)"'
    elif ms:
        attrs += f' marker-start="url(#{ms})"'

    me = style_dict.get("marker-end")
    if me == "arrow":
        attrs += ' marker-end="url(#arrow-end)"'
    elif me == "distance":
        attrs += ' marker-end="url(#distance-end)"'
    elif me:
        attrs += f' marker-end="url(#{me})"'

    # Shorten p2 so the visible line ends at the blade tips, not the refX crossing.
    x2, y2 = element.p2.x, element.p2.y
    if me == "scissor":
        dx = element.p2.x - element.p1.x
        dy = element.p2.y - element.p1.y
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            x2 -= SCISSOR_BLADE_OVERHANG * dx / length
            y2 -= SCISSOR_BLADE_OVERHANG * dy / length

    nodes.append(f'<line x1="{element.p1.x}" y1="{element.p1.y}" x2="{x2}" y2="{y2}" {attrs} />')
    if getattr(element, "name", None):
        mid_x = (element.p1.x + element.p2.x) / 2
        mid_y = (element.p1.y + element.p2.y) / 2
        nodes.append(
            _svg_text(
                mid_x,
                mid_y - font_size_mm * 0.5,
                font_size_mm,
                str(element.name),
                **{
                    "text-anchor": "middle",
                    "font-weight": style_dict.get("font-weight", "normal"),
                    "font-style": style_dict.get("font-style", "normal"),
                },
            )
        )
    return nodes


def _render_line(element: Line, style_dict: dict[str, Any]) -> list[str]:
    """Render an infinite :class:`Line` by clipping it to a finite extent.

    The line is extended 1500 mm in each direction from its base point and
    then rendered as a regular :class:`Segment`.

    Args:
        element: The infinite line to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings.
    """
    extent = 1500.0
    p1 = element.point_at_distance(-extent)
    p2 = element.point_at_distance(extent)
    seg = Segment(p1, p2, name=element.name)
    return _render_segment(seg, style_dict)


def _render_ray(element: Ray, style_dict: dict[str, Any]) -> list[str]:
    """Render a semi-infinite :class:`Ray` by clipping it to a finite extent.

    The ray starts at its origin and extends 1500 mm in its direction.

    Args:
        element: The ray to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings.
    """
    extent = 1500.0
    seg = Segment(element.origin, element.point_at_distance(extent), name=element.name)
    return _render_segment(seg, style_dict)


def _render_circle(element: Circle, style_dict: dict[str, Any]) -> list[str]:
    """Return SVG elements for a Circle.

    The stroke is painted on the inside of the radius so the outer edge of the
    visible stroke coincides exactly with the declared radius.  This mirrors
    the ``stroke-alignment: inside`` behaviour used by ``_render_rect``.

    Args:
        element: The circle geometry to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings (clipPath + circle).
    """
    attrs = _common_stroke_attrs(style_dict)
    cx, cy, r = element.center.x, element.center.y, element.radius
    clip_id = f"cc_{int(round(cx * 100))}_{int(round(cy * 100))}_{int(round(r * 100))}"
    return [
        f'<clipPath id="{clip_id}"><circle cx="{cx}" cy="{cy}" r="{r}" /></clipPath>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" clip-path="url(#{clip_id})" {attrs} />',
    ]


def _render_triangle(element: Triangle, style_dict: dict[str, Any]) -> list[str]:
    """Return an SVG polygon element for a filled Triangle (e.g. a notch).

    Args:
        element: The triangle geometry to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings.
    """
    stroke = _resolve_stroke_color(style_dict.get("stroke", "black") or "black")
    stroke_width = style_dict.get("stroke-width", 0.3)
    fill = style_dict.get("fill", "none")
    if fill == "none":
        fill = _resolve_stroke_color("black")
    opacity = style_dict.get("opacity", 1.0)
    pts = (
        f"{element.p1.x},{element.p1.y} {element.p2.x},{element.p2.y} {element.p3.x},{element.p3.y}"
    )
    return [
        f'<polygon points="{pts}" '
        f'style="stroke:{stroke};fill:{fill}" '
        f'stroke-width="{stroke_width}" opacity="{opacity}" />'
    ]


def _render_info_box(element: InfoBox, style_dict: dict[str, Any]) -> list[str]:
    """Render an InfoBox as SVG text: header in bold, notes below.

    Args:
        element: The info box to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG ``<text>`` element strings.
    """
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    line_height = font_size_mm * 1.6
    x = element.position.x
    total_lines = 1 + len(element.notes)
    y_start = element.position.y - (total_lines - 1) * line_height / 2

    nodes.append(
        f'<text x="{x}" y="{y_start}" '
        f'font-size="{font_size_mm * 1.2}" font-weight="bold" fill="#000000" '
        f'text-anchor="middle" dominant-baseline="middle">'
        f"{_xml_escape(element.header)}</text>"
    )
    for i, note in enumerate(element.notes):
        y = y_start + (i + 1) * line_height
        nodes.append(
            f'<text x="{x}" y="{y}" '
            f'font-size="{font_size_mm}" fill="#000000" '
            f'text-anchor="middle" dominant-baseline="middle">'
            f"{_xml_escape(note)}</text>"
        )
    return nodes


def _render_rect(element: Rect, style_dict: dict[str, Any]) -> list[str]:
    """Return SVG elements for a Rect.

    SVG has no native ``stroke-alignment: inside``, but the same result is
    achieved by clipping the element to its own bounding box so the outer edge
    of the visible stroke coincides exactly with the declared width/height.

    Args:
        element: The rectangle geometry to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings (clipPath + rect + optional label).
    """
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    stroke_attrs = _common_stroke_attrs(style_dict)

    x, y = element.origin.x, element.origin.y
    w, h = element.width, element.height

    clip_id = (
        f"rc_{int(round(x * 100))}_{int(round(y * 100))}"
        f"_{int(round(w * 100))}_{int(round(h * 100))}"
    )

    nodes.append(
        f'<clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="{w}" height="{h}" /></clipPath>'
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
    """Return SVG elements for a Point.

    Args:
        element: The point geometry to render.
        style_dict: Resolved style attributes.

    Returns:
        List of SVG element strings.
    """
    nodes: list[str] = []
    font_size_mm = style_dict.get("font-size-mm", DEFAULT_FONT_SIZE_MM)
    attrs = _common_stroke_attrs(
        style_dict, force_fill=_resolve_stroke_color(style_dict.get("fill", "black"))
    )
    nodes.append(f'<circle cx="{element.x}" cy="{element.y}" r="1" {attrs} />')
    if element.name:
        nodes.append(_svg_text(element.x, element.y, font_size_mm, element.name))
    return nodes


# ---------------------------------------------------------------------------
# Renderer registry
# ---------------------------------------------------------------------------


def _make_renderers(
    show_bezier_control_points: bool,
) -> dict[type, Callable[[Any, dict[str, Any]], list[str]]]:
    """Build a mapping from geometry type to its render callable.

    Args:
        show_bezier_control_points: Passed through to :func:`_render_cubic_bezier`.

    Returns:
        Dict mapping each geometry type to a ``(element, style_dict) → list[str]``
        callable.
    """
    return {
        CubicBezier: lambda el, sd: _render_cubic_bezier(el, sd, show_bezier_control_points),
        Segment: lambda el, sd: _render_segment(el, sd),
        Line: lambda el, sd: _render_line(el, sd),
        Ray: lambda el, sd: _render_ray(el, sd),
        Circle: lambda el, sd: _render_circle(el, sd),
        Triangle: lambda el, sd: _render_triangle(el, sd),
        InfoBox: lambda el, sd: _render_info_box(el, sd),
        Rect: lambda el, sd: _render_rect(el, sd),
        Point: lambda el, sd: _render_point(el, sd),
    }


def _geoms_to_path_data(geoms: list[Segment | CubicBezier]) -> str:
    """Serialise a connected chain of Segment/CubicBezier objects into an SVG path string."""
    if not geoms:
        return ""

    parts: list[str] = []
    first_pt = geoms[0].start
    parts.append(f"M {first_pt.x},{first_pt.y}")

    for g in geoms:
        if isinstance(g, Segment):
            parts.append(f"L {g.p2.x},{g.p2.y}")
        else:  # CubicBezier
            parts.append(f"C {g.p1.x},{g.p1.y} {g.p2.x},{g.p2.y} {g.p3.x},{g.p3.y}")

    last_pt = geoms[-1].end
    if float(np.linalg.norm(last_pt.coords - first_pt.coords)) < 0.01:
        parts.append("Z")

    return " ".join(parts)


def _render_seam_allowance_chain(
    sa_elements: list[PatternElement],
    style_dict: dict[str, Any],
) -> list[str]:
    """Render all SA Segment/CubicBezier elements as one ``<path>`` for clean linejoin corners."""
    geoms: list[Segment | CubicBezier] = [
        e.geometry for e in sa_elements if isinstance(e.geometry, (Segment, CubicBezier))
    ]
    if not geoms:
        return []

    path_data = _geoms_to_path_data(geoms)
    if not path_data:  # pragma: no cover
        return []

    attrs = _common_stroke_attrs(style_dict, force_fill="none")
    return [f'<path d="{path_data}" {attrs} />']


def _render_elements(
    elements: list[PatternElement],
    svg_nodes: list[str],
    show_bezier_control_points: bool,
    show_construction: bool,
    styles: dict[str, StyleOptions] | None = None,
) -> None:
    """Render PatternElements into *svg_nodes* in-place.

    SA elements are collected and flushed as a single connected ``<path>`` at
    the end so ``stroke-linejoin`` applies at every corner.  Elements with
    ``is_construction=True`` are skipped when *show_construction* is ``False``.

    Args:
        elements: PatternElements to render.
        svg_nodes: List to append SVG strings to (mutated in-place).
        show_bezier_control_points: Render Bézier control-point handles.
        show_construction: Include construction elements in output.
        styles: Optional type-level style overrides.
    """
    _TYPE_KEY = {
        Segment: "segment",
        CubicBezier: "cubicbezier",
        Circle: "circle",
        Point: "point",
        Line: "segment",
        Ray: "segment",
    }

    sa_elements: list[PatternElement] = []
    sa_style_dict: dict[str, Any] | None = None

    renderers = _make_renderers(show_bezier_control_points)

    for pat_elem in elements:
        element = pat_elem.geometry

        if pat_elem.is_seam_allowance and isinstance(element, (Segment, CubicBezier)):
            sa_elements.append(pat_elem)
            if sa_style_dict is None:
                sa_style_dict = pat_elem.style.as_dict()
            continue

        if not show_construction and pat_elem.is_construction:
            continue

        style = pat_elem.style
        if styles is not None:
            type_key = _TYPE_KEY.get(type(element))
            if type_key and style == StyleOptions():
                style = styles.get(type_key, style)

        effective_name = pat_elem.get_name()
        renderer = renderers.get(type(element))
        if renderer is not None:
            original_name = getattr(element, "name", None)
            try:
                if isinstance(element, Point):
                    object.__setattr__(element, "name", effective_name)
            except AttributeError, TypeError:  # pragma: no cover
                pass
            svg_nodes.extend(renderer(element, style.as_dict()))
            try:
                if isinstance(element, Point):
                    object.__setattr__(element, "name", original_name)
            except AttributeError, TypeError:  # pragma: no cover
                pass

    if sa_elements and sa_style_dict is not None:
        svg_nodes.extend(_render_seam_allowance_chain(sa_elements, sa_style_dict))


def _resolve_styles(
    style_map: dict[str, StyleOptions] | None,
) -> dict[str, StyleOptions]:
    """Merge *style_map* overrides into ``_DEFAULT_STYLES``; unknown keys raise ``ValueError``."""
    styles = {**_DEFAULT_STYLES}
    if style_map:
        for k, v in style_map.items():
            if k in styles:
                styles[k] = v
            else:
                raise ValueError(
                    f"style_map key {k!r} does not match any known element type "
                    f"({list(styles.keys())})"
                )
    return styles


def _dark_mode_style(dark_mode: bool = True) -> str:
    """Return a ``<style>`` block that controls the canvas background colour.

    Stroke and fill colours are emitted as literal hex values in presentation
    attributes (Inkscape-compatible).  Dark mode for browser viewers is handled
    by overriding the ``svg`` background only — the strokes remain dark on a
    light background regardless of system preference when ``dark_mode=False``.

    When *dark_mode* is ``True`` the background flips to near-black in browsers
    that respect ``prefers-color-scheme: dark``.
    """
    base = "  svg { background-color: #ffffff; }\n"
    dark_override = (
        "  @media (prefers-color-scheme: dark) {\n    svg { background-color: #1e1e1e; }\n  }\n"
    )
    return "<style>\n" + base + (dark_override if dark_mode else "") + "</style>"


def _resolve_stroke_color(color: str) -> str:
    """Map a named colour to its light-mode hex value.

    Literal hex values are used in presentation attributes so that all viewers
    — including Inkscape, which does not support CSS custom properties in SVG
    attributes — render lines correctly.  The ``<style>`` block handles
    dark-mode overrides for browser-based viewers via CSS class selectors.
    """
    _MAP = {
        "black": "#000000",
        "white": "#ffffff",
        "grey": "#555555",
        "lightgrey": "#aaaaaa",
        "red": "#cc0000",
        "none": "none",
    }
    return _MAP.get(color.lower(), color)


def _build_svg(
    title: str,
    element_groups: list[list[PatternElement]],
    width_mm: float,
    height_mm: float,
    margin_mm: float,
    show_construction: bool,
    show_bezier_control_points: bool,
    show_seam_allowance: bool = True,
    styles: dict[str, StyleOptions] | None = None,
    dark_mode: bool = True,
) -> str:
    """Build and return the SVG string for one or more element groups.

    Args:
        title: Label rendered in the top-left corner of the canvas.
        element_groups: Each sub-list is one pattern part's elements.
        width_mm: Canvas width in mm.
        height_mm: Canvas height in mm.
        margin_mm: Canvas margin in mm.
        show_construction: Include construction elements.
        show_bezier_control_points: Render Bézier control-point handles.
        show_seam_allowance: Include SA offset lines.
        styles: Optional type-level style overrides.
        dark_mode: When ``False`` the SVG is always rendered with a white
            background and dark strokes, ignoring the system colour scheme.

    Returns:
        Complete SVG document as a string.
    """
    resolved = styles if styles is not None else _DEFAULT_STYLES
    svg_nodes: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">',
        _dark_mode_style(dark_mode=dark_mode),
        ARROW_DEFS,
        _svg_text(margin_mm, margin_mm, DEFAULT_FONT_SIZE_MM, title),
    ]

    for elements in element_groups:
        if show_seam_allowance:
            visible = [e for e in elements if not e.is_seam_notch]
        else:
            visible = [e for e in elements if not e.is_seam_allowance]
        _render_elements(
            visible,
            svg_nodes,
            show_bezier_control_points,
            show_construction,
            resolved,
        )

    svg_nodes.append("</svg>")
    return "\n".join(svg_nodes) + "\n"


def export_pattern_part_svg_mm(
    pattern_part: PatternPart,
    filename: str,
    width_mm: float = 210,
    height_mm: float = 297,
    margin_mm: float = 10,
    style_map: dict[str, StyleOptions] | None = None,
    show_construction: bool = True,
    show_bezier_control_points: bool = False,
    show_seam_allowance: bool = True,
    dark_mode: bool = True,
) -> None:
    """Export a single PatternPart as an SVG file with mm units.

    Args:
        pattern_part: Part to export.
        filename: Output SVG path.
        width_mm: Canvas width in mm.
        height_mm: Canvas height in mm.
        margin_mm: Canvas margin in mm.
        style_map: Element-type → StyleOptions overrides; unknown keys warn.
        show_construction: Render elements flagged ``is_construction=True``.
            Set to ``False`` for a clean print view without drafting aids.
        show_bezier_control_points: Render Bézier control-point handles.
        show_seam_allowance: Include SA offset lines (default True).
        dark_mode: When ``False`` the SVG always uses a white background and
            dark strokes, ignoring the viewer's system colour scheme.
    """
    styles = _resolve_styles(style_map)
    svg = _build_svg(
        title=pattern_part.name,
        element_groups=[pattern_part.elements],
        width_mm=width_mm,
        height_mm=height_mm,
        margin_mm=margin_mm,
        show_construction=show_construction,
        show_bezier_control_points=show_bezier_control_points,
        show_seam_allowance=show_seam_allowance,
        styles=styles,
        dark_mode=dark_mode,
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
    show_construction: bool = True,
    show_bezier_control_points: bool = False,
    parts: list[str] | None = None,
    show_seam_allowance: bool = True,
    dark_mode: bool = True,
) -> None:
    """Export a Pattern (all or selected parts) as a single SVG file.

    Args:
        pattern: Pattern to export.
        filename: Output SVG path.
        width_mm: Canvas width in mm.
        height_mm: Canvas height in mm.
        margin_mm: Canvas margin in mm.
        style_map: Element-type → StyleOptions overrides; unknown keys warn.
        show_construction: Render elements flagged ``is_construction=True``.
            Set to ``False`` for a clean print view without drafting aids.
        show_bezier_control_points: Render Bézier control-point handles.
        parts: Part names to include.  When ``None``, all parts are rendered
            except :class:`ConstructionGridPart` and :class:`Block` — those
            must be requested explicitly by name.
        show_seam_allowance: Include SA offset lines (default True).
        dark_mode: When ``False`` the SVG always uses a white background and
            dark strokes, ignoring the viewer's system colour scheme.
    """
    styles = _resolve_styles(style_map)

    if parts is not None:
        selected_parts = [p for p in pattern.parts if p.name in parts]
    else:
        selected_parts = [
            p for p in pattern.parts if not isinstance(p, (ConstructionGridPart, Block))
        ]

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
        show_construction=show_construction,
        show_bezier_control_points=show_bezier_control_points,
        show_seam_allowance=show_seam_allowance,
        styles=styles,
        dark_mode=dark_mode,
    )
    with open(filename, "w") as f:
        f.write(svg)
