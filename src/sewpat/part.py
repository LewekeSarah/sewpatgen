import math
import shapely.geometry as _sg

from .style import StyleOptions, STYLE_GRAINLINE, STYLE_SEAM_ALLOWANCE
from .geometry import (
    Rect,
    Point,
    Segment,
    Circle,
    Triangle,
    InfoBox,
    CubicBezier,
    geom_start,
    geom_end,
    with_endpoints,
    build_chain,
    buffer_chain,
    miter_corner,
    round_corner,
    outline_polygon,
    offset_adaptive as _offset_adaptive,
    seam_length as _geom_seam_length,
)
from .units import CM, MM


class PatternElement:
    """A pattern element combining a geometric shape with a style.

    Attributes:
        geometry: The geometric shape (Point, Segment, Rect, Circle, CubicBezier, …).
        style: Visual style for rendering this element.
        name: Optional label override. If None, the geometry's own name is used.
        is_outline: Whether this element forms part of the cut-line outline.
            Only elements with ``is_outline=True`` participate in seam-allowance
            generation via :meth:`PatternPart.add_seam_allowance`.
        is_seam_allowance: Whether this element was generated as a seam-allowance
            offset line.  Elements with this flag can be hidden by passing
            ``show_seam_allowance=False`` to the export functions.
        is_seam_notch: Whether this element is the seam-line copy of a notch
            triangle.  When a SA counterpart exists, this copy is hidden when
            ``show_seam_allowance=True`` so that only the cut-edge notch is visible.
    """

    def __init__(
        self,
        geometry: Segment | Rect | Circle | Triangle | CubicBezier | Point | InfoBox,
        style: StyleOptions | None = None,
        name: str | None = None,
        is_outline: bool = False,
        is_seam_allowance: bool = False,
    ) -> None:
        self.geometry = geometry
        self.style = style if style is not None else StyleOptions()
        self.name = name
        self.is_outline = is_outline
        self.is_seam_allowance = is_seam_allowance
        self.is_seam_notch: bool = False  # set by add_notches() when SA twin exists

    def get_name(self) -> str | None:
        """Return the effective name (element name overrides geometry name)."""
        if self.name is not None:
            return self.name
        return getattr(self.geometry, "name", None)


