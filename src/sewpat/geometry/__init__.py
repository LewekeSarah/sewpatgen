"""2D geometry primitives for sewing pattern generation.

This package re-exports everything from the sub-modules so that all existing
imports like ``from sewpat.geometry import Point`` continue to work unchanged.
"""

from ._algorithms import (
    GEOMETRIC_TYPE,
    buffer_chain,
    build_chain,
    edge_tangent,
    geom_to_shapely,
    intersect,
    miter_corner,
    offset_adaptive,
    outline_polygon,
    project_onto_edge,
    round_corner,
    seam_length,
    with_endpoints,
)
from ._bezier import (
    CubicBezier,
    _bezier_shapely,  # noqa: F401 — imported by tests via sewpat.geometry
    _true_offset_ls,  # noqa: F401 — imported by tests via sewpat.geometry
)
from ._bezier_offset import (
    bezier_offset,
    bezier_offset_adaptive,
    bezier_offset_error,
)
from ._dart import (
    Dart,
    DartType,
)
from ._primitives import (
    Circle,
    InfoBox,
    Line,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
)

__all__ = [
    # Primitives
    "Point",
    "Segment",
    "Ray",
    "Line",
    "Rect",
    "Triangle",
    "Circle",
    "InfoBox",
    # Bezier
    "CubicBezier",
    "bezier_offset",
    "bezier_offset_error",
    "bezier_offset_adaptive",
    # Dart
    "DartType",
    "Dart",
    # Algorithms
    "GEOMETRIC_TYPE",
    "intersect",
    "geom_to_shapely",
    "edge_tangent",
    "with_endpoints",
    "build_chain",
    "miter_corner",
    "round_corner",
    "buffer_chain",
    "outline_polygon",
    "seam_length",
    "project_onto_edge",
    "offset_adaptive",
]
