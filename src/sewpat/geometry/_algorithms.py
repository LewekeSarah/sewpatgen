"""Geometry algorithms for sewing-pattern construction.

Public API
----------
intersect          -- intersection points between any two supported geometry types
build_chain        -- sort a list of segments/curves into a single connected chain
buffer_chain       -- outward-buffer a closed chain using Shapely
outline_polygon    -- build a Shapely Polygon from a mixed segment/Bézier list
offset_adaptive    -- per-piece adaptive offset (exact for Segment, split for Bézier)
edge_tangent       -- unit tangent of a segment or Bézier at its start or end
seam_length        -- total arc length in mm of Segment/Bézier/Circle/Rect/Triangle
with_endpoints     -- copy a segment or Bézier with new start/end points
miter_corner       -- miter-join point between two consecutive edges
round_corner       -- G1-continuous cubic Bézier arc at a convex corner
project_onto_edge  -- project a point onto a linear or Bézier edge

Notes:
-----
* All coordinates and distances are in **millimetres** unless stated otherwise.
* Linear geometry (Segment, Ray, Line) and circle intersections are computed
  via the Shapely/GEOS backend.
* Bézier–Bézier intersections use Bézier-clipping (svgpathtools).
* Bézier–linear and Bézier–circle intersections discretise the curve and
  delegate to Shapely.
"""

import math

import numpy as np
import shapely.geometry as _sg
import shapely.ops as _so

from ._bezier import CubicBezier, _bezier_closest_t, _bezier_shapely, _intersect_bezier_bezier
from ._primitives import (
    Circle,
    InfoBox,
    Line,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
    _LinearGeom,
)

type GEOMETRIC_TYPE = (
    Point | Line | Ray | Circle | Segment | Rect | Triangle | InfoBox | CubicBezier
)


def _intersect_linear_linear(
    a: _LinearGeom,
    b: _LinearGeom,
    check1: bool,
    check2: bool,
) -> list[Point]:
    """Find the intersection point between two linear objects using Shapely.

    Args:
        a: First linear geometry (Segment, Ray, or Line).
        b: Second linear geometry (Segment, Ray, or Line).
        check1: If ``True``, verify that the computed point lies within ``a``
            (required for Segments, which have finite extent).
        check2: If ``True``, verify that the computed point lies within ``b``.

    Returns:
        A list containing the single intersection :class:`Point`, or an empty
        list when the objects are parallel, coincident, or the intersection
        falls outside the bounded extent of a Segment.
    """
    result = geom_to_shapely(a).intersection(geom_to_shapely(b))
    if result.is_empty or result.geom_type != "Point":
        return []
    pt = Point(result.x, result.y)
    if (check1 and not a.contains_point(pt)) or (
        check2 and not b.contains_point(pt)
    ):  # pragma: no cover
        return []
    return [pt]


def geom_to_shapely(obj: _LinearGeom | CubicBezier, far: float = 1e9) -> _sg.LineString:
    """Convert any supported geometry to a Shapely LineString.

    Args:
        obj: A linear geometry (:class:`Segment`, :class:`Ray`, :class:`Line`)
            or :class:`CubicBezier` to convert.
        far: Half-length in mm used to extend infinite objects (Ray, Line) into
            a finite Shapely LineString.  Defaults to ``1e9`` mm, which is
            effectively infinite for pattern-scale geometry.

    Returns:
        A :class:`shapely.geometry.LineString` representation of *obj*.

    Note:
        A :class:`CubicBezier` is converted to a polyline approximation via
        :func:`._bezier._bezier_shapely`; it is *not* stored as an exact curve.
        Ray and Line objects are clipped to ``[-far, +far]`` along their
        direction vector.
    """
    if isinstance(obj, CubicBezier):
        return _bezier_shapely(obj)
    if isinstance(obj, Segment):
        return _sg.LineString([(obj.start.x, obj.start.y), (obj.end.x, obj.end.y)])
    if isinstance(obj, Ray):
        end = obj.origin.coords + far * obj.unit_direction
        return _sg.LineString([(obj.origin.x, obj.origin.y), (end[0], end[1])])
    # Line — only remaining concrete _LinearGeom subtype
    if isinstance(obj, Line):
        start = obj.point.coords - far * obj.unit_direction
        end = obj.point.coords + far * obj.unit_direction
        return _sg.LineString([(start[0], start[1]), (end[0], end[1])])
    raise TypeError(f"geom_to_shapely: unsupported type {type(obj)}")


