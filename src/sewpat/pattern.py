"""Pattern parts — collections of :class:`~sewpat.element.PatternElement` objects.

This module owns:

* :class:`DartResult` — return value of :meth:`PatternPart.add_dart`.
* :class:`PatternPart` — a single pattern piece (a named list of elements).
* :class:`ConstructionGridPart` / :class:`ConstructionGrid` — orthogonal grid helpers.
* :class:`Block` — a base-block pattern piece.
* :class:`OverlayPart` — a piece drafted on top of a parent part.
* :class:`Pattern` — a complete sewing pattern (collection of parts).
"""

import copy
from dataclasses import dataclass
from enum import Enum

import shapely.geometry as _sg

from .element import PatternElement, PrecisionPoint
from .geometry import (
    CubicBezier,
    Dart,
    InfoBox,
    Point,
    Ray,
    Rect,
    Segment,
    Triangle,
    buffer_chain,
    build_chain,
    edge_tangent,
    geom_end,
    geom_start,
    geom_to_shapely,
    miter_corner,
    outline_polygon,
    project_onto_edge,
    round_corner,
    with_endpoints,
)
from .geometry import (
    offset_adaptive as _offset_adaptive,
)
from .geometry import (
    seam_length as _geom_seam_length,
)
from .style import (
    STYLE_CONSTRUCTION_GRID,
    STYLE_DART_FOLD,
    STYLE_DART_STITCH,
    STYLE_GRAINLINE,
    STYLE_PRECISION_POINT,
    STYLE_SEAM_ALLOWANCE,
    StyleOptions,
)
from .units import CM, MM


@dataclass
class PatternConfig:
    anchor: Point = Point(5 * CM, 5 * CM, "anchor")
    margin: float = 10 * CM


class GarmentPart(str, Enum):
    """Base enum for pattern-part names.

    Subclass this in each garment module to define the parts of that pattern.
    Because values are plain strings, they can be used anywhere a part name
    string is expected — ``Pattern.get_part()``, the ``parts=`` argument of
    the export functions, and ``PatternPart(name=…)`` — without any changes
    to the rest of the library.

    Example::

        class Part(GarmentPart):
            BLOCK_BACK  = "Block Back"
            BLOCK_FRONT = "Block Front"
            GRID        = "Grid"

        block_back = PatternPart(name=Part.BLOCK_BACK)
        export_pattern_svg_mm(pattern, parts=[Part.GRID, Part.BLOCK_BACK])
    """


class DartResult:
    """Return value of :meth:`PatternPart.add_dart`.

    Attributes:
        dart: The dart geometry.
        elements: All :class:`PatternElement` objects created, in draw order.
            Filter by ``element.role`` for specific groups:
            ``"dart_stitch"``, ``"dart_fold"``, ``"dart_roof"``,
            ``"dart_tip"``, ``"dart_notch"``.
    """

    def __init__(self, dart: Dart, elements: list[PatternElement]) -> None:
        self.dart = dart
        self.elements = elements

    def __repr__(self) -> str:
        return f"DartResult(dart={self.dart!r}, elements={len(self.elements)})"

    def __iter__(self):
        """Iterate as ``(dart, *elements)`` to allow unpacking.

        Example::

            dart, *elems = part.add_dart(my_dart)
        """
        yield self.dart
        yield from self.elements


class NamedAccessMixin:
    """Mixin that exposes named :class:`PatternElement` objects as attributes.

    Allows snake_case attribute access to elements whose geometry carries a
    matching ``name``.  The conversion rule is:

    * underscores → spaces
    * result is title-cased

    So ``part.center_back`` resolves to the element named ``"Center Back"``.

    This is the ad-hoc complement to the typed-dataclass approach used by
    :class:`~sewpat.grids.TopGrid`: no boilerplate, IDE autocomplete via
    :meth:`get_element` for known names, and a clean ``AttributeError`` when
    the name is absent.

    Only triggers for names that are not already real attributes, so existing
    methods and properties are never shadowed.
    """

    elements: list[PatternElement]  # provided by PatternPart

    def __getattr__(self, snake: str) -> PatternElement:
        # Avoid infinite recursion for dunder / private attributes.
        if snake.startswith("_"):
            raise AttributeError(snake)
        key = snake.replace("_", " ").title()
        for e in self.elements:
            if e.get_name() == key:
                return e
        raise AttributeError(
            f"{type(self).__name__!r} has no element named {key!r} "
            f"(looked up as {snake!r})"
        )


