"""Sewpat package - A Python library for generating sewing patterns.

This package provides geometric primitives for CAD operations,
designed for generating and manipulating vector patterns.

Modules:
    geometry: Contains geometric primitives like Point, Line, Ray, Circle,
              Segment, Rect, and CubicBezier.
    style:    Contains StyleOptions and stroke-width constants.
    part:     Contains PatternPart.
    render:   Contains the SVG export function.
"""

from .geometry import (
    Point,
    Segment,
    Ray,
    Circle,
    Line,
    Rect,
    Triangle,
    CubicBezier,
    intersect,
    segment_to_intersection,
)
from .units import MM, CM, INCH
from .part import PatternPart, PatternElement, Pattern
from .style import (
    StyleOptions,
    Marker,
    DEFAULT_STROKE_WIDTH,
    DEFAULT_STROKE_WIDTH_GRAIN,
    STYLE_GRAINLINE,
    STYLE_FOLD,
    STYLE_HEM,
    STYLE_CUT,
    STYLE_STITCH,
    STYLE_CENTER_LINE,
)

__all__ = [
    # Geometry primitives
    "Point",
    "Segment",
    "Ray",
    "Circle",
    "Line",
    "Rect",
    "Triangle",
    "CubicBezier",
    # Geometry helpers
    "intersect",
    "segment_to_intersection",
    # Units
    "MM",
    "CM",
    "INCH",
    # Pattern
    "PatternPart",
    "PatternElement",
    "Pattern",
    # Style
    "StyleOptions",
    "Marker",
    "DEFAULT_STROKE_WIDTH",
    "DEFAULT_STROKE_WIDTH_GRAIN",
    "STYLE_GRAINLINE",
    "STYLE_FOLD",
    "STYLE_HEM",
    "STYLE_CUT",
    "STYLE_STITCH",
    "STYLE_CENTER_LINE",
]