def _shapely_to_points(result: _sg.base.BaseGeometry) -> list[Point]:
    """Extract a list of Points from a Shapely intersection result.

    Args:
        result: A Shapely geometry returned by an ``intersection`` call.  May
            be any geometry type; only ``Point`` geometries are extracted.

    Returns:
        A list of :class:`Point` objects.  Returns an empty list when *result*
        is empty or contains no point-like sub-geometries (e.g. when two lines
        overlap and produce a ``LineString``).

    Note:
        Overlapping collinear objects produce a ``LineString`` intersection in
        Shapely.  Such cases are intentionally ignored and an empty list is
        returned, because the caller expects discrete crossing points.
    """
    if result.is_empty:
        return []
    if result.geom_type == "Point":
        return [Point(result.x, result.y)]
    if result.geom_type in ("MultiPoint", "GeometryCollection"):
        return [Point(g.x, g.y) for g in result.geoms if g.geom_type == "Point"]
    return []


def intersect(a: GEOMETRIC_TYPE, b: GEOMETRIC_TYPE) -> list[Point]:
    """Find intersections between two geometric objects.

    Linear objects (Segment, Ray, Line) and circles are handled via Shapely's
    GEOS backend.  Bézier–Bézier intersections use svgpathtools (Bézier-clipping).
    Bézier–linear and Bézier–circle intersections discretise the curve and use
    Shapely.

    Args:
        a: First geometric object.  Must be one of :data:`GEOMETRIC_TYPE`.
        b: Second geometric object.  Must be one of :data:`GEOMETRIC_TYPE`.

    Returns:
        A list of :class:`Point` objects at every intersection.  Returns an
        empty list when there are no intersections or the objects are parallel /
        coincident.

    Raises:
        TypeError: If the combination of types ``(a, b)`` is not supported.

    Note:
        * Accuracy differs by backend: GEOS (linear/circle) is exact; Bézier
          intersections are approximated via polyline discretisation.
        * The order of points in the returned list is not guaranteed.

    Example:
        >>> seg = Segment(Point(0, 0), Point(10, 0))
        >>> ray = Ray(Point(5, -5), np.array([0.0, 1.0]))
        >>> intersect(seg, ray)
        [Point(5.0, 0.0)]
    """
    if isinstance(a, _LinearGeom) and isinstance(b, _LinearGeom):
        return _intersect_linear_linear(a, b, isinstance(a, Segment), isinstance(b, Segment))

    if isinstance(a, _LinearGeom) and isinstance(b, Circle):
        circle_shape = _sg.Point(b.center.x, b.center.y).buffer(b.radius)
        result = geom_to_shapely(a).intersection(circle_shape.exterior)
        return _shapely_to_points(result)

    if isinstance(a, Circle) and isinstance(b, _LinearGeom):
        return intersect(b, a)

    if isinstance(a, Circle) and isinstance(b, Circle):
        return a._intersect_with_circle(b)

    if isinstance(a, CubicBezier) and isinstance(b, CubicBezier):
        return _intersect_bezier_bezier(a, b)

    if isinstance(a, CubicBezier) and isinstance(b, _LinearGeom):
        result = _bezier_shapely(a).intersection(geom_to_shapely(b))
        return _shapely_to_points(result)

    if isinstance(a, _LinearGeom) and isinstance(b, CubicBezier):
        return intersect(b, a)

    if isinstance(a, CubicBezier) and isinstance(b, Circle):
        circle_shape = _sg.Point(b.center.x, b.center.y).buffer(b.radius)
        result = _bezier_shapely(a).intersection(circle_shape.exterior)
        return _shapely_to_points(result)

    if isinstance(a, Circle) and isinstance(b, CubicBezier):
        return intersect(b, a)

    raise TypeError(f"Intersection not implemented for {type(a)} and {type(b)}")


_CHAIN_SNAP = 0.5  # mm — endpoint-matching tolerance


