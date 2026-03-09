"""Seam-allowance generation — free functions that operate on a :class:`PatternPart`.

This module owns:

* :func:`add_seam_allowance` — offset the part outline and append SA elements.
* :func:`_project_dart_notches_to_sa` — re-project dart notches onto the SA edge.

Both functions accept the part as their first argument and are wired back into
``PatternPart`` as thin one-liner wrapper methods in :mod:`sewpat.pattern.part`.
"""

import copy
from typing import TYPE_CHECKING, cast

import numpy as np

from ..element import PatternElement
from ..geometry import (
    CubicBezier,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
    buffer_chain,
    build_chain,
    miter_corner,
    project_onto_edge,
    round_corner,
    with_endpoints,
)
from ..geometry import intersect as _intersect_geom
from ..geometry import offset_adaptive as _offset_adaptive
from ..geometry._algorithms import _reverse_geom
from ..style import STYLE_SEAM_ALLOWANCE, StyleOptions

if TYPE_CHECKING:
    from .part import PatternPart

# ---------------------------------------------------------------------------
# Module-level constants and helpers
# ---------------------------------------------------------------------------

#: Shapely join-style codes for each corner-join name.
_CJ: dict[str, int] = {"miter": 2, "round": 1, "bevel": 3}

#: Valid corner-join names — used for input validation in two places.
_VALID_CJ: frozenset[str] = frozenset(_CJ)

#: Maximum distance (mm) between two dart-leg notch base midpoints to consider
#: them a paired double-notch (back-piece convention).
_NOTCH_PAIRING_TOLERANCE: float = 1.0


def _ep_key(g: Segment | CubicBezier) -> frozenset[tuple[float, float]]:
    """Return a frozenset of the two rounded endpoint coordinate pairs.

    Used as a dict key to map original chain geometries to per-element style
    overrides, surviving the endpoint rounding that ``build_chain`` applies.
    """
    s, e = g.start, g.end
    return frozenset([(round(s.x, 6), round(s.y, 6)), (round(e.x, 6), round(e.y, 6))])


def _normalize_vec(v: np.ndarray) -> np.ndarray:
    """Return *v* divided by its L2 norm; return *v* unchanged when near-zero.

    Note:
        Equivalent to the normalization in geometry._algorithms — kept here to
        avoid importing private modules in hot-path code.
    """
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _closest_sa_edge(
    ref: Point,
    sa_geoms: list[Segment | CubicBezier],
) -> Segment | CubicBezier | None:
    """Return the SA edge geometrically closest to *ref*, or ``None``.

    Uses :meth:`Point.distance_to` for consistency with the rest of the API.
    """
    if not sa_geoms:
        return None
    return min(sa_geoms, key=lambda g: ref.distance_to(g.start))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _orient_dart_roof_pairs(
    elems: list[PatternElement],
) -> list[PatternElement]:
    """Ensure dart roof segment pairs form a through-path for :func:`build_chain`.

    Each triangle dart produces two roof segments both pointing *into* the
    peak: ``leg_a → roof`` and ``leg_b → roof``.  This V-shape confuses
    ``build_chain``'s nearest-endpoint sort.

    Detects pairs of ``dart_roof`` elements sharing a peak and ensures the
    first ends at the peak (``leg_a → roof``) while the second starts at the
    peak (``roof → leg_b``), giving ``build_chain`` a clean through-path.

    Args:
        elems: Outline elements in any order.

    Returns:
        New list with dart roof segments re-oriented where needed.
    """
    result = list(elems)

    # Map each rounded endpoint → list of element indices for roof elements.
    roof_endpoint_idx: dict[tuple[float, float], list[int]] = {}
    for idx, e in enumerate(result):
        if e.role != "dart_roof" or not isinstance(e.geometry, (Segment, CubicBezier)):
            continue
        for pt in (e.geometry.start, e.geometry.end):
            key = (round(pt.x, 4), round(pt.y, 4))
            roof_endpoint_idx.setdefault(key, []).append(idx)

    # A shared peak has exactly two roof indices at the same key.
    visited: set[int] = set()
    for key, indices in roof_endpoint_idx.items():
        if len(indices) != 2:
            continue
        i0, i1 = indices
        if i0 in visited or i1 in visited:
            continue
        visited.add(i0)
        visited.add(i1)

        peak = Point(*key)
        g0 = result[i0].geometry
        g1 = result[i1].geometry
        if not isinstance(g0, (Segment, CubicBezier)) or not isinstance(g1, (Segment, CubicBezier)):
            continue  # unexpected geometry type — leave unchanged

        # Orient g0: must END at peak (leg → roof).
        if g0.start.distance_to(peak) < g0.end.distance_to(peak):
            new_e0 = copy.copy(result[i0])
            new_e0.geometry = _reverse_geom(g0)
            result[i0] = new_e0

        # Orient g1: must START at peak (roof → leg).
        if g1.end.distance_to(peak) < g1.start.distance_to(peak):
            new_e1 = copy.copy(result[i1])
            new_e1.geometry = _reverse_geom(g1)
            result[i1] = new_e1

    return result


