"""Style options and named presets for rendering sewing pattern elements."""

from enum import StrEnum
from typing import Any


class Marker(StrEnum):
    """Named markers placed at line endpoints.

    String values match ``<marker id="…">`` definitions in the SVG renderer.
    """

    ARROW = "arrow"
    SCISSOR = "scissor"
    DISTANCE = "distance"
    DOT = "dot"
    STOP = "stop"


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
        no_notch: bool = False,
    ) -> None:
        """Initialise with the given visual properties.

        Args:
            stroke_color: SVG stroke colour string.
            stroke_width: Stroke width in mm.
            fill_color: SVG fill colour string.
            dash_array: Dash pattern lengths in mm.
            dash_offset: Dash pattern start offset.
            opacity: Stroke opacity (0–1).
            stroke_linejoin: SVG stroke-linejoin value.
            stroke_miterlimit: SVG stroke-miterlimit value.
            marker_start: Optional marker at the segment start.
            marker_end: Optional marker at the segment end.
            font_size_mm: Label font size in mm.
            font_weight: CSS font-weight string.
            font_style: CSS font-style string.
            seam_allowance: Per-element SA override in mm.  ``None`` = use the
                global distance passed to ``add_seam_allowance()``.  ``0.0`` =
                explicitly no seam allowance on this edge (e.g. fold line).
            corner_join: Per-element corner-join override (``"miter"``,
                ``"round"``, ``"bevel"``); ``None`` = use the part-wide default.
            no_notch: When ``True``, :func:`~sewpat.pattern.add_grid_notches`
                never places a notch on this edge regardless of grid
                intersections.
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
        self.no_notch: bool = no_notch

    def __eq__(self, other: object) -> bool:
        """Return ``True`` when all style attributes are equal."""
        if not isinstance(other, StyleOptions):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __repr__(self) -> str:
        """Return a compact representation showing only non-default attributes."""
        parts = []
        defaults = StyleOptions()
        for k, v in self.__dict__.items():
            if v != getattr(defaults, k):
                parts.append(f"{k}={v!r}")
        return f"StyleOptions({', '.join(parts)})"

    def as_dict(self) -> dict[str, Any]:
        """Return a dict of SVG-ready attribute key/value pairs."""
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


#: Grainline arrow style — grey dashed with arrowheads at both ends.
STYLE_GRAINLINE = StyleOptions(
    stroke_color="grey",
    stroke_width=DEFAULT_STROKE_WIDTH_GRAIN,
    marker_start=Marker.ARROW,
    marker_end=Marker.ARROW,
    dash_array=[3, 2],
)

#: Fold-line style — grey dashed, no notch.
STYLE_FOLD = StyleOptions(
    stroke_color="grey",
    dash_array=[10.0, 2.0],
    no_notch=True,
)

#: Hem-line style — dashed with 2.5 cm default seam allowance, no notch.
STYLE_HEM = StyleOptions(
    stroke_color="black",
    seam_allowance=25.0,  # 2.5 cm
    dash_array=[10.0, 2.0],
    no_notch=True,
)

#: Waistband style — solid with stop markers at both ends and 3 cm SA.
STYLE_WAISTBAND = StyleOptions(
    stroke_color="black",
    marker_start=Marker.STOP,
    marker_end=Marker.STOP,
    seam_allowance=30.0,  # 3 cm
)

#: Cutting-line style — solid with scissor marker at the end.
STYLE_CUT = StyleOptions(
    stroke_color="black",
    marker_end=Marker.SCISSOR,
)

#: Stitching-line style — dashed.
STYLE_STITCH = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[5.0, 2.0],
)

#: Stitching-line style with bevel corner join for direction changes.
STYLE_STITCH_BEVEL = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[5.0, 2.0],
    corner_join="bevel",
)

#: Center-front / center-back line — long-dash–short-dash, no notch.
STYLE_CENTER_LINE = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[10.0, 2.0, 2.0, 2.0],
    no_notch=True,
    corner_join="bevel",
)

#: Seam-allowance outline style — thin solid, no markers.
STYLE_SEAM_ALLOWANCE = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
)

#: Debug highlight style — thick red semi-transparent line for visual verification.
STYLE_DEBUG_RED = StyleOptions(
    stroke_color="red",
    stroke_width=1.5,
    opacity=0.7,
)

#: Construction-grid line style — light grey dashed.
STYLE_CONSTRUCTION_GRID = StyleOptions(
    stroke_color="lightgrey",
    stroke_width=0.8,
    opacity=0.8,
    dash_array=[3.0, 2.0],
)

#: Dart stitching-line style — dashed with zero seam allowance.
STYLE_DART_STITCH = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[5.0, 2.0],
    seam_allowance=0.0,
)

#: Dart fold / crease-line style — long-dash–dot, no notch.
STYLE_DART_FOLD = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    dash_array=[10.0, 2.0, 2.0, 2.0],
    no_notch=True,
)

#: Precision-point marker style — thin grey stroke.
STYLE_PRECISION_POINT = StyleOptions(
    stroke_color="grey",
    stroke_width=DEFAULT_STROKE_WIDTH_GRAIN,
)

#: Sleeve slit — solid black line with a stop marker at the top (closed end).
STYLE_SLIT = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    marker_end=Marker.STOP,
)

#: Pleat fold line — solid black, no seam allowance, no notch.
STYLE_PLEAT_FOLD = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    seam_allowance=0.0,
    no_notch=True,
)

#: Pleat folding-direction arrow — solid black with arrowhead at end, no SA.
STYLE_PLEAT_ARROW = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    marker_end=Marker.ARROW,
    seam_allowance=0.0,
    no_notch=True,
)

#: Button mark — outlined circle, no seam allowance, no notch.
STYLE_BUTTON = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    fill_color="none",
    seam_allowance=0.0,
    no_notch=True,
)

#: Buttonhole mark — solid thin line, no seam allowance, no notch.
STYLE_BUTTONHOLE = StyleOptions(
    stroke_color="black",
    stroke_width=DEFAULT_STROKE_WIDTH,
    seam_allowance=0.0,
    no_notch=True,
)
