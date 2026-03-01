"""
Style options for rendering sewing pattern elements.

Kept separate from geometry.py and render.py to avoid circular imports.
"""

from enum import Enum
from typing import Any


class Marker(str, Enum):
    """Named markers placed at line endpoints.

    String values match ``<marker id="…">`` in render.py.

    Members:
        ARROW:    Filled triangular arrowhead.
        SCISSOR:  Scissor blades; indicates a cut start/end point.
        DISTANCE: Arrowhead with perpendicular stop-bar for dimension lines.
        DOT:      Small filled circle; button or match-point marker.
        STOP:     Short perpendicular bar; hem lines, dart ends.
    """

    ARROW = "arrow"
    SCISSOR = "scissor"
    DISTANCE = "distance"
    DOT = "dot"
    STOP = "stop"


# ---------------------------------------------------------------------------
# Stroke width constants
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
        seam_allowance: float | None = None,
        corner_join: str | None = None,
    ) -> None:
        """
        Args:
            seam_allowance: Per-element SA override in mm.  ``None`` (default)
                = use the global distance passed to ``add_seam_allowance()``.
                ``0.0`` = explicitly no seam allowance on this edge (e.g. fold line).
            corner_join: Per-element corner-join override (``"miter"``,
                ``"round"``, ``"bevel"``); ``None`` = use the part-wide default.
            All other arguments map directly to the identically named SVG attributes.
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
        self.seam_allowance = seam_allowance
        self.corner_join: str | None = corner_join

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StyleOptions):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __repr__(self) -> str:
        parts = []
        defaults = StyleOptions()
        for k, v in self.__dict__.items():
            if v != getattr(defaults, k):
                parts.append(f"{k}={v!r}")
        return f"StyleOptions({', '.join(parts)})"

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
            "font-size-mm": self.font_size_mm,
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
    seam_allowance=25.0,  # 2.5 cm default hem allowance
    dash_array=[10.0, 2.0],
)

STYLE_WAISTBAND = StyleOptions(
    stroke_color="black",
    marker_start=Marker.STOP,
    marker_end=Marker.STOP,
    seam_allowance=30.0,  # 3 cm default hem allowance
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

# Seam Allowance Line — thin solid outer line showing where to cut.
# Drawn outside (and parallel to) the stitching line by the seam allowance
# distance. No markers – the outline speaks for itself.
STYLE_SEAM_ALLOWANCE = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
)

# Debug highlight — thick red solid line used to visually verify which
# segments are selected for a seam-length comparison.  Import and apply
# temporarily; remove once the measurement is confirmed correct.
STYLE_DEBUG_RED = StyleOptions(
    stroke_color="red",
    stroke_width=1.5,
    opacity=0.7,
)

# Construction Grid Line — light grey dashed line for the construction grid layer.
STYLE_CONSTRUCTION_GRID = StyleOptions(
    stroke_color="lightgrey",
    stroke_width=0.8,
    opacity=0.8,
    dash_array=[3.0, 2.0],
)

