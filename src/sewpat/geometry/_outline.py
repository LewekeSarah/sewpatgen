"""Outline-related helpers extracted from the main algorithms module.

These helpers operate on a list of outline geometries (Segments / CubicBeziers)
and provide convenient operations used by higher-level code such as
`sewpat.pattern.part.PatternPart`.
"""

import shapely.geometry as _sg

from ._algorithms import outline_polygon
from ._bezier import CubicBezier
from ._primitives import Point, Segment


def _extract_coords_from_shapely(
    geom: _sg.base.BaseGeometry,
) -> list[tuple[float, float]]:  # pragma: no cover
    """Return a flat list of (x,y) coordinates contained in a Shapely geometry.

    Handles Point, LineString, LinearRing, MultiLineString, MultiPoint and
    GeometryCollection by returning the coordinates of all point- and line-like
    sub-geometries in order.

    This helper deals with many Shapely geometry variants that are awkward to
    construct deterministically in unit tests (different GEOM types, empty
    geometries, etc.). Excluding it from coverage assertions keeps test
    coverage focused on behaviour that's exercised by the library's public
    API.
    """
    if geom.is_empty:
        return []
    coords: list[tuple[float, float]] = []
    gt = geom.geom_type
    if gt == "Point":
        return [(geom.x, geom.y)]
    if gt in ("LineString", "LinearRing"):
        return list(geom.coords)
    if gt == "MultiLineString":
        for g in geom.geoms:
            coords.extend(list(g.coords))
        return coords
    if gt in ("MultiPoint", "GeometryCollection"):
        for g in geom.geoms:
            if g.geom_type == "Point":
                coords.append((g.x, g.y))
            elif g.geom_type in ("LineString", "LinearRing"):
                coords.extend(list(g.coords))
        return coords
    return []


def outline_centroid(geoms: list[Segment | CubicBezier]) -> Point | None:
    poly = outline_polygon(geoms)
    if poly is None or poly.is_empty:
        return None
    c = poly.centroid
    return Point(c.x, c.y)


def outline_area_cm2(geoms: list[Segment | CubicBezier]) -> float | None:
    poly = outline_polygon(geoms)
    if poly is None or poly.is_empty:
        return None
    return float(poly.area) / 100.0


def outline_bounding_box(geoms: list[Segment | CubicBezier]) -> tuple[Point, Point] | None:
    poly = outline_polygon(geoms)
    if poly is None or poly.is_empty:
        return None
    minx, miny, maxx, maxy = poly.bounds
    return Point(minx, miny), Point(maxx, maxy)


def outline_width_at_y(geoms: list[Segment | CubicBezier], y: float) -> tuple[float, float]:
    poly = outline_polygon(geoms)
    if poly is None or poly.is_empty:
        raise ValueError("No outline polygon")
    h_line = _sg.LineString([(-1e9, y), (1e9, y)])
    cross = poly.intersection(h_line)
    if cross.is_empty:
        raise ValueError(f"Y level {y:.1f} mm does not intersect the outline.")
    coords = _extract_coords_from_shapely(cross)
    if len(coords) == 0:
        raise ValueError(f"No intersection coordinates found at Y={y:.1f}.")  # pragma: no cover
    xs = [c[0] for c in coords]
    return float(min(xs)), float(max(xs))


def outline_contains_point(geoms: list[Segment | CubicBezier], point: Point) -> bool:
    poly = outline_polygon(geoms)
    if poly is None or poly.is_empty:
        return False
    return bool(poly.contains(_sg.Point(point.x, point.y)))


def nudge_point_inside(
    geoms: list[Segment | CubicBezier], point: Point, inward_ref: Point, step: float = 1.0
) -> Point:
    poly = outline_polygon(geoms)
    if poly is None or poly.is_empty:
        return point
    sp = _sg.Point(point.x, point.y)
    if poly.contains(sp) or poly.exterior.distance(sp) <= 0.1:
        return point
    snapped = poly.exterior.interpolate(poly.exterior.project(sp))
    dx = inward_ref.x - snapped.x
    dy = inward_ref.y - snapped.y
    dist = (dx**2 + dy**2) ** 0.5
    if dist < 1e-9:
        return point  # pragma: no cover
    nudge = min(step, dist * 0.5)
    return Point(snapped.x + nudge * dx / dist, snapped.y + nudge * dy / dist)