class PatternPart:
    """A collection of pattern elements forming one pattern piece."""

    def __init__(self, name: str, elements: list[PatternElement] | None = None) -> None:
        self.name = name
        self.elements: list[PatternElement] = elements if elements is not None else []

    def append(
        self,
        geometry: object,
        style: StyleOptions | None = None,
        name: str | None = None,
        is_outline: bool = False,
    ) -> PatternElement:
        """Create a PatternElement from geometry + style and append it to this part.

        Args:
            geometry: The geometric shape to add.
            style: Optional style for the element. Defaults to StyleOptions().
            name: Optional label override for the element.
            is_outline: Whether this element forms part of the cut-line outline.

        Returns:
            The newly created PatternElement.
        """
        elem = PatternElement(
            geometry=geometry, style=style, name=name, is_outline=is_outline
        )
        self.elements.append(elem)
        return elem

    def extend(self, elements: list[PatternElement]) -> None:
        """Append multiple PatternElements at once.

        Args:
            elements: List of PatternElement objects to add.
        """
        self.elements.extend(elements)

    def _outline_polygon(self):
        """Build a Shapely Polygon from the ``is_outline`` elements of this part."""
        geoms = [
            e.geometry
            for e in self.elements
            if e.is_outline and isinstance(e.geometry, (Segment, CubicBezier))
        ]
        return outline_polygon(geoms) if geoms else None

    @property
    def centroid(self) -> Point | None:
        """Return the true geometric centroid of the outline polygon.

        Uses Shapely to compute the exact centroid from the closed outline.
        Returns ``None`` if no ``is_outline`` elements have been added yet.
        """
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return None
        c = poly.centroid
        return Point(c.x, c.y)

    @property
    def area_cm2(self) -> float | None:
        """Return the area of the outline polygon in cm².

        Uses Shapely to compute the exact area of the closed outline polygon.
        Returns ``None`` if no outline polygon has been defined yet.

        Returns:
            Area in cm², or ``None``.
        """
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return None
        # Internal unit is mm², divide by 100 to get cm²
        return poly.area / 100.0

    def bounding_box(self) -> "tuple[Point, Point] | None":
        """Return the axis-aligned bounding box of the outline polygon.

        Uses Shapely's ``Polygon.bounds`` to compute the tightest rectangle
        that encloses all ``is_outline`` elements (including discretised
        Bézier curves).  Useful for auto-layout and page-size checks.

        Returns:
            Tuple of ``(min_point, max_point)`` in mm, or ``None`` if no
            outline polygon has been defined yet.
        """
        poly = self._outline_polygon()
        if poly is None or poly.is_empty:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return Point(minx, miny), Point(maxx, maxy)

    def seam_length(
        self,
        geoms_or_names: "list[Segment | CubicBezier | PatternElement | str]",
    ) -> float:
        """Return the total arc length (mm) of a named seam edge on this part.

        Accepts any mix of:

        * **``Segment`` / ``CubicBezier``** — geometry objects used directly.
        * **``PatternElement``** — the return value of :meth:`append`; the
          geometry is unwrapped automatically.  This is the most convenient
          form when you hold the element reference from construction time::

              elem = part.append(Segment(pt1, pt2), is_outline=True)
              part.seam_length([elem])

        * **``str``** — element name; all matching ``Segment``/``CubicBezier``
          elements in this part are summed::

              part.seam_length(["Seitennaht", "Seitensaum"])

        Mixed lists are fine.

        Typical use — compare front and back inseam before finalising::

            front_len = front.seam_length([front_inner_leg])
            back_len  = back.seam_length([back_inner_seam])
            print(f"inseam Δ = {front_len - back_len:.1f} mm")

        Args:
            geoms_or_names: Any combination of ``Segment``, ``CubicBezier``,
                ``PatternElement``, or name strings.

        Returns:
            Total arc length in mm.

        Raises:
            KeyError: If a name string does not match any element in this part.
            TypeError: If an entry is none of the accepted types.
        """
        resolved: list[Segment | CubicBezier] = []
        for item in geoms_or_names:
            if isinstance(item, PatternElement):
                if isinstance(item.geometry, (Segment, CubicBezier)):
                    resolved.append(item.geometry)
                # silently skip non-geometry elements (Points, Circles, …)
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
                        f"No Segment/CubicBezier element named {item!r} in part {self.name!r}"
                    )
                resolved.extend(matches)
            else:
                raise TypeError(
                    f"Expected Segment, CubicBezier, PatternElement, or str; "
                    f"got {type(item).__name__}"
                )
        return _geom_seam_length(resolved)

    def contains_point(self, point: Point) -> bool:
        """Return True if *point* lies inside the outline polygon.

        Uses Shapely's ``Polygon.contains()`` — points exactly on the boundary
        return False (use ``covers()`` semantics if you need boundary inclusion,
        but for pattern work strict interior is the right check).

        Useful for validating that grainline endpoints, notch positions, or
        info-box anchors actually sit inside the piece.

        Args:
            point: The point to test.

        Returns:
            True if *point* is strictly inside the outline, False otherwise or
            if no outline polygon has been defined yet.
        """
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
        """Move *point* toward *inward_ref* until :meth:`contains_point` returns True.

        Each step moves the point by *step* mm along the line toward
        *inward_ref*.  Returns the original point unchanged if it is already
        inside, if *inward_ref* equals *point*, or if no movement succeeded
        within *max_steps*.

        Args:
            point: The point to check and potentially move.
            inward_ref: Direction target (usually the midpoint of the grainline).
            step: Step size in mm for each nudge iteration. Defaults to 1 mm.
            max_steps: Minimum iteration cap; the actual number of steps is
                at least ``ceil(dist / step) + 1`` so the full line is always
                walked. Defaults to 200.

        Returns:
            A Point that is inside the outline polygon, or the original if no
            movement was possible within *max_steps*.
        """
        if self.contains_point(point):
            return point

        dx = inward_ref.x - point.x
        dy = inward_ref.y - point.y
        dist = (dx**2 + dy**2) ** 0.5
        if dist < 1e-9:
            return point
        ux, uy = dx / dist, dy / dist

        steps = max(max_steps, math.ceil(dist / step) + 1)
        for i in range(1, steps + 1):
            candidate = Point(point.x + ux * step * i, point.y + uy * step * i)
            if self.contains_point(candidate):
                return candidate

        return point

    def add_grainline(
        self,
        start: Point,
        end: Point,
        name: str = "grainline / Fadenlauf",
    ) -> PatternElement:
        """Add a grainline to this pattern part.

        Before adding the grainline, both endpoints are checked against the
        outline polygon via :meth:`contains_point`.  If either point lies
        outside the polygon, it is nudged inward along the grainline direction
        in 1 mm steps until it is strictly inside.  This requires that at
        least some ``is_outline`` elements have been appended before calling
        this method.

        The grainline is optional — not every part requires one.

        Args:
            start: Start point of the grainline (arrow end).
            end: End point of the grainline.
            name: Label for the grainline. Defaults to "grainline / Fadenlauf".

        Returns:
            The created PatternElement.
        """
        mid = Point((start.x + end.x) / 2, (start.y + end.y) / 2)
        start = self._nudge_point_inside(start, mid)
        end = self._nudge_point_inside(end, mid)

        return self.append(Segment(start, end, name=name), style=STYLE_GRAINLINE)

    def add_info_box(
        self, header: str | None = None, notes: list[str] | None = None
    ) -> PatternElement | None:
        """Add an info box at the centroid of this pattern part.

        The info box displays the part name as a bold header and optional
        notes below it (e.g. seam allowance, fabric type).

        Must be called after geometry has been added so the centroid is defined.

        Args:
            header: Header text. Defaults to the part name.
            notes: Optional list of note lines shown below the header.

        Returns:
            The created PatternElement, or None if no centroid exists yet.
        """
        pos = self.centroid
        if pos is None:
            return None
        return self.append(
            InfoBox(
                position=pos,
                header=header if header is not None else self.name,
                notes=notes,
            )
        )

    def add_precision_points(self, *centers: Point) -> None:
        """Add a precision point mark (two concentric circles) for each given center.

        Used to mark exact positions on a pattern piece for accurate cutting or
        alignment, e.g. notch points or fold corners.

        Args:
            *centers: One or more points to mark.
        """
        for center in centers:
            self.append(Circle(center, radius=2 * MM))
            self.append(Circle(center, radius=0.2 * MM))

    def add_notches(
        self,
        *points: Point,
        seam_edge: Segment | CubicBezier | None = None,
        length: float = 0.8 * CM,
        width: float = 0.4 * CM,
        is_back: bool = False,
    ) -> None:
        """Add notch marks at the given points, always facing inward.

        Notches are small filled triangles standing on the seam edge and
        pointing inward (toward the fabric), as per standard sewing pattern
        conventions.

        A **single** triangle marks a front seam edge; **two** neighbouring
        triangles mark a back seam edge (``is_back=True``), following the
        standard sewing-pattern reading guide.

        If ``seam_edge`` is a :class:`~sewpat.geometry.Segment`, each point is
        projected orthogonally onto it.  If ``seam_edge`` is a
        :class:`~sewpat.geometry.CubicBezier`, the closest point on the curve
        is found numerically and the curve's tangent/normal at that point are
        used.  Without ``seam_edge``, a vertical triangle centred on the point
        is used.

        **Automatic SA projection:** when seam-allowance elements are already
        present on the part (added via :meth:`add_seam_allowance`), two
        triangles are generated per notch:

        * one on the **seam line** (``is_seam_allowance=False``) — shown when
          the pattern is exported without SA (``show_seam_allowance=False``).
        * one on the **cut edge** (``is_seam_allowance=True``) — shown when
          the pattern is exported with SA (``show_seam_allowance=True``).

        This means :meth:`add_notches` must be called **after**
        :meth:`add_seam_allowance` if SA projection is desired; calling it
        before produces only the seam-line triangle (no warning is raised).

        Args:
            *points: One or more reference points for the notches.
            seam_edge: Segment or CubicBezier (seam line) used to project the
                notch position and derive the tangent/normal direction.
            length: Distance from base to tip of the triangle. Defaults to 0.8 cm.
            width: Width of the triangle base on the seam edge. Defaults to 0.4 cm.
            is_back: If True, render two neighbouring triangles instead of one
                to indicate a back pattern piece. Defaults to False.
        """
        from scipy.optimize import minimize_scalar

        inward_ref = self.centroid
        half_w = width / 2
        gap = width * 0.5

        # Collect SA geometries (present when add_seam_allowance was called first).
        sa_geoms: list[Segment | CubicBezier] = [
            e.geometry
            for e in self.elements
            if e.is_seam_allowance and isinstance(e.geometry, (Segment, CubicBezier))
        ]

        def _project(edge: Segment | CubicBezier, ref: Point) -> tuple:
            """Return (notch_pt, along, inward_normal) for *edge* closest to *ref*."""
            if isinstance(edge, Segment):
                notch_pt = edge.project_point(ref)
                along = edge.unit_direction
                normal = edge.unit_normal
            else:
                res = minimize_scalar(
                    lambda t, _e=edge: _e.point_at_t(t).distance_to(ref),
                    bounds=(0.0, 1.0),
                    method="bounded",
                )
                t_c = float(res.x)
                notch_pt = edge.point_at_t(t_c)
                tangent = edge.tangent_at_t(t_c)
                tang_len = float((tangent[0] ** 2 + tangent[1] ** 2) ** 0.5)
                along = tangent / tang_len if tang_len > 1e-12 else tangent
                normal = edge.normal_at_t(t_c)
            if inward_ref is not None:
                dot = normal[0] * (inward_ref.x - notch_pt.x) + normal[1] * (
                    inward_ref.y - notch_pt.y
                )
                if dot < 0:
                    normal = -normal
            return notch_pt, along, normal

        def _closest_sa_edge(ref: Point) -> Segment | CubicBezier | None:
            """Return the SA element whose closest point is nearest to *ref*."""
            best_edge: Segment | CubicBezier | None = None
            best_dist = float("inf")
            for g in sa_geoms:
                if isinstance(g, Segment):
                    proj = g.project_point(ref)
                    t = float(
                        (proj.x - g.p1.x) * (g.p2.x - g.p1.x)
                        + (proj.y - g.p1.y) * (g.p2.y - g.p1.y)
                    ) / max(g.length**2, 1e-12)
                    t = max(0.0, min(1.0, t))
                    d = ref.distance_to(g.point_at_t(t))
                else:
                    res = minimize_scalar(
                        lambda t, _g=g: _g.point_at_t(t).distance_to(ref),
                        bounds=(0.0, 1.0),
                        method="bounded",
                    )
                    d = float(res.fun)
                if d < best_dist:
                    best_dist = d
                    best_edge = g
            return best_edge

        def _place_triangles(notch_pt: Point, along, normal, is_sa: bool) -> list:
            ax, ay = float(along[0]), float(along[1])
            nx, ny = float(normal[0]), float(normal[1])
            offsets = (
                [0.0] if not is_back else [-(half_w + gap / 2), +(half_w + gap / 2)]
            )
            created = []
            for offset in offsets:
                centre = notch_pt.translate(offset * ax, offset * ay)
                bl = centre.translate(-half_w * ax, -half_w * ay)
                br = centre.translate(half_w * ax, half_w * ay)
                tip = centre.translate(nx * length, ny * length)
                elem = self.append(Triangle(bl, br, tip))
                elem.is_seam_allowance = is_sa
                created.append(elem)
            return created

        for pt in points:
            # ── Seam-line notch (always) ──────────────────────────────────
            if seam_edge is not None:
                notch_pt, along, normal = _project(seam_edge, pt)
            else:
                notch_pt = pt
                along = (1.0, 0.0)
                normal = (0.0, -1.0)
            seam_elems = _place_triangles(notch_pt, along, normal, is_sa=False)

            # ── SA-line notch (only when SA elements exist) ───────────────
            if sa_geoms:
                seam_proj = notch_pt  # already projected onto seam line
                sa_edge = _closest_sa_edge(seam_proj)
                if sa_edge is not None:
                    sa_notch_pt, sa_along, sa_normal = _project(sa_edge, seam_proj)
                    _place_triangles(sa_notch_pt, sa_along, sa_normal, is_sa=True)
                    # Hide the seam-line copy when SA is shown — the cut-edge
                    # notch takes over.
                    for e in seam_elems:
                        e.is_seam_notch = True

    def add_seam_allowance(
        self,
        distance: float,
        outline_elements: list[PatternElement] | None = None,
        style: StyleOptions | None = None,
        corner_join: str = "miter",
    ) -> list[PatternElement]:
        """Add seam-allowance lines around the outline of this pattern part.

        - :class:`~sewpat.geometry.Rect` outlines are expanded uniformly.
        - Pure-segment outlines use a Shapely ``Polygon.buffer()`` (GEOS
          join, limit 4.0) — robust and concave-safe.
        - Mixed or Bézier outlines offset each element individually via
          :meth:`~sewpat.geometry.CubicBezier.offset` /
          :meth:`~sewpat.geometry.Segment.offset` and stitch corners with a
          tangent-miter join.

        Args:
            distance: Seam allowance in mm (must be positive).
            outline_elements: Elements forming the cut-line contour. Defaults
                to all elements whose ``is_outline`` flag is ``True``.
            style: Style for the generated elements. Defaults to
                :data:`~sewpat.style.STYLE_SEAM_ALLOWANCE`.
            corner_join: Corner join style for the offset path.  One of
                ``"miter"`` (default), ``"round"``, or ``"bevel"``.

                * ``"miter"`` — tangent-line intersection clamped by a miter
                  limit of 4 × *distance*; reflex (concave) corners fall back
                  to bevel automatically.
                * ``"round"`` — circular arc at outside corners.  Pure-segment
                  paths use Shapely's arc approximation; mixed/Bézier paths
                  insert a cubic Bézier arc (k = 4/3 · tan θ/4, max error
                  < 0.027 % of arc radius).  Reflex corners fall back to bevel.
                * ``"bevel"`` — straight cut across every corner.

        Returns:
            List of the newly created :class:`PatternElement` objects.
        """
        _CORNER_JOIN_STYLES = {"miter": 2, "round": 1, "bevel": 3}
        if corner_join not in _CORNER_JOIN_STYLES:
            raise ValueError(
                f"corner_join must be one of {list(_CORNER_JOIN_STYLES)!r}, "
                f"got {corner_join!r}"
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

        # ── collect Segment / CubicBezier geometries ──────────────────────────
        geoms: list[Segment | CubicBezier] = [
            e.geometry
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
        ]

        # ── Pure-segment path: delegate entirely to Shapely ───────────────────
        # Only use the uniform Shapely buffer when there are no Béziers AND no
        # per-element SA overrides AND no per-element corner_join overrides.
        # If any element carries its own seam_allowance or corner_join, fall
        # through to the mixed path which can honour them per-corner.
        has_per_elem_sa = any(
            getattr(e.style, "seam_allowance", 0.0) > 0
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
            buf_coords = buffer_chain(
                chain,
                distance,
                join_style=_CORNER_JOIN_STYLES[corner_join],
            )
            added: list["PatternElement"] = []
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

        # Build a lookup: endpoint-pair → per-element SA distance / corner_join.
        # Keying by frozenset of (start, end) coords means a segment that
        # build_chain reversed still matches its original style entry.
        def _ep_key(g: Segment | CubicBezier) -> frozenset:
            s, e = geom_start(g), geom_end(g)
            return frozenset(
                [(round(s.x, 6), round(s.y, 6)), (round(e.x, 6), round(e.y, 6))]
            )

        elem_sa: dict[frozenset, float] = {
            _ep_key(e.geometry): getattr(e.style, "seam_allowance", 0.0)
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
            and getattr(e.style, "seam_allowance", 0.0) > 0
        }

        # Per-element corner_join: one value per element, applies to both its corners.
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

        # Offset each element adaptively (1 original → 1..n sub-segments).
        # offset_groups[i] is the list of offset sub-segments for chain_mixed[i].
        offset_groups: list[list[Segment | CubicBezier]] = [
            _offset_adaptive(g, elem_sa.get(_ep_key(g), distance), center)
            for g in chain_mixed
        ]

        # Stitch corners between consecutive original elements.
        # Only the LAST sub-segment of group i and the FIRST sub-segment of
        # group i+1 need a corner join — the sub-segments within one group are
        # already connected by construction (split endpoints touch).
        n = len(offset_groups)
        arc_inserts: list[tuple[int, int, CubicBezier]] = []  # (group_i, CubicBezier)
        for i in range(n):
            j = (i + 1) % n
            ga = offset_groups[i][-1]  # last sub-seg of group i
            gb = offset_groups[j][0]  # first sub-seg of group j
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
                        corner = arc
                        offset_groups[i][-1] = with_endpoints(
                            ga, geom_start(ga), corner
                        )
                        offset_groups[j][0] = with_endpoints(gb, corner, geom_end(gb))
                else:  # bevel
                    _ea = geom_end(ga)
                    _sb = geom_start(gb)
                    corner = Point(*(0.5 * (_ea.coords + _sb.coords)))
                    offset_groups[i][-1] = with_endpoints(ga, geom_start(ga), corner)
                    offset_groups[j][0] = with_endpoints(gb, corner, geom_end(gb))

        # Flatten groups into a single ordered list, inserting round-corner arcs
        # after their group (in reverse order to keep indices stable).
        flat: list[Segment | CubicBezier] = []
        for i, group in enumerate(offset_groups):
            flat.extend(group)
        # arc_inserts: insert arc after the last element of group i.
        # Compute flat indices of "end of group i".
        group_end_flat: list[int] = []
        pos = 0
        for group in offset_groups:
            pos += len(group)
            group_end_flat.append(pos - 1)
        for group_i, arc in sorted(arc_inserts, key=lambda x: x[0], reverse=True):
            flat.insert(group_end_flat[group_i] + 1, arc)

        added_mixed: list["PatternElement"] = []
        for geom in flat:
            elem = self.append(geom, style=sa_style)
            elem.is_seam_allowance = True
            added_mixed.append(elem)
        return added_mixed


class Pattern:
    """A complete sewing pattern consisting of one or more pattern parts.

    Each part (e.g. main body, drawstring channel) can be rendered
    individually or together, making it easy to include or exclude parts.

    Attributes:
        name: Name of the pattern (e.g. "Drawstring Pouch").
        parts: Ordered list of PatternPart objects.
        anchor: Top-left origin of the pattern on the page. Defaults to (1.5cm, 1.5cm).
        reference_square: Optional PatternElement rendered on every export to
            verify print scale. Set via add_reference_square().
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
        """Set a reference square for print-scale verification.

        The square is rendered on every SVG export independently of which
        parts are selected.

        If *part* is supplied (or the pattern has exactly one part) and the
        square would fall outside that part's bounding box, the origin is
        shifted so that the square fits snugly inside the bounding box with a
        small padding.  This avoids the square being printed in empty space
        when the pattern is positioned away from the page origin.

        Args:
            origin: Preferred top-left corner of the square.
            edge_length: Side length of the square. Defaults to 3 cm.
            style: Optional style override. Defaults to StyleOptions().
            part: Optional PatternPart used for auto-placement.  When omitted
                and the pattern contains exactly one part, that part is used
                automatically.

        Returns:
            The created PatternElement.
        """
        from .style import DEFAULT_STROKE_WIDTH

        # Resolve which part to use for boundary checking
        target_part: PatternPart | None = part
        if target_part is None and len(self.parts) == 1:
            target_part = self.parts[0]

        final_origin = origin
        if target_part is not None:
            bb = target_part.bounding_box()
            if bb is not None:
                mn, mx = bb
                pad = 2 * MM  # small gap from the boundary
                ox, oy = origin.x, origin.y
                # Clamp so the square stays within [mn+pad, mx-edge_length-pad]
                ox = max(mn.x + pad, min(ox, mx.x - edge_length - pad))
                oy = max(mn.y + pad, min(oy, mx.y - edge_length - pad))
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
        """Append a PatternPart to this pattern.

        Args:
            part: The PatternPart to add.

        Returns:
            The added PatternPart (for chaining).
        """
        self.parts.append(part)
        return part

    def get_part(self, name: str) -> PatternPart:
        """Return the first PatternPart with the given name.

        Args:
            name: Name of the part to find.

        Raises:
            KeyError: If no part with that name exists.
        """
        for part in self.parts:
            if part.name == name:
                return part
        raise KeyError(f"No PatternPart named {name!r}")
