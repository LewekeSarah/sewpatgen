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
    CubicBezier,
    intersect,
    segment_to_intersection,
    MM,
    CM,
)
from .part import PatternPart
from .style import StyleOptions, DEFAULT_STROKE_WIDTH, DEFAULT_STROKE_WIDTH_GRAIN

__all__ = [
    # Geometry primitives
    "Point",
    "Segment",
    "Ray",
    "Circle",
    "Line",
    "Rect",
    "CubicBezier",
    # Geometry helpers
    "intersect",
    "segment_to_intersection",
    # Units
    "MM",
    "CM",
    # Pattern
    "PatternPart",
    # Style
    "StyleOptions",
    "DEFAULT_STROKE_WIDTH",
    "DEFAULT_STROKE_WIDTH_GRAIN",
]