def edge_tangent(g: _LinearGeom | CubicBezier, at_end: bool) -> np.ndarray:
    """Return the unit tangent of *g* in the direction of travel.

    Args:
        g: A linear geometry or :class:`CubicBezier` to evaluate.
        at_end: If ``True``, return the tangent at the end of *g*; otherwise
            return the tangent at the start.

    Returns:
        A unit-length ``numpy`` array of shape ``(2,)`` pointing in the
        direction of travel.

    Note:
        For a :class:`CubicBezier` with a cusp (zero-length tangent), the raw
        (un-normalised) derivative is returned as a fallback to avoid division
        by zero.  For linear geometry the tangent is constant along the whole
        edge and *at_end* has no effect.
    """
    if isinstance(g, CubicBezier):
        d = g.tangent_at_t(1.0 if at_end else 0.0)
        norm = float(np.linalg.norm(d))
        return np.asarray(d / norm) if norm > 1e-12 else np.asarray(d)
    return g.unit_direction


def with_endpoints(
    g: Segment | CubicBezier, new_start: Point, new_end: Point
) -> Segment | CubicBezier:
    """Return a copy of *g* with replaced start and end points.

    Args:
        g: The original geometry to copy.
        new_start: New start point to use in place of ``g.start``.
        new_end: New end point to use in place of ``g.end``.

    Returns:
        A new :class:`Segment` or :class:`CubicBezier` with the updated
        endpoints.  All other attributes (e.g. ``name``) are preserved.

    Note:
        For a :class:`CubicBezier` only the anchor points ``p0`` and ``p3``
        are replaced; the inner control points ``p1`` and ``p2`` are copied
        unchanged, so the curve shape may change if the new endpoints differ
        significantly from the originals.
    """
    if isinstance(g, Segment):
        return Segment(new_start, new_end, name=g.name)
    return CubicBezier(new_start, g.p1, g.p2, new_end, name=g.name)


def _reverse_geom(g: Segment | CubicBezier) -> Segment | CubicBezier:
    """Return a copy of *g* with its direction reversed."""
    if isinstance(g, Segment):
        return Segment(g.p2, g.p1, name=g.name)
    return CubicBezier(g.p3, g.p2, g.p1, g.p0, name=g.name)


def build_chain(
    geoms: list[Segment | CubicBezier],
) -> list[Segment | CubicBezier]:
    """Sort *geoms* into a single connected chain, reversing pieces as needed.

    Iteratively matches the tail of the chain-so-far to the nearest unused
    segment, or the head when growing in the other direction.  Segments are
    reversed where necessary so that all pieces flow head-to-tail.

    Args:
        geoms: A non-empty list of :class:`Segment` and/or :class:`CubicBezier`
            objects to assemble.  Order does not matter.

    Returns:
        The same elements reordered (and possibly reversed) into a connected
        chain.  If one or more pieces cannot be attached (i.e. no endpoint
        is within :data:`_CHAIN_SNAP` mm of the current head or tail), the
        remaining pieces are appended to the end of the chain unchanged.

    Raises:
        IndexError: If *geoms* is empty.

    Note:
        * The endpoint-matching tolerance is :data:`_CHAIN_SNAP` (``0.5`` mm).
          Gaps larger than this will leave disconnected pieces appended at the
          end of the returned list.
        * The algorithm is O(n²) in the number of pieces; it is intended for
          pattern-scale geometry (typically < 100 pieces).

    Example:
        >>> s1 = Segment(Point(0, 0), Point(5, 0))
        >>> s2 = Segment(Point(10, 0), Point(5, 0))  # reversed relative to s1
        >>> build_chain([s1, s2])
        [Segment(Point(0,0), Point(5,0)), Segment(Point(5,0), Point(10,0))]
    """
    chain: list[Segment | CubicBezier] = [geoms[0]]
    remaining: list[Segment | CubicBezier] = list(geoms[1:])

    changed = True
    while remaining and changed:
        changed = False
        tail = chain[-1].end
        head = chain[0].start

        for i, g in enumerate(remaining):
            gs, ge = g.start, g.end

            if tail.distance_to(gs) < _CHAIN_SNAP:
                chain.append(remaining.pop(i))
                changed = True
                break
            if tail.distance_to(ge) < _CHAIN_SNAP:
                chain.append(_reverse_geom(remaining.pop(i)))
                changed = True
                break

            if head.distance_to(ge) < _CHAIN_SNAP:
                chain.insert(0, remaining.pop(i))
                changed = True
                break
            if head.distance_to(gs) < _CHAIN_SNAP:
                chain.insert(0, _reverse_geom(remaining.pop(i)))
                changed = True
                break

    if remaining:
        chain.extend(remaining)
    return chain


