"""Notch placement — free functions that operate on a :class:`PatternPart`.

This module owns:

* :func:`add_notches` — place filled-triangle notch marks at given points.
* :func:`add_grid_notches` — place notches where outline edges intersect
  construction-grid lines, driven by an explicit role → grid-line mapping.

Both functions accept the part as their first argument and are wired back into
``PatternPart`` as thin one-liner wrapper methods in :mod:`sewpat.pattern.part`.
"""

import warnings
from typing import TYPE_CHECKING

import numpy as np

from ..element import PatternElement
from ..geometry import (
    CubicBezier,
    Point,
    Segment,
    Triangle,
    project_onto_edge,
)
from ..geometry import (
    intersect as _intersect,
)
from ..units import CM
from ._sa import _closest_sa_edge

if TYPE_CHECKING:
    from .part import PatternPart

# ---------------------------------------------------------------------------
# Public type alias
# ---------------------------------------------------------------------------

#: Maps a semantic role name (e.g. ``"side"``, ``"neckline"``) to a list of
#: construction-grid element names that should produce notches on that role.
#: An empty list means *no grid notches* for that role (the role is explicitly
#: excluded — no notches are placed on those edges).
#:
#: Example::
#:
#:     BACK_ROLE_MAP: RoleMap = {
#:         "side":     ["Waist", "Hip"],
#:         "armscye":  [],
#:         "shoulder": ["Armscye Back"],
#:         "neckline": [],
#:     }
RoleMap = dict[str, list[str]]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _too_close(pt: Point, candidates: list[Point], spacing: float) -> bool:
    """Return ``True`` if *pt* is within *spacing* mm of any point in *candidates*."""
    return any(pt.distance_to(c) < spacing for c in candidates)


def _ep_key(pt: Point) -> tuple[float, float]:
    """Return a rounded ``(x, y)`` key suitable for use in a dict or set."""
    return (round(pt.x, 3), round(pt.y, 3))


def _place_notch_triangles(
    part: PatternPart,
    notch_pt: Point,
    along: np.ndarray,
    normal: np.ndarray,
    half_w: float,
    length: float,
    *,
    is_back: bool = False,
    is_sa: bool = False,
    role: str = "",
) -> list[PatternElement]:
    """Append one or two notch :class:`~sewpat.geometry.Triangle` elements to *part*.

    When *is_back* is ``True`` two triangles are placed offset by
    ±1.5 × *half_w* along *along* (the back-piece double-notch convention).
    Each created element has ``is_seam_allowance`` set to *is_sa*; when *role*
    is non-empty it is assigned to ``element.role``.  All created elements are
    returned so callers can attach extra attributes.
    """
    along_pt = Point(*along)
    normal_pt = Point(*normal)
    offsets = [0.0] if not is_back else [-half_w * 1.5, +half_w * 1.5]
    created = []
    for offset in offsets:
        centre = notch_pt + along_pt * offset
        tip = centre + normal_pt * length
        bl = centre - along_pt * half_w
        br = centre + along_pt * half_w
        elem = part.append(Triangle(bl, br, tip))
        elem.is_seam_allowance = is_sa
        if role:
            elem.role = role
        created.append(elem)
    return created


# ---------------------------------------------------------------------------
# add_notches
# ---------------------------------------------------------------------------


def add_notches(
    part: PatternPart,
    *points: Point,
    seam_edge: Segment | CubicBezier | None = None,
    length: float = 0.8 * CM,
    width: float = 0.4 * CM,
    is_back: bool = False,
) -> None:
    """Add filled-triangle notch marks at *points*, always pointing inward.

    Each point receives one notch triangle (or two when *is_back* is ``True``,
    offset by ±1.5 × half-width — the back-piece double-notch convention).
    When *seam_edge* is supplied the notch is projected onto it and oriented
    along the edge tangent; without it a plain upright triangle is placed at
    the point directly.

    When seam-allowance elements are already present on *part*, a matching SA
    notch is placed on the nearest SA edge and the original notch is flagged
    ``is_seam_notch = True``.

    Args:
        part: The pattern part to add notches to.
        *points: One or more points at which to place notches.
        seam_edge: Optional edge to project the notch onto.
        length: Tip-to-base distance of the notch triangle.
        width: Base span of the notch triangle.
        is_back: When ``True``, place a double notch (back-piece convention).
    """
    inward_ref = part.centroid
    half_w = width / 2

    sa_geoms: list[Segment | CubicBezier] = [
        e.geometry
        for e in part.elements
        if e.is_seam_allowance and isinstance(e.geometry, (Segment | CubicBezier))
    ]

    for pt in points:
        if seam_edge is not None:
            notch_pt, along, normal = project_onto_edge(seam_edge, pt, inward_ref)
        else:
            notch_pt = pt
            along = np.array([1.0, 0.0])
            normal = np.array([0.0, -1.0])

        seam_elems = _place_notch_triangles(
            part, notch_pt, along, normal, half_w, length, is_back=is_back, is_sa=False
        )

        if sa_geoms:
            sa_edge = _closest_sa_edge(notch_pt, sa_geoms)
            if sa_edge is not None:
                sa_pt, sa_along, sa_normal = project_onto_edge(sa_edge, notch_pt, inward_ref)
                _place_notch_triangles(
                    part, sa_pt, sa_along, sa_normal, half_w, length, is_back=is_back, is_sa=True
                )
                for e in seam_elems:
                    e.is_seam_notch = True


# ---------------------------------------------------------------------------
# Role-based helpers
# ---------------------------------------------------------------------------