def _build_elem_overrides(
    seam_elems: list[PatternElement],
) -> tuple[
    dict[frozenset, float],
    dict[frozenset, Point],
    dict[frozenset, str],
]:
    """Extract per-element SA, center, and corner-join overrides from style/attrs.

    Args:
        seam_elems: Outline elements that will be offset.

    Returns:
        Three dicts keyed by :func:`_ep_key`:
        ``elem_sa`` — distance override (mm),
        ``elem_center`` — inward-reference point override,
        ``elem_cj`` — corner-join override string.

    Raises:
        ValueError: If a ``corner_join`` style value is not one of the valid names.
    """
    elem_sa: dict[frozenset, float] = {}
    elem_center: dict[frozenset, Point] = {}
    elem_cj: dict[frozenset, str] = {}

    for e in seam_elems:
        key = _ep_key(cast(Segment | CubicBezier, e.geometry))

        sa_val = getattr(e.style, "seam_allowance", None)
        if sa_val is not None:
            elem_sa[key] = float(sa_val)

        sa_center = getattr(e, "_sa_center", None)
        if isinstance(sa_center, Point):
            elem_center[key] = sa_center

        cj_val = getattr(e.style, "corner_join", None)
        if cj_val is not None:
            if cj_val not in _VALID_CJ:
                raise ValueError(
                    f"StyleOptions.corner_join must be one of {sorted(_VALID_CJ)!r}, "
                    f"got {cj_val!r} on element {e.get_name()!r}"
                )
            elem_cj[key] = cj_val

    return elem_sa, elem_center, elem_cj


def _stitch_corners(
    offset_groups: list[list[Segment | CubicBezier]],
    chain: list[Segment | CubicBezier],
    elem_cj: dict[frozenset, str],
    default_cj: str,
    distance: float,
) -> list[Segment | CubicBezier]:
    """Close gaps between adjacent offset groups with the appropriate corner join.

    Mutates *offset_groups* in-place to adjust endpoints, then returns a flat
    list of all geometries in order, with any round-corner arcs inserted.

    Args:
        offset_groups: Per-edge offset results; modified in-place at boundaries.
        chain: Original ordered chain — used to look up per-element overrides.
        elem_cj: Per-element corner-join overrides keyed by :func:`_ep_key`.
        default_cj: Part-wide corner-join fallback.
        distance: Global SA distance, used by miter/bevel calculations.

    Returns:
        Flat list of ``Segment | CubicBezier`` forming the complete SA outline.
    """
    n = len(offset_groups)
    arc_inserts: list[tuple[int, CubicBezier]] = []  # (group index, arc to insert after)

    for i in range(n):
        j = (i + 1) % n
        ga = offset_groups[i][-1]
        gb = offset_groups[j][0]
        effective_cj = (
            elem_cj.get(_ep_key(chain[i])) or elem_cj.get(_ep_key(chain[j])) or default_cj
        )
        gap = ga.end.distance_to(gb.start)

        # Apply corner join when there is a gap, OR when bevel is explicitly
        # requested (covers zero-gap corners where offsets diverge).
        if gap <= 0.01 and effective_cj != "bevel":
            continue

        if effective_cj == "miter":
            corner = miter_corner(ga, gb, distance)
            offset_groups[i][-1] = with_endpoints(ga, ga.start, corner)
            offset_groups[j][0] = with_endpoints(gb, corner, gb.end)
        elif effective_cj == "round":
            arc = round_corner(ga, gb)
            if isinstance(arc, CubicBezier):
                offset_groups[i][-1] = with_endpoints(ga, ga.start, arc.p0)
                offset_groups[j][0] = with_endpoints(gb, arc.p3, gb.end)
                arc_inserts.append((i, arc))
            else:
                offset_groups[i][-1] = with_endpoints(ga, ga.start, arc)
                offset_groups[j][0] = with_endpoints(gb, arc, gb.end)
        else:  # bevel — clipped miter capped at 3× SA
            corner = miter_corner(ga, gb, distance, miter_limit=3.0, check_reflex=False)
            offset_groups[i][-1] = with_endpoints(ga, ga.start, corner)
            offset_groups[j][0] = with_endpoints(gb, corner, gb.end)

    # Build flat list, inserting round-corner arcs at the correct positions.
    # Collect group-end positions first, then insert arcs back-to-front so
    # earlier indices remain valid.
    flat: list[Segment | CubicBezier] = []
    group_end: list[int] = []
    for group in offset_groups:
        group_end.append(len(flat) + len(group) - 1)
        flat.extend(group)

    for group_i, arc in sorted(arc_inserts, key=lambda x: x[0], reverse=True):
        flat.insert(group_end[group_i] + 1, arc)

    return flat


