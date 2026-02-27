"""
Style options for rendering sewing pattern elements.

This module is intentionally kept separate from both ``geometry.py`` and
``render.py`` so that geometry objects can reference ``StyleOptions`` without
creating a circular import.
"""

from enum import Enum
from typing import Any


class Marker(str, Enum):
    """Named markers that can be placed at either end of a line element.

    The string value of each member matches the SVG ``<marker id="...">``
    defined in ``render.py``, so it can be used directly to build
    ``marker-start="url(#<value>)"`` attributes.

    Members:
        ARROW:    A filled triangular arrowhead pointing away from the line.
        SCISSOR:  A pair of scissor blades indicating a cutting start/end point.
        DISTANCE: An arrowhead with a perpendicular stop-bar; used for
                  dimension/measurement annotations (start and end variants
                  are selected automatically by position).
        DOT:      A small filled circle; useful for button positions or
                  match-point markers at line ends.
        STOP:     A short perpendicular bar at the line end; useful for
                  hem lines, dart ends, and adjustment lines.
    """

    ARROW = "arrow"
    SCISSOR = "scissor"
    DISTANCE = "distance"
    DOT = "dot"
    STOP = "stop"


# ---------------------------------------------------------------------------
# Stroke width constants — single source of truth for the whole library.
# Override DEFAULT_STROKE_WIDTH here to change all pattern lines at once.
# ---------------------------------------------------------------------------
DEFAULT_STROKE_WIDTH: float = 0.5
DEFAULT_STROKE_WIDTH_GRAIN: float = 0.2
DEFAULT_FONT_SIZE_MM: float = 5.0


class StyleOptions:
    """Style options for rendering pattern elements."""

    def __init__(
        self,
        stroke_color: str = "black",
        stroke_width: float = DEFAULT_STROKE_WIDTH,
        fill_color: str = "none",
        dash_array: list[float] | None = None,
        dash_offset: float = 0.0,
        opacity: float = 1.0,
        stroke_linejoin: str = "miter",
        stroke_miterlimit: float = 4.0,
        marker_start: Marker | None = None,
        marker_end: Marker | None = None,
        font_size_mm: float = DEFAULT_FONT_SIZE_MM,
        font_weight: str = "normal",
        font_style: str = "normal",
    ) -> None:
        """Initialize style options.

        Args:
            stroke_color: Color of the stroke (outline).
            stroke_width: Width of the stroke in SVG units.
            fill_color: Fill color for closed shapes.
            dash_array: List of values defining the dash pattern, or None for a solid line.
            dash_offset: Starting offset into the dash pattern (``stroke-dashoffset``).
            opacity: Opacity value between 0.0 (transparent) and 1.0 (opaque).
            stroke_linejoin: How line corners are joined (``"miter"``, ``"round"``, ``"bevel"``).
            stroke_miterlimit: Limit on miter joins before they are bevelled.
            marker_start: Optional :class:`Marker` to draw at the start of the element (p1).
                Supported values: ``Marker.ARROW``, ``Marker.SCISSOR``.
            marker_end: Optional :class:`Marker` to draw at the end of the element (p2).
                Supported values: ``Marker.ARROW``, ``Marker.SCISSOR``.
            font_size_mm: Font size in mm for the element label. Defaults to ``DEFAULT_FONT_SIZE_MM``.
            font_weight: CSS font-weight for labels (``"normal"``, ``"bold"``).
            font_style: CSS font-style for labels (``"normal"``, ``"italic"``).
        """
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.dash_array = dash_array
        self.dash_offset = dash_offset
        self.opacity = opacity
        self.stroke_linejoin = stroke_linejoin
        self.stroke_miterlimit = stroke_miterlimit
        self.marker_start = marker_start
        self.marker_end = marker_end
        self.font_size_mm = font_size_mm
        self.font_weight = font_weight
        self.font_style = font_style

    def as_dict(self) -> dict[str, Any]:
        """Convert style options to a dictionary.

        Returns:
            Dictionary with style attributes.
        """
        style_dict: dict[str, Any] = {
            "stroke": self.stroke_color,
            "stroke-width": self.stroke_width,
            "stroke-linejoin": self.stroke_linejoin,
            "stroke-miterlimit": self.stroke_miterlimit,
            "fill": self.fill_color,
            "opacity": self.opacity,
            "marker-start": self.marker_start.value if self.marker_start else None,
            "marker-end": self.marker_end.value if self.marker_end else None,
            "font-weight": self.font_weight,
            "font-style": self.font_style,
        }
        if self.dash_array:
            style_dict["stroke-dasharray"] = ",".join(map(str, self.dash_array))
            style_dict["stroke-dashoffset"] = self.dash_offset
        return style_dict


# ---------------------------------------------------------------------------
# Named style presets — ready-to-use StyleOptions for common pattern elements.
# ---------------------------------------------------------------------------

# -- Existing presets -------------------------------------------------------
# based on https://de.scribd.com/document/564488289/Guide-to-read-Basic-Pattern-Symbols


STYLE_GRAINLINE = StyleOptions(
    stroke_color="grey",
    stroke_width=DEFAULT_STROKE_WIDTH_GRAIN,
    marker_start=Marker.ARROW,
    marker_end=Marker.ARROW,
    dash_array=[3, 2],
)

STYLE_FOLD = StyleOptions(
    stroke_color="grey",
    dash_array=[10.0, 2.0],
)

STYLE_HEM = StyleOptions(
    stroke_color="black",
    marker_start=Marker.STOP,
    marker_end=Marker.STOP,
)

# Cutting Line — the outermost solid line; cut along this line.
# A scissor marker at the start indicates where to begin cutting.
STYLE_CUT = StyleOptions(
    stroke_color="black",
    marker_end=Marker.SCISSOR,
)

# Stitching Line — dashed line inside the cutting line showing where to sew.
STYLE_STITCH = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[5.0, 2.0],
)


# Center Front / Center Back Line — long-dash–short-dash line marking
# the vertical centre of a garment front or back.
STYLE_CENTER_LINE = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[10.0, 2.0, 2.0, 2.0],
)