def miter_corner(
    ga: Segment | CubicBezier,
    gb: Segment | CubicBezier,
    sa_distance: float,
    miter_limit: float = 4.0,
    check_reflex: bool = True,
) -> Point:
    """Return the miter-join corner between the end of *ga* and the start of *gb*.

    Computes the point where the offset lines along *ga* and *gb* would meet
    if extended as infinite lines.  Falls back to the bevel midpoint when
    the corner is reflex, when lines are parallel, or when the miter spike
    would be excessively long.

    Args:
        ga: The incoming edge; the miter is anchored at ``ga.end``.
        gb: The outgoing edge; the miter is anchored at ``gb.start``.
        sa_distance: Seam-allowance width in mm.  Used to evaluate whether the
            miter spike exceeds *miter_limit*.  Pass ``0.0`` to disable the
            length check.
        miter_limit: Maximum ratio of miter-spike length to *sa_distance*
            before falling back to a bevel.  Defaults to ``4.0`` (matches
            SVG/CSS behaviour).
        check_reflex: If ``True`` (default), reflex corners (where the
            intersection point lies *behind* the incoming edge) are replaced
            with the bevel midpoint.

    Returns:
        The miter-join :class:`Point`.  Returns the midpoint between
        ``ga.end`` and ``gb.start`` (a simple bevel) in any of these cases:

        * The tangent lines are parallel (no intersection).
        * The corner is reflex and *check_reflex* is ``True``.
        * The miter spike length exceeds ``miter_limit × sa_distance``.

    Note:
        Tangents are evaluated at the exact endpoints via :func:`edge_tangent`,
        so the result is meaningful even when *ga* or *gb* is a curved Bézier.
    """
    end_a = ga.end
    start_b = gb.start
    ta = edge_tangent(ga, at_end=True)
    tb = edge_tangent(gb, at_end=False)

    bevel_mid = (end_a + start_b) * 0.5

    pts = intersect(Line(end_a, ta), Line(start_b, tb))
    if not pts:
        return bevel_mid
    pt = pts[0]

    if check_reflex and float(np.dot(pt.coords - end_a.coords, ta)) < 0.0:
        return bevel_mid

    if sa_distance > 1e-9 and pt.distance_to(end_a) > miter_limit * sa_distance:
        return bevel_mid
    return pt


def round_corner(
    ga: Segment | CubicBezier,
    gb: Segment | CubicBezier,
) -> CubicBezier | Point:
    """Return a cubic Bézier arc for a round join at a convex corner.

    Constructs a G1-continuous cubic Bézier that connects ``ga.end`` to
    ``gb.start`` while matching the outgoing tangent of *ga* and the incoming
    tangent of *gb*.  The arc approximates a true circular arc using the
    standard ``(4/3) tan(θ/4)`` handle-length formula.

    Args:
        ga: The incoming edge; the arc starts at ``ga.end``.
        gb: The outgoing edge; the arc ends at ``gb.start``.

    Returns:
        A :class:`CubicBezier` arc joining the two edges with G1 continuity,
        or the bevel midpoint :class:`Point` between ``ga.end`` and ``gb.start``
        as a fallback in any of these cases:

        * The corner angle is nearly zero or nearly 180° (flat or U-turn).
        * The tangent lines do not intersect (parallel edges).
        * The corner is concave (centre lies on the wrong side).
        * The two endpoint distances to the centre differ by more than 1 %
          (degenerate geometry).

    Note:
        * The resulting arc is G1-continuous (tangent-matched) but not
          necessarily C2-continuous at the joins.
        * Tangents are evaluated at the exact endpoints via :func:`edge_tangent`,
          so the function works correctly when *ga* or *gb* is a :class:`CubicBezier`.
        * The handle length uses the ``k = (4/3) tan(θ/4)`` approximation,
          which gives a maximum radial error of < 0.027 % for a full circle.
    """
    end_a = ga.end
    start_b = gb.start
    bevel_mid = (end_a + start_b) * 0.5

    ta = edge_tangent(ga, at_end=True)
    tb = edge_tangent(gb, at_end=False)

    cross = float(ta[0] * tb[1] - ta[1] * tb[0])
    dot_ = float(ta[0] * tb[0] + ta[1] * tb[1])
    angle = math.atan2(cross, dot_)

    if angle <= 1e-6 or angle > math.pi - 1e-6:
        return bevel_mid

    na = np.array([ta[1], -ta[0]])
    centre_pts = intersect(Line(end_a, ta), Line(start_b, tb))
    if not centre_pts:  # pragma: no cover
        return bevel_mid
    centre_pt = centre_pts[0]

    if float(np.dot(centre_pt.coords - end_a.coords, na)) < 0.0:
        return bevel_mid

    r = centre_pt.distance_to(end_a)
    if r < 1e-9:
        return bevel_mid

    r2 = centre_pt.distance_to(start_b)
    if abs(r2 - r) > r * 0.01:
        return bevel_mid

    k = (4.0 / 3.0) * math.tan(angle / 4.0)
    handle = k * r

    cp1 = end_a + Point(*(handle * ta))
    cp2 = start_b - Point(*(handle * tb))

    return CubicBezier(end_a, cp1, cp2, start_b)