def _is_double_notch(seam_elem: PatternElement, all_elems: list[PatternElement]) -> bool:
    """Return ``True`` when *seam_elem* is one of a pair of dart-leg notches.

    Two dart-leg notches whose base midpoints are within
    :data:`_NOTCH_PAIRING_TOLERANCE` mm of each other indicate a back-piece
    double-notch pair.  The center notch is never doubled.

    Args:
        seam_elem: The notch element to test.
        all_elems: All elements on the pattern part.
    """
    if seam_elem.role == "dart_center_notch":
        return False
    if not isinstance(seam_elem.geometry, Triangle):
        return False
    base = Point(
        (seam_elem.geometry.p1.x + seam_elem.geometry.p2.x) / 2,
        (seam_elem.geometry.p1.y + seam_elem.geometry.p2.y) / 2,
    )
    return any(
        e is not seam_elem
        and e.role == "dart_notch"
        and not e.is_seam_allowance
        and not e.is_seam_notch
        and isinstance(e.geometry, Triangle)
        and Point(
            (e.geometry.p1.x + e.geometry.p2.x) / 2,
            (e.geometry.p1.y + e.geometry.p2.y) / 2,
        ).distance_to(base)
        < _NOTCH_PAIRING_TOLERANCE
        for e in all_elems
    )


# ---------------------------------------------------------------------------
# SA code paths
# ---------------------------------------------------------------------------


def _add_sa_rect(
    part: PatternPart,
    elem: PatternElement,
    distance: float,
    sa_style: StyleOptions,
) -> list[PatternElement]:
    """Fast path: expand a Rect outline uniformly by *distance*."""
    rect_geom = cast(Rect, elem.geometry)
    new_elem = part.append(
        Rect(
            origin=rect_geom.origin.translate(-distance, -distance),
            width=rect_geom.width + 2 * distance,
            height=rect_geom.height + 2 * distance,
            name=rect_geom.name,
        ),
        style=sa_style,
    )
    new_elem.is_seam_allowance = True
    _project_dart_notches_to_sa(part)
    return [new_elem]


def _add_sa_segments(
    part: PatternPart,
    geoms: list[Segment | CubicBezier],
    distance: float,
    corner_join: str,
    sa_style: StyleOptions,
) -> list[PatternElement]:
    """Pure-segment path: offset via Shapely buffer."""
    chain = build_chain(geoms)
    buf_coords = buffer_chain(chain, distance, join_style=_CJ[corner_join])
    added: list[PatternElement] = []
    for (x1, y1), (x2, y2) in zip(buf_coords, buf_coords[1:], strict=False):
        elem = part.append(Segment(Point(x1, y1), Point(x2, y2)), style=sa_style)
        elem.is_seam_allowance = True
        added.append(elem)
    _project_dart_notches_to_sa(part)
    return added