class PatternPart(NamedAccessMixin):
    """A collection of pattern elements forming one pattern piece."""

    def __init__(
        self,
        name: str,
        elements: list[PatternElement] | None = None,
        is_construction: bool = False,
    ) -> None:
        self.name = name
        self.elements: list[PatternElement] = elements if elements is not None else []
        self.is_construction: bool = is_construction

    def append(
        self,
        geometry: object,
        style: StyleOptions | None = None,
        is_outline: bool = False,
    ) -> PatternElement:
        """Wrap *geometry* in a PatternElement, stamp ``is_construction``, and append it.

        The element's name is taken from ``geometry.name``; set it on the
        geometry object before calling (e.g. ``seg.set_name("Center Back")``).
        """
        elem = PatternElement(
            geometry=geometry,
            style=style,
            is_outline=is_outline,
            is_construction=self.is_construction,
        )
        self.elements.append(elem)
        return elem

    def extend(self, elements: list[PatternElement]) -> None:
        """Append multiple :class:`~sewpat.element.PatternElement` objects, stamping
        ``is_construction`` from this part.

        When a :class:`PatternElement` wraps a :class:`~sewpat.geometry.Dart`
        as its geometry, it is dispatched to :meth:`add_dart` using the
        element's ``style`` as ``stitch_style``; all other dart options keep
        their defaults.  Use :meth:`add_dart` directly when you need full
        control over fold style, notches, etc.

        All other :class:`PatternElement` objects are appended as-is after
        stamping ``is_construction``.
        """
        for elem in elements:
            if isinstance(elem.geometry, Dart):
                self.add_dart(elem.geometry, stitch_style=elem.style)
            else:
                elem.is_construction = elem.is_construction or self.is_construction
                self.elements.append(elem)

    def _outline_polygon(self) -> _sg.Polygon | None:
        """Build a Shapely Polygon from the ``is_outline`` elements of this part."""
        geoms = [
            e.geometry
            for e in self.elements
            if e.is_outline and isinstance(e.geometry, (Segment, CubicBezier))
        ]
        return outline_polygon(geoms) if geoms else None

    @property
    def centroid(self) -> Point | None:
        """Geometric centroid of the outline polygon, or ``None`` if not yet defined."""
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return None
        c = poly.centroid
        return Point(c.x, c.y)

    @property
    def area_cm2(self) -> float | None:
        """Area of the outline polygon in cm², or ``None`` if not yet defined."""
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return None
        return poly.area / 100.0

    def bounding_box(self) -> tuple[Point, Point] | None:
        """Axis-aligned bounding box of the outline polygon.

        Returns:
            ``(min_point, max_point)`` in mm, or ``None`` if no outline exists.
        """
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return Point(minx, miny), Point(maxx, maxy)

    def get_element(self, name: str) -> PatternElement:
        """Return the first :class:`PatternElement` whose geometry carries *name*.

        Prefer snake_case attribute access via :class:`NamedAccessMixin`
        (e.g. ``part.center_back``) over calling this method directly.
        Use this method when the name contains characters that cannot form a
        valid Python identifier (e.g. spaces, slashes).

        Raises:
            KeyError: If no element with that name exists in this part.
        """
        for e in self.elements:
            if e.get_name() == name:
                return e
        raise KeyError(f"No element named {name!r} in part {self.name!r}")

    def seam_length(
        self,
        geoms_or_names: list[Segment | CubicBezier | PatternElement | str],
    ) -> float:
        """Return the total arc length in mm of the given seam elements.

        Each entry may be a ``Segment``, ``CubicBezier``, ``PatternElement``
        (geometry is unwrapped), or a ``str`` name (all matching elements
        in this part are summed).  Mixed lists are fine.

        Raises:
            KeyError: If a name string matches no element in this part.
            TypeError: If an entry is none of the accepted types.
        """
        resolved: list[Segment | CubicBezier] = []
        for item in geoms_or_names:
            if isinstance(item, PatternElement):
                if isinstance(item.geometry, (Segment, CubicBezier)):
                    resolved.append(item.geometry)
            elif isinstance(item, (Segment, CubicBezier)):
                resolved.append(item)
            elif isinstance(item, str):
                matches = [
                    e.geometry
                    for e in self.elements
                    if e.get_name() == item
                    and isinstance(e.geometry, (Segment, CubicBezier))
                ]
                if not matches:
                    raise KeyError(
                        f"No Segment/CubicBezier named {item!r} in part {self.name!r}"
                    )
                resolved.extend(matches)
            else:
                raise TypeError(
                    f"Expected Segment, CubicBezier, PatternElement, or str; got {type(item).__name__}"
                )
        return _geom_seam_length(resolved)

    def contains_point(self, point: Point) -> bool:
        """Return True if *point* lies strictly inside the outline polygon (boundary = False)."""
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return False
        return bool(poly.contains(_sg.Point(point.x, point.y)))

    def _nudge_point_inside(
        self,
        point: Point,
        inward_ref: Point,
        step: float = 1.0,
        max_steps: int = 200,
    ) -> Point:
        """Return *point* moved inside the outline if it lies strictly outside.

        Points already inside or on the boundary (within 0.1 mm) are returned
        unchanged — boundary endpoints are valid grainline endpoints.
        """
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return point
        sp = _sg.Point(point.x, point.y)
        # Keep points that are inside or on (≤ 0.1 mm from) the boundary.
        if poly.contains(sp) or poly.exterior.distance(sp) <= 0.1:
            return point
        # Point is strictly outside — snap to boundary, then nudge inward.
        snapped = poly.exterior.interpolate(poly.exterior.project(sp))
        dx = inward_ref.x - snapped.x
        dy = inward_ref.y - snapped.y
        dist = (dx**2 + dy**2) ** 0.5
        if dist < 1e-9:
            return point
        nudge = min(step, dist * 0.5)
        return Point(snapped.x + nudge * dx / dist, snapped.y + nudge * dy / dist)

    def add_grainline(
        self,
        start: Point,
        end: Point,
        name: str = "grainline / Fadenlauf",
        style: StyleOptions | None = None,
    ) -> PatternElement:
        """Add a grainline segment, nudging outside endpoints inward along the grain axis.

        Each endpoint is nudged toward the opposite one, so the grainline stays
        perfectly straight even when an endpoint sits on the outline boundary.

        Args:
            style: Optional style override; defaults to :data:`STYLE_GRAINLINE`.
        """
        start = self._nudge_point_inside(start, end)
        end = self._nudge_point_inside(end, start)
        return self.append(
            Segment(start, end, name=name),
            style=style if style is not None else STYLE_GRAINLINE,
        )

    def add_info_box(
        self, header: str | None = None, notes: list[str] | None = None
    ) -> PatternElement | None:
        """Add an info box at the centroid of this part.

        Args:
            header: Bold header text. Defaults to the part name.
            notes: Optional note lines shown below the header.

        Returns:
            The created PatternElement, or ``None`` if no centroid exists yet.
        """
        pos = self.centroid
        if pos is None:
            return None
        return self.append(
            InfoBox(
                position=pos + Point(0, 3 * CM),
                header=header if header is not None else self.name,
                notes=notes,
            )
        )

    def add_precision_points(
        self,
        *centers: Point,
        style: StyleOptions | None = None,
    ) -> None:
        """Add a two-circle precision mark at each given point.

        Each mark is a :class:`~sewpat.element.PrecisionPoint` with default
        radii (2 mm outer, 0.2 mm inner).  To use custom radii, construct a
        :class:`~sewpat.element.PrecisionPoint` directly and pass its elements
        to :meth:`append` or :meth:`extend`.

        Args:
            *centers: Points at which to place precision marks.
            style: Visual style for the circles.  Defaults to
                :data:`~sewpat.style.STYLE_PRECISION_POINT`.
        """
        if style is None:
            style = STYLE_PRECISION_POINT
        for center in centers:
            pp = PrecisionPoint(center, style=style)
            self.extend(pp.build_elements())

    def add_notches(
        self,
        *points: Point,
        seam_edge: Segment | CubicBezier | None = None,
        length: float = 0.8 * CM,
        width: float = 0.4 * CM,
        symbol: str = "Triangle",
        is_back: bool = False,
    ) -> None:
        """Add filled-triangle notch marks at *points*, always pointing inward.

        Args:
            *points: Reference points for the notches.
            seam_edge: Edge to project onto for tangent/normal; without it a
                vertical triangle centred on the point is used.
            length: Tip-to-base distance. Defaults to 0.8 cm.
            width: Base width on the seam edge. Defaults to 0.4 cm.
            is_back: Two neighbouring triangles (back piece convention) if True.
        """
        inward_ref = self.centroid
        half_w = width / 2
        gap = width * 0.5

        sa_geoms: list[Segment | CubicBezier] = [
            e.geometry
            for e in self.elements
            if e.is_seam_allowance and isinstance(e.geometry, (Segment, CubicBezier))
        ]

        def _closest_sa_edge(ref: Point) -> Segment | CubicBezier | None:
            if not sa_geoms:
                return None
            sp = _sg.Point(ref.x, ref.y)
            return min(sa_geoms, key=lambda g: sp.distance(geom_to_shapely(g)))

        def _place_symbol(notch_pt: Point, along, normal, symbol, is_sa: bool) -> list:
            along_pt = Point(*along)
            normal_pt = Point(*normal)
            offsets = (
                [0.0] if not is_back else [-(half_w + gap / 2), +(half_w + gap / 2)]
            )
            created = []
            for offset in offsets:
                centre = notch_pt + along_pt * offset
                tip = centre + normal_pt * length
                if symbol == "Triangle":
                    bl = centre - along_pt * half_w
                    br = centre + along_pt * half_w
                else:
                    bl = centre - along_pt * (half_w / 5)
                    br = centre + along_pt * (half_w / 5)
                elem = self.append(Triangle(bl, br, tip))
                elem.is_seam_allowance = is_sa
                created.append(elem)
            return created

        for pt in points:
            if seam_edge is not None:
                notch_pt, along, normal = project_onto_edge(seam_edge, pt, inward_ref)
            else:
                notch_pt, along, normal = pt, (1.0, 0.0), (0.0, -1.0)
            seam_elems = _place_symbol(notch_pt, along, normal, symbol, is_sa=False)

            if sa_geoms:
                sa_edge = _closest_sa_edge(notch_pt)
                if sa_edge is not None:
                    sa_notch_pt, sa_along, sa_normal = project_onto_edge(
                        sa_edge, notch_pt, inward_ref
                    )
                    _place_symbol(sa_notch_pt, sa_along, sa_normal, symbol, is_sa=True)
                    for e in seam_elems:
                        e.is_seam_notch = True

    def add_seam_allowance(
        self,
        distance: float,
        outline_elements: list[PatternElement] | None = None,
        style: StyleOptions | None = None,
        corner_join: str = "miter",
    ) -> list[PatternElement]:
        """Offset the outline outward by *distance* mm and add the result as SA elements.

        Three code paths: **Rect** outlines expand uniformly; **pure-segment**
        outlines use ``Shapely.Polygon.buffer()``; **mixed/Bézier** outlines
        offset each element and stitch corners via *corner_join*.

        Per-element ``StyleOptions(corner_join=…, seam_allowance=…)`` overrides
        the arguments here.

        Args:
            distance: Seam allowance in mm (must be positive).
            outline_elements: Defaults to all ``is_outline`` elements.
            style: Defaults to ``STYLE_SEAM_ALLOWANCE``.
            corner_join: ``"miter"`` (default), ``"round"``, or ``"bevel"``.

        Returns:
            List of newly created PatternElement objects.
        """
        _CJ = {"miter": 2, "round": 1, "bevel": 3}
        if corner_join not in _CJ:
            raise ValueError(
                f"corner_join must be one of {list(_CJ)!r}, got {corner_join!r}"
            )
        if distance <= 0:
            raise ValueError(
                f"seam allowance distance must be positive, got {distance}"
            )

        sa_style = style if style is not None else STYLE_SEAM_ALLOWANCE

        if outline_elements is None:
            outline_elements = [e for e in self.elements if e.is_outline]
        if not outline_elements:
            return []

        # ── Rect fast-path ────────────────────────────────────────────────────
        for elem in outline_elements:
            if isinstance(elem.geometry, Rect):
                g = elem.geometry
                new_elem = self.append(
                    Rect(
                        origin=g.origin.translate(-distance, -distance),
                        width=g.width + 2 * distance,
                        height=g.height + 2 * distance,
                        name=g.name,
                    ),
                    style=sa_style,
                )
                new_elem.is_seam_allowance = True
                return [new_elem]

        geoms: list[Segment | CubicBezier] = [
            e.geometry
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
        ]

        # ── Pure-segment path: Shapely buffer ────────────────────────────────
        has_per_elem_sa = any(
            getattr(e.style, "seam_allowance", None) is not None
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
        )
        has_per_elem_cj = any(
            getattr(e.style, "corner_join", None) is not None
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
        )
        if (
            not any(isinstance(g, CubicBezier) for g in geoms)
            and not has_per_elem_sa
            and not has_per_elem_cj
        ):
            chain = build_chain(geoms)
            buf_coords = buffer_chain(chain, distance, join_style=_CJ[corner_join])
            added: list[PatternElement] = []
            for (x1, y1), (x2, y2) in zip(buf_coords, buf_coords[1:]):
                elem = self.append(
                    Segment(Point(x1, y1), Point(x2, y2)), style=sa_style
                )
                elem.is_seam_allowance = True
                added.append(elem)
            return added

        # ── Mixed / Bézier path: per-element offset + corner stitching ────────
        center = self.centroid
        chain_mixed = build_chain(geoms)

        def _ep_key(g: Segment | CubicBezier) -> frozenset:
            s, e = geom_start(g), geom_end(g)
            return frozenset(
                [(round(s.x, 6), round(s.y, 6)), (round(e.x, 6), round(e.y, 6))]
            )

        # seam_allowance=None  → not in dict → use global distance
        # seam_allowance=0.0   → in dict as 0.0 → no offset (fold line)
        # seam_allowance=x > 0 → in dict as x   → custom distance
        elem_sa: dict[frozenset, float] = {
            _ep_key(e.geometry): getattr(e.style, "seam_allowance")
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
            and getattr(e.style, "seam_allowance", None) is not None
        }

        _valid_cj = {"miter", "round", "bevel"}
        elem_cj: dict[frozenset, str] = {}
        for e in outline_elements:
            if not isinstance(e.geometry, (Segment, CubicBezier)):
                continue
            val = getattr(e.style, "corner_join", None)
            if val is None:
                continue
            if val not in _valid_cj:
                raise ValueError(
                    f"StyleOptions.corner_join must be one of {sorted(_valid_cj)!r}, "
                    f"got {val!r} on element {e.get_name()!r}"
                )
            elem_cj[_ep_key(e.geometry)] = val

        offset_groups: list[list[Segment | CubicBezier]] = []
        for g in chain_mixed:
            d = elem_sa.get(_ep_key(g), distance)
            if d == 0.0:
                offset_groups.append([g])  # fold line — keep in place
            else:
                offset_groups.append(_offset_adaptive(g, d, center))

        n = len(offset_groups)
        arc_inserts: list[tuple[int, CubicBezier]] = []
        for i in range(n):
            j = (i + 1) % n
            ga = offset_groups[i][-1]
            gb = offset_groups[j][0]
            if geom_end(ga).distance_to(geom_start(gb)) > 0.01:
                key_a = _ep_key(chain_mixed[i])
                key_b = _ep_key(chain_mixed[j])
                effective_cj = elem_cj.get(key_a) or elem_cj.get(key_b) or corner_join

                if effective_cj == "miter":
                    corner = miter_corner(ga, gb, distance)
                    offset_groups[i][-1] = with_endpoints(ga, geom_start(ga), corner)
                    offset_groups[j][0] = with_endpoints(gb, corner, geom_end(gb))
                elif effective_cj == "round":
                    arc = round_corner(ga, gb)
                    if isinstance(arc, CubicBezier):
                        offset_groups[i][-1] = with_endpoints(
                            ga, geom_start(ga), arc.p0
                        )
                        offset_groups[j][0] = with_endpoints(gb, arc.p3, geom_end(gb))
                        arc_inserts.append((i, arc))
                    else:
                        offset_groups[i][-1] = with_endpoints(ga, geom_start(ga), arc)
                        offset_groups[j][0] = with_endpoints(gb, arc, geom_end(gb))
                else:  # bevel
                    _ea = geom_end(ga)
                    _sb = geom_start(gb)
                    corner = (_ea + _sb) * 0.5
                    offset_groups[i][-1] = with_endpoints(ga, geom_start(ga), corner)
                    offset_groups[j][0] = with_endpoints(gb, corner, geom_end(gb))

        flat: list[Segment | CubicBezier] = []
        for group in offset_groups:
            flat.extend(group)
        group_end_flat: list[int] = []
        pos = 0
        for group in offset_groups:
            pos += len(group)
            group_end_flat.append(pos - 1)
        for group_i, arc in sorted(arc_inserts, key=lambda x: x[0], reverse=True):
            flat.insert(group_end_flat[group_i] + 1, arc)

        added_mixed: list[PatternElement] = []
        for geom in flat:
            elem = self.append(geom, style=sa_style)
            elem.is_seam_allowance = True
            added_mixed.append(elem)
        return added_mixed

    def add_dart(
        self,
        dart: Dart,
        *,
        stitch_style: StyleOptions | None = None,
        fold_style: StyleOptions = STYLE_DART_FOLD,
        precision_style: StyleOptions = STYLE_PRECISION_POINT,
        notches: bool = True,
        precision_tip: bool = True,
        notch_kwargs: dict | None = None,
    ) -> DartResult:
        """Add all visual elements for *dart* to this part.

        The dart's ``_edge_element`` (set automatically by the
        ``Dart.from_edge_*`` factories) provides the style for the roof
        outline segments.  When absent a plain default style is used.

        **Triangle dart:** stitch lines, fold line, Abnäherdach roof outline
        (``is_outline=True``), notches, precision tip mark.

        **Rhombus dart:** four diamond sides, precision marks at both apices.

        Args:
            dart: A :class:`~sewpat.geometry.Dart` instance.
            stitch_style: Override for stitch-line style.
            fold_style: Override for fold-line style.
            precision_style: Override for precision-mark style.
            notches: Add notch marks at the leg points (triangle darts only).
            precision_tip: Add precision circles at the tip.
            notch_kwargs: Extra kwargs forwarded to :meth:`add_notches`.

        Returns:
            :class:`DartResult` with ``dart`` and ``elements``.
        """
        _stitch = stitch_style if stitch_style is not None else STYLE_DART_STITCH
        _fold = fold_style if fold_style is not None else STYLE_DART_FOLD
        _nkw: dict = notch_kwargs if notch_kwargs is not None else {}

        # Edge style for the roof outline: inherit from source element when available.
        edge_elem = getattr(dart, "_edge_element", None)
        edge_style = getattr(edge_elem, "style", None)
        roof_style = copy.copy(edge_style) if edge_style is not None else StyleOptions()
        roof_style.corner_join = "miter"

        created: list[PatternElement] = []

        # ── Split the source edge at the dart legs ───────────────────────────
        # When the dart was created from an outline edge, the original segment
        # is replaced by the outer sub-segments produced by splitting at the
        # two leg points.  The dart mouth between the legs is thereby removed
        # from the outline so add_seam_allowance() sees the correct polygon.
        if (
            dart.is_triangle
            and edge_elem is not None
            and edge_elem in self.elements
            and edge_elem.is_outline
            and isinstance(edge_elem.geometry, (Segment, CubicBezier))
        ):
            src_style = (
                copy.copy(edge_elem.style)
                if edge_elem.style is not None
                else StyleOptions()
            )
            all_subs = edge_elem.geometry.split_at_points([dart.leg_a, dart.leg_b])
            # The middle sub-segment (between the two legs) is the dart mouth —
            # discard it; keep only the first and last sub-segments.
            outer_subs = all_subs[:1] + (all_subs[-1:] if len(all_subs) > 1 else [])
            edge_elem.is_outline = False
            idx = self.elements.index(edge_elem)
            for i, seg in enumerate(outer_subs):
                stub = PatternElement(
                    seg, style=src_style, is_outline=True, role="dart_edge_stub"
                )
                self.elements.insert(idx + 1 + i, stub)
                created.append(stub)

        def _add(elem: PatternElement) -> PatternElement:
            self.elements.append(elem)
            created.append(elem)
            return elem

        if dart.is_triangle:
            # Stitch lines (tip → leg_a, tip → leg_b)
            _add(PatternElement(dart.stitch_line_a, style=_stitch, role="dart_stitch"))
            _add(PatternElement(dart.stitch_line_b, style=_stitch, role="dart_stitch"))

            # Fold / crease line
            _add(PatternElement(dart.fold_line, style=_fold, role="dart_fold"))

            # Abnäherdach roof outline — replaces the straight mouth edge
            roof = dart.roof
            _add(
                PatternElement(
                    Segment(dart.leg_a, roof),
                    style=roof_style,
                    is_outline=True,
                    role="dart_roof",
                )
            )
            _add(
                PatternElement(
                    Segment(dart.leg_b, roof),
                    style=roof_style,
                    is_outline=True,
                    role="dart_roof",
                )
            )

            # Centre notch at the roof peak
            if notches:
                delta = dart.roof - dart.center
                mouth_edge = Segment(dart.leg_a + delta, dart.leg_b + delta)
                before = len(self.elements)
                self.add_notches(roof, seam_edge=mouth_edge, **_nkw, symbol="")
                for e in self.elements[before:]:
                    e.role = "dart_notch"
                    created.append(e)

            # Tip precision mark
            if precision_tip:
                for e in PrecisionPoint(
                    dart.tip, style=precision_style
                ).build_elements():
                    e.role = "dart_tip"
                    _add(e)
                if dart.name:
                    _add(
                        PatternElement(
                            InfoBox(dart.tip - Point(0, 14 * MM), header=dart.name),
                            role="dart_tip",
                        )
                    )

            # Leg notches
            if notches:
                mouth_edge = Segment(dart.leg_a, dart.leg_b)
                for pt in (dart.leg_a, dart.leg_b):
                    before = len(self.elements)
                    self.add_notches(pt, seam_edge=mouth_edge, **_nkw)
                    for e in self.elements[before:]:
                        e.role = "dart_notch"
                        created.append(e)

        else:
            # Rhombus dart — four diamond sides
            st = dart.effective_second_tip
            for p1, p2 in [
                (dart.leg_a, dart.tip),
                (dart.tip, dart.leg_b),
                (dart.leg_b, st),
                (st, dart.leg_a),
            ]:
                _add(PatternElement(Segment(p1, p2), style=_stitch, role="dart_stitch"))

            # Precision marks at both apices
            if precision_tip:
                for pt in (dart.tip, st):
                    for e in PrecisionPoint(pt, style=precision_style).build_elements():
                        e.role = "dart_tip"
                        _add(e)
                if dart.name:
                    _add(
                        PatternElement(
                            InfoBox(dart.tip - Point(0, 14 * MM), header=dart.name),
                            role="dart_tip",
                        )
                    )

        return DartResult(dart=dart, elements=created)

    def add_construction_line(
        self,
        geometry: Segment | Ray,
        name: str | None = None,
        style: StyleOptions | None = None,
    ) -> PatternElement:
        """Append a construction-grid line (never ``is_outline``; defaults to grid style).

        *name* is applied directly to *geometry* so it is the single source of
        truth and can be retrieved via :meth:`~sewpat.pattern.PatternPart.get_element`.
        """
        if name is not None:
            geometry = geometry.set_name(name)
        return self.append(
            geometry,
            style=style if style is not None else STYLE_CONSTRUCTION_GRID,
        )

    def add_grid_notches(
        self,
        grid_part: "PatternPart",
        tolerance: float = 1.0,
        min_spacing: float = 8.0,
        corner_clearance: float = 15.0,
        length: float = 0.8 * CM,
        width: float = 0.4 * CM,
        is_back: bool = False,
        corner_angle_threshold: float = 30.0,
    ) -> list[PatternElement]:
        """Add notches where outline edges intersect construction lines.

        Sharp corners and free endpoints are skipped (within *tolerance* mm and
        within *corner_clearance* mm).  Horizontal grid lines take priority over
        vertical ones when two candidates are within *min_spacing* mm of each other.
        """
        import math as _math

        import numpy as _np

        from .geometry import intersect as _intersect

        outline_elems = [
            e
            for e in self.elements
            if e.is_outline and isinstance(e.geometry, (Segment, CubicBezier))
        ]
        grid_geoms = [
            e.geometry
            for e in grid_part.elements
            if isinstance(e.geometry, (Segment, CubicBezier, Ray))
        ]

        # Build map of forward tangents at each outline endpoint for corner detection.
        ep_tangents: dict[tuple, list] = {}
        for oe in outline_elems:
            s = geom_start(oe.geometry)
            e = geom_end(oe.geometry)
            sk = (round(s.x, 3), round(s.y, 3))
            ek = (round(e.x, 3), round(e.y, 3))
            ep_tangents.setdefault(sk, []).append(
                edge_tangent(oe.geometry, at_end=False)
            )
            ep_tangents.setdefault(ek, []).append(
                edge_tangent(oe.geometry, at_end=True)
            )

        def _is_corner_endpoint(pt: Point) -> bool:
            """True when *pt* is within *tolerance* of a sharp corner or free endpoint."""
            for oe in outline_elems:
                for ep in (geom_start(oe.geometry), geom_end(oe.geometry)):
                    if pt.distance_to(ep) >= tolerance:
                        continue
                    key = (round(ep.x, 3), round(ep.y, 3))
                    tangents = ep_tangents.get(key, [])
                    if len(tangents) < 2:
                        return True  # free endpoint
                    t0, t1 = tangents[0], tangents[1]
                    cos_a = float(_np.clip(_np.dot(t0, t1), -1.0, 1.0))
                    if _math.degrees(_math.acos(abs(cos_a))) > corner_angle_threshold:
                        return True  # sharp corner
            return False

        def _is_horizontal(g: Segment | CubicBezier | Ray) -> bool:
            if isinstance(g, Segment):
                return abs(geom_start(g).y - geom_end(g).y) < 1e-6
            return False

        corner_vertices: list[Point] = []
        for oe in outline_elems:
            for ep in (geom_start(oe.geometry), geom_end(oe.geometry)):
                key = (round(ep.x, 3), round(ep.y, 3))
                tangents = ep_tangents.get(key, [])
                if len(tangents) < 2:
                    corner_vertices.append(ep)
                else:
                    t0, t1 = tangents[0], tangents[1]
                    cos_a = float(_np.clip(_np.dot(t0, t1), -1.0, 1.0))
                    if _math.degrees(_math.acos(abs(cos_a))) > corner_angle_threshold:
                        corner_vertices.append(ep)

        def _is_near_corner(pt: Point) -> bool:
            return any(pt.distance_to(v) <= corner_clearance for v in corner_vertices)

        seen: list[Point] = []
        for e in self.elements:
            if isinstance(e.geometry, Triangle):
                tri = e.geometry
                seen.append(Point((tri.p1.x + tri.p2.x) / 2, (tri.p1.y + tri.p2.y) / 2))

        created: list[PatternElement] = []

        def _is_dup(pt: Point) -> bool:
            return any(pt.distance_to(s) < min_spacing for s in seen)

        candidates: list[tuple[int, Segment | CubicBezier, Point]] = []
        for oe in outline_elems:
            for gg in grid_geoms:
                is_horiz = _is_horizontal(gg)
                try:
                    pts = _intersect(oe.geometry, gg)
                except TypeError, Exception:
                    continue
                priority = 0 if is_horiz else 1
                for pt in pts:
                    if not _is_corner_endpoint(pt) and not _is_near_corner(pt):
                        candidates.append((priority, oe.geometry, pt))

        candidates.sort(key=lambda c: c[0])

        elem_placed: dict[int, list[Point]] = {}
        elem_has_horizontal: set[int] = set()

        def _is_dup_on_elem(geom: Segment | CubicBezier, pt: Point) -> bool:
            for placed_pt in elem_placed.get(id(geom), []):
                if pt.distance_to(placed_pt) < min_spacing:
                    return True
            return False

        for priority, seam_geom, pt in candidates:
            is_vertical = priority == 1
            if is_vertical and id(seam_geom) in elem_has_horizontal:
                continue
            if _is_dup(pt) or _is_dup_on_elem(seam_geom, pt):
                continue
            seen.append(pt)
            elem_placed.setdefault(id(seam_geom), []).append(pt)
            if not is_vertical:
                elem_has_horizontal.add(id(seam_geom))
            before = len(self.elements)
            self.add_notches(
                pt, seam_edge=seam_geom, length=length, width=width, is_back=is_back
            )
            created.extend(self.elements[before:])
        return created