def buffer_chain(
    geoms: list[Segment | CubicBezier],
    distance: float,
    join_style: int = 2,
    mitre_limit: float = 4.0,
) -> list[tuple[float, float]]:
    """Buffer a connected chain of Segments outward by *distance* using Shapely.

    Constructs a polygon from the start-points of *geoms*, expands it outward
    by *distance* using Shapely's ``buffer`` operation, and returns the
    exterior ring coordinates of the result.

    Args:
        geoms: An ordered, closed chain of :class:`Segment` and/or
            :class:`CubicBezier` objects forming the outline to buffer.
        distance: Buffer distance in mm.  Positive values expand outward;
            negative values shrink the polygon.
        join_style: Shapely join style for corners.  Use ``1`` for round,
            ``2`` for mitre (default), or ``3`` for bevel joins.
        mitre_limit: Maximum mitre ratio before Shapely falls back to a bevel
            join.  Defaults to ``4.0``.  Only relevant when *join_style* is
            ``2`` (mitre).

    Returns:
        A list of ``(x, y)`` coordinate tuples representing the exterior ring
        of the buffered polygon.  The ring is closed (first point == last point).

    Note:
        * Only the start-points of *geoms* are used to build the initial
          polygon; Bézier curves are **not** discretised here, so the result
          is a straight-sided approximation of the true outline.
        * If the resulting polygon is invalid (e.g. self-intersecting due to a
          concave outline), it is repaired with ``poly.buffer(0)`` before
          applying the offset.
    """
    ring_coords = [(g.start.x, g.start.y) for g in geoms]
    poly = _sg.Polygon(ring_coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return list(
        poly.buffer(distance, join_style=join_style, mitre_limit=mitre_limit).exterior.coords
    )


def outline_polygon(
    geoms: list[Segment | CubicBezier],
) -> _sg.Polygon | None:
    """Build a Shapely Polygon from a list of Segments and CubicBeziers.

    Chains *geoms* into a connected order, discretises each piece into a
    polyline via :func:`geom_to_shapely`, and assembles the result into a
    closed :class:`shapely.geometry.Polygon`.

    Args:
        geoms: An unordered or ordered list of :class:`Segment` and/or
            :class:`CubicBezier` objects that collectively form a closed
            outline.

    Returns:
        A :class:`shapely.geometry.Polygon` built from the discretised
        outline, or ``None`` if *geoms* is empty or produces fewer than
        three distinct coordinate points.

    Note:
        * :func:`build_chain` is called internally to sort and orient the
          pieces; the input list is not required to be pre-ordered.
        * Bézier curves are approximated as polylines (see
          :func:`geom_to_shapely`), so the polygon boundary is an
          approximation of the true curved outline.
        * The returned polygon is not guaranteed to be valid or simple; call
          ``polygon.buffer(0)`` if downstream Shapely operations require a
          valid geometry.
    """
    if not geoms:
        return None
    ordered = build_chain(geoms)
    coords: list[tuple[float, float]] = []
    for g in ordered:
        coords.extend(list(geom_to_shapely(g).coords)[:-1])
    coords.append((ordered[-1].end.x, ordered[-1].end.y))
    if len(coords) < 3:
        return None
    return _sg.Polygon(coords)


def seam_length(geoms: list[Segment | CubicBezier | Circle | Rect | Triangle]) -> float:
    """Return the total arc length in mm of a list of measurable geometry objects.

    Supported types and what ``length`` means for each:

    * :class:`Segment` — Euclidean distance between endpoints.
    * :class:`CubicBezier` — arc length via numerical integration.
    * :class:`Circle` — full circumference (``2 * π * radius``).
    * :class:`Rect` — full perimeter (``2 * (width + height)``).
    * :class:`Triangle` — full perimeter (sum of the three side lengths).

    Args:
        geoms: A list of measurable geometry objects.  May be empty.

    Returns:
        Total arc length in mm as a :class:`float`.  Returns ``0.0`` for an
        empty list.
    """
    return sum(g.length for g in geoms)


def _normalize_vector(v: np.ndarray) -> np.ndarray:
    """Normalize a vector to unit length, or return a default if near-zero."""
    norm = np.linalg.norm(v)
    return v / norm if norm > 1e-12 else np.array([1.0, 0.0])


def _normal_from_tangent(tangent: np.ndarray) -> np.ndarray:
    """Compute unit normal by rotating tangent 90° counter-clockwise."""
    return np.array([-tangent[1], tangent[0]])


def _bezier_tangent_from_control_points(
    bezier: CubicBezier,
    near_start: bool,
) -> np.ndarray:
    """Compute tangent at Bezier endpoint using control point geometry.

    Uses the direction from/to control points to avoid numerical artifacts
    at curve endpoints where the derivative may be degenerate.
    """
    if near_start:
        # Outgoing direction: p0 → p1 (or p0 → p2 if p0 ≈ p1)
        if bezier.p0.distance_to(bezier.p1) < 0.1:
            direction = bezier.p2.coords - bezier.p0.coords
        else:
            direction = bezier.p1.coords - bezier.p0.coords
        return _normalize_vector(direction)
    # near_start=False: incoming direction at p3
    if bezier.p2.distance_to(bezier.p3) < 0.1:
        direction = bezier.p3.coords - bezier.p1.coords
    else:
        direction = bezier.p3.coords - bezier.p2.coords

    return _normalize_vector(direction)


def _orient_normal_inward(
    normal: np.ndarray,
    notch_pt: Point,
    inward_ref: Point,
) -> np.ndarray:
    """Flip normal if it points away from the inward reference point."""
    to_inward = inward_ref.coords - notch_pt.coords
    if float(np.dot(normal, to_inward)) < 0:
        return -normal
    return normal


def project_onto_edge(
    edge: _LinearGeom | CubicBezier,
    ref: Point,
    inward_ref: Point | None = None,
) -> tuple[Point, np.ndarray, np.ndarray]:
    """Project *ref* onto *edge* and return ``(notch_pt, along, normal)``.

    Finds the closest point on *edge* to *ref*, then returns that point together
    with the edge's unit tangent and unit normal at that location.

    Args:
        edge: The edge to project onto.  May be any linear geometry or a
            :class:`CubicBezier`.
        ref: The reference point to project.
        inward_ref: An optional reference point used to orient the normal
            vector.  When provided, the returned normal is flipped so that it
            points toward *inward_ref* (i.e. into the pattern piece).

    Returns:
        A 3-tuple ``(notch_pt, along, normal)`` where:

        * ``notch_pt`` (:class:`Point`) – the closest point on *edge* to *ref*.
        * ``along`` (:class:`numpy.ndarray`, shape ``(2,)``) – unit tangent of
          *edge* at ``notch_pt``, pointing in the direction of travel.
        * ``normal`` (:class:`numpy.ndarray`, shape ``(2,)``) – unit normal of
          *edge* at ``notch_pt``.  Oriented toward *inward_ref* when that
          argument is supplied.

    Note:
        For a :class:`CubicBezier`, the closest point is found by discretising
        the curve via :func:`geom_to_shapely` and using
        ``shapely.ops.nearest_points``; the exact parameter *t* is then
        recovered with :func:`._bezier._bezier_closest_t`.
    """
    # Handle linear geometry (Segment, Ray, Line)
    if isinstance(edge, _LinearGeom):
        notch_pt = edge.project_point(ref)
        along = edge.unit_direction
        normal = edge.unit_normal

    # Handle CubicBezier
    else:
        # Find closest point on the curve
        _, nearest = _so.nearest_points(_sg.Point(ref.x, ref.y), geom_to_shapely(edge))
        notch_pt = Point(nearest.x, nearest.y)
        t_c = _bezier_closest_t(edge._svg(), complex(nearest.x, nearest.y))

        # Near endpoints: use control-point geometry to avoid numerical issues
        if t_c > 0.95 or t_c < 0.05:
            along = _bezier_tangent_from_control_points(edge, near_start=(t_c < 0.05))
            normal = _normal_from_tangent(along)

        # Interior: use mathematical derivatives
        else:
            tangent = edge.tangent_at_t(t_c)
            along = _normalize_vector(tangent)
            normal = edge.normal_at_t(t_c)

    # Orient normal toward interior if requested
    if inward_ref is not None:
        normal = _orient_normal_inward(normal, notch_pt, inward_ref)

    return notch_pt, along, normal


def offset_adaptive(
    geom: Segment | CubicBezier,
    distance: float,
    center: Point | None = None,
    eps: float = 0.1,
) -> list[Segment | CubicBezier]:
    """Offset *geom* outward by *distance* mm, splitting until Hausdorff error < *eps*.

    For a :class:`Segment` the offset is exact and returns a single element.
    For a :class:`CubicBezier` the curve is recursively split into sub-arcs
    until every piece's offset is within *eps* mm Hausdorff distance of the
    true parallel curve.

    Args:
        geom: The geometry to offset.  Either a :class:`Segment` (exact) or a
            :class:`CubicBezier` (adaptive subdivision).
        distance: Offset distance in mm.  Positive values move the geometry
            outward (away from *center* when supplied); negative values move it
            inward.
        center: Optional interior reference point used to determine the
            outward direction.  When ``None``, the offset direction is
            determined by the geometry's own normal.
        eps: Maximum allowed Hausdorff error in mm for Bézier offsets.
            Defaults to ``0.1`` mm.  Smaller values produce more sub-arcs and
            higher accuracy.  Ignored for :class:`Segment` inputs.

    Returns:
        A list of offset :class:`Segment` and/or :class:`CubicBezier` objects.
        Always contains exactly one element for a :class:`Segment` input; may
        contain multiple elements for a :class:`CubicBezier` after subdivision.
    """
    if isinstance(geom, Segment):
        return [geom.offset(distance, center=center)]
    result: list[Segment | CubicBezier] = list(
        geom.offset_adaptive(distance, center=center, eps=eps)
    )
    return result


def angle_between(a: GEOMETRIC_TYPE, b: GEOMETRIC_TYPE) -> float:
    """Calculate the signed angle between two geometric objects.

    Args:
        a: First geometric object. Must be one of :data:`GEOMETRIC_TYPE`.
        b: Second geometric object. Must be one of :data:`GEOMETRIC_TYPE`.

    Returns:
        The signed angle in degrees between the two objects. The value is
        obtained via ``degrees(atan2(cross, dot))`` and therefore lies in the
        range ``(-180, 180]``. A positive value indicates a counter-clockwise
        rotation from ``a`` to ``b``; a negative value indicates a
        clockwise rotation. Returns ``0.0`` when the objects are parallel.

    Raises:
        TypeError: If the combination of types ``(a, b)`` is not supported.
    """
    if isinstance(a, _LinearGeom) and isinstance(b, _LinearGeom):
        tangent_a = a.unit_direction
        tangent_b = b.unit_direction
        dot_product = float(np.dot(tangent_a, tangent_b))
        cross_product = float(tangent_a[0] * tangent_b[1] - tangent_a[1] * tangent_b[0])
        # np.degrees may return a numpy scalar; wrap in float() to satisfy strict typing
        return float(np.degrees(math.atan2(cross_product, dot_product)))

    raise TypeError(f"Angle calculation not implemented for {type(a)} and {type(b)}")