def _add_sa_mixed(
    part: PatternPart,
    seam_elems: list[PatternElement],
    geoms: list[Segment | CubicBezier],
    distance: float,
    corner_join: str,
    sa_style: StyleOptions,
) -> list[PatternElement]:
    """Mixed / Bézier path: per-element offset + corner stitching."""
    center = part.centroid
    chain = build_chain(geoms)
    elem_sa, elem_center, elem_cj = _build_elem_overrides(seam_elems)

    offset_groups: list[list[Segment | CubicBezier]] = []
    for g in chain:
        d = elem_sa.get(_ep_key(g), distance)
        seg_center = elem_center.get(_ep_key(g), center)
        if d == 0.0:
            offset_groups.append([g])  # fold line — keep in place
        else:
            offset_groups.append(_offset_adaptive(g, d, seg_center))

    flat = _stitch_corners(offset_groups, chain, elem_cj, corner_join, distance)

    added: list[PatternElement] = []
    for geom in flat:
        elem = part.append(geom, style=sa_style)
        elem.is_seam_allowance = True
        added.append(elem)
    _project_dart_notches_to_sa(part)
    return added


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def add_seam_allowance(
    part: PatternPart,
    distance: float,
    outline_elements: list[PatternElement] | None = None,
    style: StyleOptions | None = None,
    corner_join: str = "miter",
) -> list[PatternElement]:
    """Offset the outline outward by *distance* mm and add the result as SA elements.

    Dispatches to one of three code paths:

    * **Rect** outline → uniform expansion (fast path).
    * **Pure-segment** outline with no per-element overrides → Shapely buffer.
    * **Mixed / Bézier** outline, or any per-element SA/corner-join override
      → per-element adaptive offset with corner stitching.

    Per-element ``StyleOptions(corner_join=…, seam_allowance=…)`` overrides
    the arguments here.

    Args:
        part: The pattern part to operate on.
        distance: Seam allowance in mm (must be positive).
        outline_elements: Defaults to all ``is_outline`` elements on *part*.
        style: SA line style; defaults to ``STYLE_SEAM_ALLOWANCE``.
        corner_join: ``"miter"`` (default), ``"round"``, or ``"bevel"``.

    Returns:
        List of newly created :class:`~sewpat.element.PatternElement` objects.

    Raises:
        ValueError: If *corner_join* is not a valid value, or *distance* ≤ 0.
    """
    if corner_join not in _VALID_CJ:
        raise ValueError(f"corner_join must be one of {sorted(_VALID_CJ)!r}, got {corner_join!r}")
    if distance <= 0:
        raise ValueError(f"seam allowance distance must be positive, got {distance}")

    sa_style = style if style is not None else STYLE_SEAM_ALLOWANCE

    if outline_elements is None:
        outline_elements = [e for e in part.elements if e.is_outline]
    if not outline_elements:
        return []

    # Rect fast-path: first Rect element triggers uniform expansion.
    for elem in outline_elements:
        if isinstance(elem.geometry, Rect):
            return _add_sa_rect(part, elem, distance, sa_style)

    # Collect Segment/CubicBezier outline elements; orient dart roof pairs so
    # build_chain can traverse them as a clean through-path.
    seam_elems: list[PatternElement] = [
        e for e in outline_elements if isinstance(e.geometry, (Segment, CubicBezier))
    ]
    seam_elems = _orient_dart_roof_pairs(seam_elems)
    geoms = cast(list[Segment | CubicBezier], [e.geometry for e in seam_elems])

    # Pure-segment path: Shapely buffer — only when no Béziers and no
    # per-element SA or corner-join overrides are present.
    has_bezier = any(isinstance(g, CubicBezier) for g in geoms)
    has_per_elem_sa = any(getattr(e.style, "seam_allowance", None) is not None for e in seam_elems)
    has_per_elem_cj = any(getattr(e.style, "corner_join", None) is not None for e in seam_elems)
    if not has_bezier and not has_per_elem_sa and not has_per_elem_cj:
        return _add_sa_segments(part, geoms, distance, corner_join, sa_style)

    return _add_sa_mixed(part, seam_elems, geoms, distance, corner_join, sa_style)


