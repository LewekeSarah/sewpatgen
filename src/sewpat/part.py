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
    outline_polygon,
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
    """

    def __init__(
        self,
        geometry: object,
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

    def add_grainline(
        self,
        start: Point,
        end: Point,
        name: str = "grainline / Fadenlauf",
    ) -> PatternElement:
        """Add a grainline to this pattern part.

        The grainline is optional — not every part requires one.

        Args:
            start: Start point of the grainline (arrow end).
            end: End point of the grainline.
            name: Label for the grainline. Defaults to "grainline / Fadenlauf".

        Returns:
            The created PatternElement.
        """
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

        Args:
            *points: One or more reference points for the notches.
            seam_edge: Segment or CubicBezier (seam edge) on which the notches
                stand.
            length: Distance from base to tip of the triangle. Defaults to 0.8 cm.
            width: Width of the triangle base on the seam edge. Defaults to 0.4 cm.
            is_back: If True, render two neighbouring triangles instead of one
                to indicate a back pattern piece. Defaults to False.
        """
        from scipy.optimize import minimize_scalar

        inward_ref = self.centroid
        half_w = width / 2
        gap = width * 0.5

        for pt in points:
            if isinstance(seam_edge, Segment):
                notch_pt = seam_edge.project_point(pt)
                along = seam_edge.unit_direction
                normal = seam_edge.unit_normal
                if inward_ref is not None:
                    dot = normal[0] * (inward_ref.x - notch_pt.x) + normal[1] * (
                        inward_ref.y - notch_pt.y
                    )
                    if dot < 0:
                        normal = -normal
            elif isinstance(seam_edge, CubicBezier):
                result = minimize_scalar(
                    lambda t: seam_edge.point_at_t(t).distance_to(pt),
                    bounds=(0.0, 1.0),
                    method="bounded",
                )
                t_closest = float(result.x)
                notch_pt = seam_edge.point_at_t(t_closest)
                tangent = seam_edge.tangent_at_t(t_closest)
                tang_len = float((tangent[0] ** 2 + tangent[1] ** 2) ** 0.5)
                along = tangent / tang_len if tang_len > 1e-12 else tangent
                normal = seam_edge.normal_at_t(t_closest)
                if inward_ref is not None:
                    dot = normal[0] * (inward_ref.x - notch_pt.x) + normal[1] * (
                        inward_ref.y - notch_pt.y
                    )
                    if dot < 0:
                        normal = -normal
            else:
                notch_pt = pt
                along = (1.0, 0.0)
                normal = (0.0, -1.0)

            ax, ay = float(along[0]), float(along[1])
            nx, ny = float(normal[0]), float(normal[1])
            offsets = [0.0]
            if is_back:
                offsets = [-(half_w + gap / 2), +(half_w + gap / 2)]

            for offset in offsets:
                centre = notch_pt.translate(offset * ax, offset * ay)
                bl = centre.translate(-half_w * ax, -half_w * ay)
                br = centre.translate(half_w * ax, half_w * ay)
                tip = centre.translate(nx * length, ny * length)
                self.append(Triangle(bl, br, tip))

    def add_seam_allowance(
        self,
        distance: float,
        outline_elements: list["PatternElement"] | None = None,
        style: "StyleOptions | None" = None,
    ) -> list["PatternElement"]:
        """Add seam-allowance lines around the outline of this pattern part.

        - :class:`~sewpat.geometry.Rect` outlines are expanded uniformly.
        - Pure-segment outlines use a Shapely ``Polygon.buffer()`` (GEOS
          Miter-join, limit 4.0) — robust and concave-safe.
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

        Returns:
            List of the newly created :class:`PatternElement` objects.
        """
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
        if not any(isinstance(g, CubicBezier) for g in geoms):
            chain = build_chain(geoms)
            buf_coords = buffer_chain(chain, distance)
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
        elem_sa = {
            id(e.geometry): getattr(e.style, "seam_allowance", 0.0)
            for e in outline_elements
            if isinstance(e.geometry, (Segment, CubicBezier))
            and getattr(e.style, "seam_allowance", 0.0) > 0
        }
        offset_geoms = [
            g.offset(elem_sa.get(id(g), distance), center) for g in chain_mixed
        ]
        n = len(offset_geoms)
        for i in range(n):
            j = (i + 1) % n
            ga, gb = offset_geoms[i], offset_geoms[j]
            if geom_end(ga).distance_to(geom_start(gb)) > 0.01:
                corner = miter_corner(ga, gb, distance)
                offset_geoms[i] = with_endpoints(ga, geom_start(ga), corner)
                offset_geoms[j] = with_endpoints(gb, corner, geom_end(gb))
        added_mixed: list["PatternElement"] = []
        for geom in offset_geoms:
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
    ) -> PatternElement:
        """Set a reference square for print-scale verification.

        The square is rendered on every SVG export independently of which
        parts are selected.

        Args:
            origin: Top-left corner of the square.
            edge_length: Side length of the square. Defaults to 3 cm.
            style: Optional style override. Defaults to StyleOptions().

        Returns:
            The created PatternElement.
        """
        from .style import DEFAULT_STROKE_WIDTH

        elem = PatternElement(
            geometry=Rect(
                origin=origin,
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