def _geoms_for_role(
    part: PatternPart,
    role: str,
) -> list[Segment | CubicBezier]:
    """Return all outline Segment/CubicBezier geometries tagged with *role*.

    Edges whose style has ``no_notch=True`` are excluded.
    """
    return [
        e.geometry
        for e in part.elements
        if e.role == role
        and e.is_outline
        and not (e.style and e.style.no_notch)
        and isinstance(e.geometry, (Segment, CubicBezier))
    ]


def _collect_candidates_by_role(
    part: PatternPart,
    grid_part: PatternPart,
    role_map: RoleMap,
) -> list[tuple[Segment | CubicBezier, Point]]:
    """Return intersection candidates using explicit role → grid-line name mapping.

    For each role in *role_map*:

    * Collect all outline elements on *part* tagged with that role.
    * Resolve each grid-line name to a geometry via ``grid_part.get_element``.
    * Intersect each role edge with each mapped grid line.

    The user's explicit role map defines which intersections should receive
    notches — no automatic filtering is applied based on corner proximity.

    Args:
        part: The pattern part whose outline edges are intersected.
        grid_part: The construction grid part supplying named grid lines.
        role_map: ``{role: [grid_line_name, …]}`` mapping.

    Returns:
        List of ``(outline_edge, point)`` candidates in role-map iteration order.
    """
    candidates: list[tuple[Segment | CubicBezier, Point]] = []

    for role, grid_names in role_map.items():
        if not grid_names:
            continue  # role explicitly mapped to no grid lines → skip

        role_geoms = _geoms_for_role(part, role)
        if not role_geoms:
            continue

        grid_geoms: list[Segment | CubicBezier] = []
        for name in grid_names:
            try:
                elem = grid_part.get_element(name)
            except KeyError, AttributeError:
                warnings.warn(
                    f"add_grid_notches: grid element {name!r} not found; skipping.",
                    UserWarning,
                    stacklevel=5,
                )
                continue
            if isinstance(elem.geometry, (Segment, CubicBezier)):
                grid_geoms.append(elem.geometry)

        if not grid_geoms:
            continue

        for og in role_geoms:
            for gg in grid_geoms:
                try:
                    pts = _intersect(og, gg)
                except Exception as exc:
                    warnings.warn(
                        f"add_grid_notches: intersection failed ({exc}); skipping.",
                        UserWarning,
                        stacklevel=5,
                    )
                    continue
                for pt in pts:
                    candidates.append((og, pt))

    return candidates


# ---------------------------------------------------------------------------
# _place_grid_notches
# ---------------------------------------------------------------------------


def _place_grid_notches(
    part: PatternPart,
    candidates: list[tuple[Segment | CubicBezier, Point]],
    seen: list[Point],
    min_spacing: float,
    length: float,
    width: float,
    is_back: bool,
) -> list[PatternElement]:
    """Place notches for *candidates*, skipping duplicates and spacing violations.

    *seen* is extended in-place so callers can pre-populate it with existing
    notch positions to enforce global spacing.  Returns all newly created
    :class:`~sewpat.element.PatternElement` objects.
    """
    created: list[PatternElement] = []
    elem_placed: dict[int, list[Point]] = {}

    for seam_geom, pt in candidates:
        if _too_close(pt, seen, min_spacing):
            continue
        if _too_close(pt, elem_placed.get(id(seam_geom), []), min_spacing):
            continue

        seen.append(pt)
        elem_placed.setdefault(id(seam_geom), []).append(pt)

        before = len(part.elements)
        add_notches(part, pt, seam_edge=seam_geom, length=length, width=width, is_back=is_back)
        created.extend(part.elements[before:])

    return created


# ---------------------------------------------------------------------------
# add_grid_notches
# ---------------------------------------------------------------------------


def add_grid_notches(
    part: PatternPart,
    grid_part: PatternPart,
    role_map: RoleMap,
    min_spacing: float = 8.0,
    length: float = 0.8 * CM,
    width: float = 0.4 * CM,
    is_back: bool = False,
) -> list[PatternElement]:
    """Add notches where outline edges intersect construction lines.

    Only elements whose ``role`` attribute appears as a key in *role_map* are
    considered.  For each role the mapped grid-line names are resolved by name
    from *grid_part* and intersected with the role's edges.  Elements without
    a matching role are silently skipped.

    Args:
        part: The pattern part to add notches to.
        grid_part: The construction grid part supplying named grid lines.
        role_map: ``{role: [grid_line_name, …]}`` mapping.  An empty list for a
            role means *no notches* for that role.
        min_spacing: Minimum distance (mm) between any two placed notches.
        length: Tip-to-base distance of each notch triangle.
        width: Base span of each notch triangle.
        is_back: When ``True``, place double notches (back-piece convention).

    Returns:
        All newly created :class:`~sewpat.element.PatternElement` objects.
    """
    # Pre-populate seen positions with existing *seam* notch base midpoints
    # (dart notches, manually placed notches) so that grid notches respect
    # min_spacing against them.  SA-duplicate triangles (is_seam_allowance=True)
    # are excluded — they are placed automatically alongside every seam notch.
    seen: list[Point] = [
        e.geometry.base_midpoint
        for e in part.elements
        if isinstance(e.geometry, Triangle) and not e.is_seam_allowance
    ]

    candidates = _collect_candidates_by_role(part, grid_part, role_map)
    return _place_grid_notches(part, candidates, seen, min_spacing, length, width, is_back)