def _project_dart_notches_to_sa(part: PatternPart) -> None:
    """Project dart-leg and dart-center notches onto the SA edge.

    Called at the end of :func:`add_seam_allowance`.  For leg notches the
    position is projected perpendicularly onto the nearest SA edge while
    the roof-line orientation is preserved.  For the center notch the fold
    line is intersected with every SA edge so the result always lands
    exactly on the fold line, bypassing the roof knick-point.
    """
    sa_geoms: list[Segment | CubicBezier] = [
        e.geometry
        for e in part.elements
        if e.is_seam_allowance and isinstance(e.geometry, (Segment, CubicBezier))
    ]
    if not sa_geoms:
        return

    centroid_pt = part.centroid
    if centroid_pt is None:
        return  # empty part — nothing to project onto

    candidates = [
        e
        for e in part.elements
        if e.role in ("dart_notch", "dart_center_notch")
        and not e.is_seam_allowance
        and not e.is_seam_notch
        and isinstance(e.geometry, Triangle)
    ]

    for seam_elem in candidates:
        tri = cast(Triangle, seam_elem.geometry)
        base_centre = Point(
            (tri.p1.x + tri.p2.x) / 2,
            (tri.p1.y + tri.p2.y) / 2,
        )
        half_w = tri.p1.distance_to(tri.p2) / 2
        length = base_centre.distance_to(tri.p3)

        sa_edge = _closest_sa_edge(base_centre, sa_geoms)
        if sa_edge is None:
            continue

        _raw_inward = getattr(seam_elem, "_sa_center", None)
        effective_inward: Point = _raw_inward if isinstance(_raw_inward, Point) else centroid_pt

        # Pre-compute orientation unit vectors from the existing triangle.
        along_pt = Point(*_normalize_vec((tri.p2 - tri.p1).coords))
        normal_pt = Point(*_normalize_vec((tri.p3 - base_centre).coords))

        if seam_elem.role == "dart_center_notch":
            sa_pt = _fold_line_sa_point(seam_elem, sa_geoms, sa_edge, base_centre, effective_inward)
        else:
            _leg_pt = getattr(seam_elem, "_leg_pt", None)
            _proj_ref = _leg_pt if isinstance(_leg_pt, Point) else base_centre
            sa_pt, _, _ = project_onto_edge(sa_edge, _proj_ref, centroid_pt)

        is_double = _is_double_notch(seam_elem, part.elements)
        offsets = [-half_w * 1.5, half_w * 1.5] if is_double else [0.0]
        sa_role = seam_elem.role
        for offset in offsets:
            centre = sa_pt + along_pt * offset
            sa_notch_elem = part.append(
                Triangle(
                    centre - along_pt * half_w,
                    centre + along_pt * half_w,
                    centre + normal_pt * length,
                )
            )
            sa_notch_elem.is_seam_allowance = True
            sa_notch_elem.role = sa_role

        seam_elem.is_seam_notch = True


def _fold_line_sa_point(
    seam_elem: PatternElement,
    sa_geoms: list[Segment | CubicBezier],
    fallback_edge: Segment | CubicBezier,
    base_centre: Point,
    inward_ref: Point,
) -> Point:
    """Return the SA point for a center (fold-line) dart notch.

    Intersects the dart's fold line (extended outward from the roof) with
    every SA edge and picks the closest hit.  Falls back to a perpendicular
    projection onto *fallback_edge* when no intersection is found.

    Args:
        seam_elem: The dart center notch element (carries ``_dart_ref``).
        sa_geoms: All SA edges on the part.
        fallback_edge: Nearest SA edge used when the fold-line ray misses.
        base_centre: Midpoint of the notch triangle base.
        inward_ref: Inward reference point for the projection fallback.

    Returns:
        The projected SA point.
    """
    _dart = getattr(seam_elem, "_dart_ref", None)
    if _dart is not None:
        outward_dir = _normalize_vec(_dart.roof.coords - _dart.tip.coords)
        fold_ray = Ray(_dart.roof, outward_dir)
        best_d = float("inf")
        best_pt: Point | None = None
        for seg in sa_geoms:
            try:
                hits = _intersect_geom(fold_ray, seg)
            except TypeError, ValueError, AttributeError:
                # intersect can raise TypeError for unsupported types,
                # ValueError for degenerate geometry, or AttributeError
                # for malformed objects — skip this edge and continue
                continue
            for h in hits:
                d = _dart.roof.distance_to(h)
                if d < best_d:
                    best_d = d
                    best_pt = h
        if best_pt is not None:
            return best_pt

    pt, _, _ = project_onto_edge(fallback_edge, base_centre, inward_ref)
    return pt
