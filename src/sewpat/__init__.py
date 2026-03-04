"""Sewpat — a Python library for generating sewing patterns."""

from .element import PatternElement, PrecisionPoint
from .geometry import (
    Circle,
    CubicBezier,
    Dart,
    DartType,
    InfoBox,
    Line,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
    edge_tangent,
    intersect,
    seam_length,
    segment_to_intersection,
)
from .measurements import (
    Allowance,
    BlouseMeasurements,
    ModelConfig,
    TrouserMeasurements,
    make_blouse_measurements,
    make_measurements_trouser,
)
from .pages import DinA0, DinA1, DinA2, DinA4
from .pattern import (
    Block,
    ConstructionGrid,
    ConstructionGridPart,
    DartResult,
    GarmentPart,
    OverlayPart,
    Pattern,
    PatternPart,
)
from .style import (
    DEFAULT_STROKE_WIDTH,
    DEFAULT_STROKE_WIDTH_GRAIN,
    STYLE_CENTER_LINE,
    STYLE_CONSTRUCTION_GRID,
    STYLE_CUT,
    STYLE_DART_FOLD,
    STYLE_DART_STITCH,
    STYLE_DEBUG_RED,
    STYLE_FOLD,
    STYLE_GRAINLINE,
    STYLE_HEM,
    STYLE_PRECISION_POINT,
    STYLE_SEAM_ALLOWANCE,
    STYLE_STITCH,
    STYLE_WAISTBAND,
    Marker,
    StyleOptions,
)
from .units import CM, INCH, MM

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
    "Dart",
    "DartType",
    "InfoBox",
    # Geometry helpers
    "edge_tangent",
    "intersect",
    "segment_to_intersection",
    "seam_length",
    # Units
    "MM",
    "CM",
    "INCH",
    # Pattern element
    "PatternElement",
    "PrecisionPoint",
    # Dart result
    "DartResult",
    # Pattern
    "PatternPart",
    "Pattern",
    "GarmentPart",
    "ConstructionGrid",
    "ConstructionGridPart",
    "Block",
    "OverlayPart",
    # Pages
    "DinA4",
    "DinA2",
    "DinA1",
    "DinA0",
    # Measurements
    "Allowance",
    "BlouseMeasurements",
    "TrouserMeasurements",
    "ModelConfig",
    "make_blouse_measurements",
    "make_measurements_trouser",
    # Style
    "StyleOptions",
    "Marker",
    "DEFAULT_STROKE_WIDTH",
    "DEFAULT_STROKE_WIDTH_GRAIN",
    "STYLE_GRAINLINE",
    "STYLE_FOLD",
    "STYLE_HEM",
    "STYLE_STITCH",
    "STYLE_CUT",
    "STYLE_WAISTBAND",
    "STYLE_CENTER_LINE",
    "STYLE_SEAM_ALLOWANCE",
    "STYLE_CONSTRUCTION_GRID",
    "STYLE_DEBUG_RED",
    "STYLE_DART_STITCH",
    "STYLE_DART_FOLD",
    "STYLE_PRECISION_POINT",
]