class ConstructionGridPart(PatternPart):
    """A :class:`PatternPart` that represents a construction grid.

    Grid elements are kept separate from the main pattern pieces when rendering
    by default — they are only included when requested explicitly by name via
    the ``parts=`` argument of the export functions.

    All elements appended to this part automatically receive
    ``is_construction=True``, so they are hidden when ``show_construction=False``
    is passed to the export functions.

    Prefer building instances via :class:`ConstructionGrid` rather than
    creating them directly.
    """

    def __init__(
        self,
        name: str = "Konstruktionsgitter",
        elements: list[PatternElement] | None = None,
    ) -> None:
        super().__init__(name=name, elements=elements, is_construction=True)


class Block(PatternPart):
    """A base-block pattern piece derived from balanced measurements.

    A block captures the fundamental shape of a garment *without* personal
    fitting adjustments or style details.  It serves as a reusable starting
    point for new patterns and can be shown/hidden via the ``show_blocks``
    flag in the SVG export helpers.

    The part is identified by ``isinstance(part, Block)``.
    """

    def __init__(self, name: str, elements: list[PatternElement] | None = None) -> None:
        super().__init__(name=name, elements=elements)


class OverlayPart(PatternPart):
    """A pattern piece drafted directly on top of a parent part (same coordinate space).

    The overlay is constructed normally — its geometry lives in the same
    coordinate system as *parent*, so it can share reference points and edges
    directly.  When drafting is done, call :meth:`explode` to produce an
    independent, repositioned :class:`PatternPart` that can be cut separately.

    Args:
        name: Name of the overlay piece.
        parent: The pattern part this overlay is drafted on.

    Example::

        pocket = OverlayPart("Tasche", parent=front)
        pocket.append(Segment(pocket_top_left, pocket_top_right), is_outline=True)
        # … add more geometry …
        exploded = pocket.explode(offset=Point(10*CM, 0))
        pattern.add_part(pocket)     # visible on the front piece during drafting
        pattern.add_part(exploded)   # separate cut piece
    """

    def __init__(
        self,
        name: str,
        parent: PatternPart,
        elements: list[PatternElement] | None = None,
    ) -> None:
        super().__init__(name=name, elements=elements)
        self.parent = parent

    def explode(self, offset: Point, name: str | None = None) -> PatternPart:
        """Detach this overlay into a standalone :class:`PatternPart`.

        Every element's geometry is translated by *offset* so the new part
        sits next to the parent on the page rather than on top of it.

        Args:
            offset: Translation applied to all geometry in the exploded part.
                Typically ``Point(parent_width + gap, 0)`` to place it to the
                right of the parent.
            name: Name for the exploded part.  Defaults to ``self.name``.

        Returns:
            A new plain :class:`PatternPart` with translated geometry.
        """
        dx, dy = offset.x, offset.y

        exploded = PatternPart(name=name if name is not None else self.name)
        for elem in self.elements:
            new_geom = elem.geometry.translate(dx, dy)
            new_elem = PatternElement(
                geometry=new_geom,
                style=elem.style,
                name=elem.name,
                is_outline=elem.is_outline,
                is_seam_allowance=elem.is_seam_allowance,
            )
            new_elem.is_seam_notch = elem.is_seam_notch
            exploded.elements.append(new_elem)

        return exploded


