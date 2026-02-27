from .style import StyleOptions, STYLE_GRAINLINE, STYLE_SEAM_ALLOWANCE
from .geometry import (
    Rect,
    Point,
    Segment,
    Circle,
    Triangle,
    InfoBox,
    CubicBezier,
    _miter_join,
    _intersect_lines,
)
from .units import CM, MM
import numpy as np


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

    @property
    def centroid(self) -> Point | None:
        """Calculate the centroid of all vertex coordinates in this part.

        Collects every coordinate from Points, Segment endpoints, Rect corners,
        and Circle centres, then returns their average. Returns None if the part
        contains no geometry yet.

        This centroid is used internally (e.g. by add_notches) to determine
        which side of a seam edge is the interior of the pattern piece.

        Returns:
            The centroid Point, or None if there are no coordinates.
        """

        coords: list[np.ndarray] = []
        for elem in self.elements:
            g = elem.geometry
            if isinstance(g, Point):
                coords.append(g.coords)
            elif isinstance(g, Segment):
                coords.append(g.p1.coords)
                coords.append(g.p2.coords)
            elif isinstance(g, Rect):
                coords.append(g.origin.coords)
                coords.append(g.origin.coords + np.array([g.width, g.height]))
            elif isinstance(g, Circle):
                coords.append(g.center.coords)
        if not coords:
            return None
        mean = np.mean(coords, axis=0)
        return Point(*mean)

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
                    if np.dot(normal, inward_ref.coords - notch_pt.coords) < 0:
                        normal = -normal
            elif isinstance(seam_edge, CubicBezier):
                # Find the parameter t that minimises distance to pt
                result = minimize_scalar(
                    lambda t: float(
                        np.linalg.norm(seam_edge.point_at_t(t).coords - pt.coords)
                    ),
                    bounds=(0.0, 1.0),
                    method="bounded",
                )
                t_closest = float(result.x)
                notch_pt = seam_edge.point_at_t(t_closest)
                tangent = seam_edge.tangent_at_t(t_closest)
                tang_len = float(np.linalg.norm(tangent))
                along = tangent / tang_len if tang_len > 1e-12 else tangent
                normal = seam_edge.normal_at_t(t_closest)
                if inward_ref is not None:
                    if np.dot(normal, inward_ref.coords - notch_pt.coords) < 0:
                        normal = -normal
            else:
                notch_pt = pt
                along = np.array([1.0, 0.0])
                normal = np.array([0.0, -1.0])

            ax, ay = along
            nx, ny = normal
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

        For each outline element (``is_outline=True`` or explicitly given via
        *outline_elements*) an offset copy is created that is shifted outward
        by *distance* mm from the interior of the part.  The interior is
        determined automatically from :attr:`centroid`.

        Successive offset segments are connected at corners using a
        **miter-join** (extended intersection); if the miter ratio is too large
        a bevel midpoint is used as fallback (see :func:`geometry._miter_join`).

        Offset :class:`~sewpat.geometry.CubicBezier` elements are approximated
        via the hodograph method (see :meth:`CubicBezier.offset`).

        Args:
            distance: Seam allowance in mm (must be positive).
            outline_elements: Optional list of :class:`PatternElement` objects
                that define the cut-line contour.  Defaults to all elements
                whose ``is_outline`` flag is ``True``.
            style: Optional :class:`~sewpat.style.StyleOptions` for the
                generated seam-allowance elements.  Defaults to
                :data:`~sewpat.style.STYLE_SEAM_ALLOWANCE`.

        Returns:
            List of the newly created :class:`PatternElement` objects.
        """
        if distance <= 0:
            raise ValueError(
                f"seam allowance distance must be positive, got {distance}"
            )

        sa_style = style if style is not None else STYLE_SEAM_ALLOWANCE
        center = self.centroid

        # --- collect outline geometry ----------------------------------------
        if outline_elements is None:
            outline_elements = [e for e in self.elements if e.is_outline]

        if not outline_elements:
            return []

        # --- helpers ---------------------------------------------------------
        def _start(g: Segment | CubicBezier) -> Point:
            return g.p1 if isinstance(g, Segment) else g.p0

        def _end(g: Segment | CubicBezier) -> Point:
            return g.p2 if isinstance(g, Segment) else g.p3

        def _reverse(g: Segment | CubicBezier) -> Segment | CubicBezier:
            """Return a copy of *g* with direction flipped."""
            if isinstance(g, Segment):
                return Segment(g.p2, g.p1, name=g.name)
            else:
                # Swap anchor endpoints AND control points so the curve shape
                # is preserved exactly.
                return CubicBezier(g.p3, g.p2, g.p1, g.p0, name=g.name)

        def _with_endpoints(
            g: Segment | CubicBezier, new_start: Point, new_end: Point
        ) -> Segment | CubicBezier:
            if isinstance(g, Segment):
                return Segment(new_start, new_end, name=g.name)
            else:
                return CubicBezier(new_start, g.p1, g.p2, new_end, name=g.name)

        # --- handle Rect special case early ----------------------------------
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

        # --- sort outline elements into a connected chain --------------------
        # Collect Segment / CubicBezier geometries only.
        geoms_raw: list[Segment | CubicBezier] = [
            elem.geometry
            for elem in outline_elements
            if isinstance(elem.geometry, (Segment, CubicBezier))
        ]

        SNAP = 0.5  # mm — tolerance for endpoint matching

        def _close(a: Point, b: Point) -> bool:
            return float(np.linalg.norm(a.coords - b.coords)) < SNAP

        # Greedy chain builder: start with the first element, then repeatedly
        # find the next piece whose start or end connects to the current tail.
        # Reverse the piece when it connects end-first so every element in the
        # chain runs start → end continuously.
        chain: list[Segment | CubicBezier] = [geoms_raw[0]]
        remaining = list(geoms_raw[1:])
        while remaining:
            tail = _end(chain[-1])
            found = False
            for i, g in enumerate(remaining):
                if _close(tail, _start(g)):
                    chain.append(g)
                    remaining.pop(i)
                    found = True
                    break
                elif _close(tail, _end(g)):
                    chain.append(_reverse(g))
                    remaining.pop(i)
                    found = True
                    break
            if not found:
                # Gap in the outline — append remaining pieces as-is
                chain.extend(remaining)
                break

        # --- offset each element in chain order ------------------------------
        offset_geoms: list[Segment | CubicBezier] = [
            g.offset(distance, center) for g in chain
        ]

        # --- miter-join corner stitching -------------------------------------
        new_geoms: list[Segment | CubicBezier] = list(offset_geoms)
        n = len(new_geoms)

        def _end_tangent(g: Segment | CubicBezier) -> np.ndarray:
            """Unit tangent at the *end* of g (pointing away from start)."""
            if isinstance(g, Segment):
                d = g.p2.coords - g.p1.coords
            else:
                d = g.tangent_at_t(1.0)
            norm = float(np.linalg.norm(d))
            return d / norm if norm > 1e-12 else d

        def _start_tangent(g: Segment | CubicBezier) -> np.ndarray:
            """Unit tangent at the *start* of g (pointing toward end)."""
            if isinstance(g, Segment):
                d = g.p2.coords - g.p1.coords
            else:
                d = g.tangent_at_t(0.0)
            norm = float(np.linalg.norm(d))
            return d / norm if norm > 1e-12 else d

        def _miter_corner(
            ga: Segment | CubicBezier,
            gb: Segment | CubicBezier,
            miter_limit: float = 4.0,
        ) -> Point:
            """Miter corner for any combination of Segment / CubicBezier.

            Extends the end-tangent of *ga* and the start-tangent of *gb* as
            infinite lines and returns their intersection.  Falls back to a
            bevel midpoint when the lines are parallel or the miter extension
            exceeds *miter_limit* × the gap between the two endpoints.
            """
            end_a = _end(ga)
            start_b = _start(gb)
            gap = float(np.linalg.norm(end_a.coords - start_b.coords))

            ta = _end_tangent(ga)  # direction leaving ga
            tb = _start_tangent(gb)  # direction entering gb

            # Normal vectors (perpendicular to tangents) for _intersect_lines
            na = np.array([-ta[1], ta[0]])
            nb = np.array([-tb[1], tb[0]])

            pt = _intersect_lines(end_a.coords, na, start_b.coords, nb)
            if pt is None:
                return Point(*(0.5 * (end_a.coords + start_b.coords)))

            miter_dist = float(np.linalg.norm(pt - end_a.coords))
            if gap > 1e-9 and miter_dist / gap > miter_limit:
                return Point(*(0.5 * (end_a.coords + start_b.coords)))

            return Point(*pt)

        if n > 1:
            for i in range(n):
                j = (i + 1) % n
                ga = new_geoms[i]
                gb = new_geoms[j]
                end_a = _end(ga)
                start_b = _start(gb)
                # Only apply miter-join when the gap is non-trivial (> 0.01 mm)
                if end_a.distance_to(start_b) > 0.01:
                    corner = _miter_corner(ga, gb)
                    new_geoms[i] = _with_endpoints(ga, _start(ga), corner)
                    new_geoms[j] = _with_endpoints(gb, corner, _end(gb))

        # --- append and return -----------------------------------------------
        added: list["PatternElement"] = []
        for geom in new_geoms:
            elem = self.append(geom, style=sa_style)
            elem.is_seam_allowance = True
            added.append(elem)
        return added


class Pattern:
    """A complete sewing pattern consisting of one or more pattern parts.

    Each part (e.g. main body, drawstring channel) can be rendered
    individually or together, making it easy to include or exclude parts.

    Attributes:
        name: Name of the pattern (e.g. "Drawstring Pouch").
        parts: Ordered list of PatternPart objects.
        anchor: Top-left origin of the pattern on the page. Defaults to (1.5cm, 1.5cm).
        reference_square: Optional PatternElement rendered on every export to
            verify print scale. Set via set_reference_square().
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

    def set_reference_square(
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
