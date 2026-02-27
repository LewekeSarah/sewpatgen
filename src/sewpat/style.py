"""
Style options for rendering sewing pattern elements.

This module is intentionally kept separate from both ``geometry.py`` and
``render.py`` so that geometry objects can reference ``StyleOptions`` without
creating a circular import.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Stroke width constants — single source of truth for the whole library.
# Override DEFAULT_STROKE_WIDTH here to change all pattern lines at once.
# ---------------------------------------------------------------------------
DEFAULT_STROKE_WIDTH: float = 0.5
DEFAULT_STROKE_WIDTH_GRAIN: float = 0.2


class StyleOptions:
    """Style options for rendering pattern elements."""

    def __init__(
        self,
        stroke_color: str = "black",
        stroke_width: float = DEFAULT_STROKE_WIDTH,
        fill_color: str = "none",
        dash_array: list[float] | None = None,
        opacity: float = 1.0,
        arrow_start: bool = False,
    ) -> None:
        """Initialize style options.

        Args:
            stroke_color: Color of the stroke (outline).
            stroke_width: Width of the stroke in SVG units.
            fill_color: Fill color for closed shapes.
            dash_array: List of values defining the dash pattern, or None for a solid line.
            opacity: Opacity value between 0.0 (transparent) and 1.0 (opaque).
            arrow_start: Whether to draw an arrowhead at the start of the element (p1).
        """
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.dash_array = dash_array
        self.opacity = opacity
        self.arrow_start = arrow_start

    def as_dict(self) -> dict[str, Any]:
        """Convert style options to a dictionary.

        Returns:
            Dictionary with style attributes.
        """
        style_dict: dict[str, Any] = {
            "stroke": self.stroke_color,
            "stroke-width": self.stroke_width,
            "fill": self.fill_color,
            "opacity": self.opacity,
            "arrow-start": self.arrow_start,
        }
        if self.dash_array:
            style_dict["stroke-dasharray"] = ",".join(map(str, self.dash_array))
        return style_dict

