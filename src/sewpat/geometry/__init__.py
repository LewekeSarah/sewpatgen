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
    point_in_sector,
    project_onto_edge,
    round_corner,
    seam_length,
    with_endpoints,
)
from ._bezier import (
    CubicBezier,
    fit_cubic_bezier,
    fit_cubic_bezier_free,
    split_bezier_seam_fn,
)
from ._bezier_offset import (
    bezier_offset,
    bezier_offset_adaptive,
    bezier_offset_error,
)
from ._dart import (
    Dart,
    DartType,
    dart_from_edge_at_legs,
    dart_from_edge_at_point,
    dart_from_edge_at_t,
    dart_from_edge_free_tip,
    dart_from_tip_and_legs,
    dart_from_tip_center_width,
)
from ._outline import (
    nudge_point_inside,
    outline_area_cm2,
    outline_bounding_box,
    outline_centroid,
    outline_contains_point,
    outline_width_at_y,
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
    "fit_cubic_bezier",
    "fit_cubic_bezier_free",
    "split_bezier_seam_fn",
    "bezier_offset",
    "bezier_offset_error",
    "bezier_offset_adaptive",
    # Dart
    "DartType",
    "Dart",
    "dart_from_tip_center_width",
    "dart_from_edge_at_legs",
    "dart_from_tip_and_legs",
    "dart_from_edge_at_t",
    "dart_from_edge_at_point",
    "dart_from_edge_free_tip",
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
    "outline_centroid",
    "outline_area_cm2",
    "outline_bounding_box",
    "outline_width_at_y",
    "outline_contains_point",
    "nudge_point_inside",
    "seam_length",
    "project_onto_edge",
    "offset_adaptive",
    "point_in_sector",
]