class ConstructionGrid:
    """Builds an orthogonal construction grid as a :class:`PatternPart`.

    Each horizontal/vertical line is labelled with its measurement name.

    Args:
        anchor: Top-left origin of the grid.
        verticals: ``(name, x_offset_mm)`` pairs — lines parallel to the y-axis.
        horizontals: ``(name, y_offset_mm)`` pairs — lines parallel to the x-axis.
        extent: Half-length of each line in mm (default 1500).
        part_name: Name of the produced PatternPart.
        style: Defaults to ``STYLE_CONSTRUCTION_GRID``.

    Example::

        grid = ConstructionGrid(
            anchor=Point(10*CM, 10*CM),
            verticals=[("Hintermitte", 0), ("Vorderbreite", 39*CM)],
            horizontals=[("Bund", 0), ("Brust", 27*CM), ("Taille", 39*CM)],
        )
        pattern.add_part(grid.build())
    """

    def __init__(
        self,
        anchor: Point,
        verticals: list[tuple[str, float]] | None = None,
        horizontals: list[tuple[str, float]] | None = None,
        extent: float = 1500.0,
        part_name: str = "Konstruktionsgitter",
        style: StyleOptions | None = None,
    ) -> None:
        self.anchor = anchor
        self.verticals: list[tuple[str, float]] = verticals or []
        self.horizontals: list[tuple[str, float]] = horizontals or []
        self.extent = extent
        self.part_name = part_name
        self.style = style if style is not None else STYLE_CONSTRUCTION_GRID

    def build(self) -> ConstructionGridPart:
        """Build and return the construction-grid as a :class:`ConstructionGridPart`."""
        part = ConstructionGridPart(name=self.part_name)
        ax, ay = self.anchor.x, self.anchor.y
        for name, x_off in self.verticals:
            x = ax + x_off
            part.add_construction_line(
                Segment(
                    Point(x, ay - self.extent), Point(x, ay + self.extent), name=name
                ),
                style=self.style,
            )
        for name, y_off in self.horizontals:
            y = ay + y_off
            part.add_construction_line(
                Segment(
                    Point(ax - self.extent, y), Point(ax + self.extent, y), name=name
                ),
                style=self.style,
            )
        return part


class Pattern:
    """A complete sewing pattern consisting of one or more pattern parts.

    Attributes:
        name: Pattern name.
        parts: Ordered list of all :class:`PatternPart` objects.
        anchor: Top-left origin on the page. Defaults to (1.5 cm, 1.5 cm).
        reference_square: Optional scale-verification square added via
            :meth:`add_reference_square`.
    """

    def __init__(
        self,
        name: str,
        parts: list[PatternPart] | None = None,
        anchor: Point | None = None,
    ) -> None:
        self.name = name
        self.parts: list[PatternPart] = parts if parts is not None else []
        self.reference_square: PatternElement | None = None
        self.anchor: Point = anchor if anchor is not None else Point(1.5 * CM, 1.5 * CM)

    def add_reference_square(
        self,
        origin: Point,
        edge_length: float = 3 * CM,
        style: StyleOptions | None = None,
        part: PatternPart | None = None,
    ) -> PatternElement:
        """Add a print-scale verification square, clamped inside the bounding box with 2 mm padding.

        Args:
            origin: Preferred top-left corner.
            edge_length: Side length. Defaults to 3 cm.
            style: Defaults to a plain stroke style.
            part: Part for boundary clamping; auto-detected for single non-grid
                non-block parts.
        """
        from .style import DEFAULT_STROKE_WIDTH

        target_part: PatternPart | None = part
        if target_part is None:
            regular = [
                p
                for p in self.parts
                if not isinstance(p, (ConstructionGridPart, Block))
            ]
            if len(regular) == 1:
                target_part = regular[0]

        final_origin = origin
        if target_part is not None:
            bb = target_part.bounding_box()
            if bb is not None:
                mn, mx = bb
                pad = 2 * MM
                ox = max(mn.x + pad, min(origin.x, mx.x - edge_length - pad))
                oy = max(mn.y + pad, min(origin.y, mx.y - edge_length - pad))
                final_origin = Point(ox, oy)

        elem = PatternElement(
            geometry=Rect(
                origin=final_origin,
                width=edge_length,
                height=edge_length,
                name=f"{edge_length / CM:.0f}cm × {edge_length / CM:.0f}cm",
            ),
            style=(
                style
                if style is not None
                else StyleOptions(stroke_width=DEFAULT_STROKE_WIDTH)
            ),
        )
        self.reference_square = elem
        return elem

    def add_part(self, part: PatternPart) -> PatternPart:
        """Append *part* to this pattern and return it (for chaining)."""
        self.parts.append(part)
        return part

    def get_part(self, name: str) -> PatternPart:
        """Return the first PatternPart with the given name.

        Raises:
            KeyError: If no part with that name exists.
        """
        for part in self.parts:
            if part.name == name:
                return part
        raise KeyError(f"No PatternPart named {name!r}")
