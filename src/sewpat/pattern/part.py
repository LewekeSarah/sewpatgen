"""Pattern parts — collections of :class:`~sewpat.element.PatternElement` objects.

This module owns:

* :class:`PatternPart` — a single pattern piece (a named list of elements).
* :class:`Block` — a base-block pattern piece.
* :class:`OverlayPart` — a piece drafted on top of a parent part.
* :class:`Pattern` — a complete sewing pattern (collection of parts).

:class:`ConstructionGridPart` and :class:`ConstructionGrid` live in
:mod:`sewpat.pattern.construction`.
"""

import copy
from dataclasses import dataclass
from enum import StrEnum

import shapely.geometry as _sg

from ..element import GeometryType, PatternElement, PrecisionPoint
from ..geometry import (
    Circle,
    CubicBezier,
    Dart,
    InfoBox,
    Point,
    Rect,
    Segment,
    Triangle,
    outline_polygon,
)
from ..geometry import (
    seam_length as _geom_seam_length,
)
from ..style import (
    STYLE_CONSTRUCTION_GRID,
    STYLE_DART_FOLD,
    STYLE_GRAINLINE,
    STYLE_PRECISION_POINT,
    StyleOptions,
)
from ..units import CM, MM


@dataclass
class PatternConfig:
    """Layout configuration for a pattern: anchor point and inter-piece margin."""

    anchor: Point = Point(5 * CM, 5 * CM, "anchor")
    margin: float = 15 * CM


class GarmentPart(StrEnum):
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
        """Look up a PatternElement by snake_case name (e.g. ``part.center_back``)."""
        # Avoid infinite recursion for dunder / private attributes.
        if snake.startswith("_"):
            raise AttributeError(snake)
        key = snake.replace("_", " ").title()
        for e in self.elements:
            if e.get_name() == key:
                return e
        raise AttributeError(
            f"{type(self).__name__!r} has no element named {key!r} (looked up as {snake!r})"
        )


class PatternPart(NamedAccessMixin):
    """A collection of pattern elements forming one pattern piece."""

    def __init__(
        self,
        name: str,
        elements: list[PatternElement] | None = None,
        is_construction: bool = False,
    ) -> None:
        """Initialise a PatternPart.

        Args:
            name: Human-readable label for this piece.
            elements: Initial list of elements; defaults to an empty list.
            is_construction: When ``True`` every appended element is stamped
                ``is_construction=True`` automatically.
        """
        self.name = name
        self.elements: list[PatternElement] = elements if elements is not None else []
        self.is_construction: bool = is_construction

    def append(
        self,
        geometry: GeometryType,
        style: StyleOptions | None = None,
        is_outline: bool = False,
        is_construction: bool = False,
        role: str | None = None,
    ) -> PatternElement:
        """Wrap *geometry* in a PatternElement, stamp ``is_construction``, and append it.

        The element's name is taken from ``geometry.name``; set it on the
        geometry object before calling (e.g. ``seg.set_name("Center Back")``).
        Style defaulting (including the automatic ``STYLE_CONSTRUCTION_GRID``
        for construction elements with no explicit style) is handled by
        :class:`~sewpat.element.PatternElement` itself.

        Args:
            geometry: The shape to wrap.
            style: Visual style.  Defaults to ``STYLE_CONSTRUCTION_GRID`` when
                ``is_construction=True`` and no style is given, or plain
                ``StyleOptions()`` otherwise — both via ``PatternElement``.
            is_outline: Whether this element contributes to the seam-allowance
                polygon.
            is_construction: Mark as a drafting aid (hidden on final print).
                Automatically ``True`` when the part itself is
                ``is_construction=True``.
            role: Optional semantic tag (e.g. ``"side"``, ``"neckline"``).
                Used by :meth:`add_grid_notches` when a *role_map* is supplied
                to select which grid lines should produce notches on this edge.
        """
        construction = is_construction or self.is_construction
        elem = PatternElement(
            geometry=geometry,
            style=style,
            is_outline=is_outline,
            is_construction=construction,
            role=role,
            name=getattr(geometry, "name", None),
        )
        self.elements.append(elem)
        return elem

    def _stamp_construction(self, elem: PatternElement) -> None:
        """Stamp ``is_construction`` from this part onto *elem* and apply default style.

        Called internally by :meth:`extend` and :meth:`append_split_at_dart`
        for already-constructed :class:`PatternElement` objects whose ``role``,
        ``is_outline``, and other flags must be preserved.
        """
        elem.is_construction = elem.is_construction or self.is_construction
        if elem.is_construction and elem.style == StyleOptions():
            elem.style = STYLE_CONSTRUCTION_GRID

    def extend(self, elements: list[PatternElement]) -> None:
        """Append multiple ``PatternElement`` objects, stamping ``is_construction`` from this part.

        When a :class:`PatternElement` wraps a :class:`~sewpat.geometry.Dart`
        as its geometry, it is dispatched to :meth:`add_dart` using the
        element's ``style`` as ``stitch_style``; all other dart options keep
        their defaults.  Use :meth:`add_dart` directly when you need full
        control over fold style, notches, etc.

        All other :class:`PatternElement` objects are appended as-is after
        stamping ``is_construction``. Construction elements with no explicit
        style receive :data:`~sewpat.style.STYLE_CONSTRUCTION_GRID` automatically.
        """
        for elem in elements:
            if isinstance(elem.geometry, Dart):
                self.add_dart(elem.geometry, stitch_style=elem.style)
            else:
                self._stamp_construction(elem)
                self.elements.append(elem)

    def _outline_polygon(self) -> _sg.Polygon | None:
        """Build a Shapely Polygon from the ``is_outline`` elements of this part.

        Only :class:`~sewpat.geometry.Segment` and
        :class:`~sewpat.geometry.CubicBezier` elements are collected — these
        are the only types that form connected, chainable seam paths.
        Other geometry types (``Triangle`` notch markers, ``Circle`` precision
        marks, ``Rect`` reference squares) may carry ``is_outline=True`` for
        their own rendering purposes but cannot contribute to a closed polygon
        boundary.

        Dart roof segments are plain :class:`~sewpat.geometry.Segment` objects
        with ``is_outline=True`` (set by :func:`~sewpat.pattern._dart_integration.add_dart`)
        and **are** therefore included here automatically.
        """
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
        return float(poly.area) / 100.0

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
        elements: list[PatternElement | str],
    ) -> float:
        """Return the total arc length in mm of the given pattern elements.

        Each entry may be a :class:`~sewpat.element.PatternElement` or a
        ``str`` name.  When a name is given, all matching elements in this
        part are summed.

        The following geometry types contribute their length:

        * :class:`~sewpat.geometry.Segment` — Euclidean distance between
          endpoints.
        * :class:`~sewpat.geometry.CubicBezier` — arc length via numerical
          integration.
        * :class:`~sewpat.geometry.Circle` — full circumference
          (``2 * π * radius``).
        * :class:`~sewpat.geometry.Rect` — full perimeter
          (``2 * (width + height)``).
        * :class:`~sewpat.geometry.Triangle` — full perimeter (sum of three
          sides).

        Geometry types with no meaningful length
        (:class:`~sewpat.geometry.Point`, :class:`~sewpat.geometry.InfoBox`,
        :class:`~sewpat.geometry.Dart`, :class:`~sewpat.geometry.Ray`,
        :class:`~sewpat.geometry.Line`) are silently skipped.

        Args:
            elements: A list of :class:`~sewpat.element.PatternElement`
                objects or element name strings.

        Returns:
            Total arc length in mm as a :class:`float`.

        Raises:
            KeyError: If a name string matches no element in this part.
            TypeError: If an entry is not a :class:`~sewpat.element.PatternElement`
                or ``str``.
        """
        _measurable = (Segment, CubicBezier, Circle, Rect, Triangle)
        resolved: list[Segment | CubicBezier | Circle | Rect | Triangle] = []
        for item in elements:
            if isinstance(item, PatternElement):
                if isinstance(item.geometry, _measurable):
                    resolved.append(item.geometry)
                # else: silently skip unmeasurable geometry (Point, InfoBox, …)
            elif isinstance(item, str):
                matches = [
                    e.geometry
                    for e in self.elements
                    if e.get_name() == item and isinstance(e.geometry, _measurable)
                ]
                if not matches:
                    raise KeyError(f"No measurable element named {item!r} in part {self.name!r}")
                resolved.extend(matches)
            else:
                raise TypeError(f"Expected PatternElement or str; got {type(item).__name__}")
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
            start: Start point of the grainline.
            end: End point of the grainline.
            name: Label for the segment. Defaults to ``"grainline / Fadenlauf"``.
            style: Optional style override; defaults to :data:`STYLE_GRAINLINE`.

        Returns:
            The newly created :class:`PatternElement`.
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

    # ── Delegating wrappers ────────────────────────────────────────────────

    def add_notches(
        self,
        *points: Point,
        seam_edge: Segment | CubicBezier | None = None,
        length: float = 0.8 * CM,
        width: float = 0.4 * CM,
        is_back: bool = False,
    ) -> None:
        """Add filled-triangle notch marks at *points*, always pointing inward.

        Delegates to :func:`sewpat.pattern._notches.add_notches`.
        See that function for full parameter documentation.
        """
        from . import _notches

        _notches.add_notches(
            self,
            *points,
            seam_edge=seam_edge,
            length=length,
            width=width,
            is_back=is_back,
        )

    def add_seam_allowance(
        self,
        distance: float,
        outline_elements: list[PatternElement] | None = None,
        style: StyleOptions | None = None,
        corner_join: str = "miter",
    ) -> list[PatternElement]:
        """Offset the outline outward by *distance* mm and add the result as SA elements.

        Delegates to :func:`sewpat.pattern._sa.add_seam_allowance`.
        See that function for full parameter documentation.
        """
        from . import _sa

        return _sa.add_seam_allowance(
            self,
            distance,
            outline_elements=outline_elements,
            style=style,
            corner_join=corner_join,
        )

    def add_dart(
        self,
        dart: Dart,
        *,
        stitch_style: StyleOptions | None = None,
        fold_style: StyleOptions = STYLE_DART_FOLD,
        precision_style: StyleOptions = STYLE_PRECISION_POINT,
        notches: bool = True,
        precision_tip: bool = True,
        notch_length: float | None = None,
        notch_width: float | None = None,
    ) -> None:
        """Add all visual elements for *dart* to this part.

        Delegates to :func:`sewpat.pattern._dart_integration.add_dart`;
        see that function for full documentation.

        All created elements are appended to ``self.elements`` and can be
        filtered by ``element.role``: ``"dart_stitch"``, ``"dart_fold"``,
        ``"dart_roof"``, ``"dart_tip"``, ``"dart_notch"``.

        Style overrides (*stitch_style*, *fold_style*, *precision_style*) and
        notch geometry (*notch_length*, *notch_width*) are forwarded unchanged.
        Pass *notches=False* to suppress notch triangles (triangle darts only)
        or *precision_tip=False* to suppress tip circles and labels.
        """
        from . import _dart_integration

        kwargs: dict = {}
        if notch_length is not None:
            kwargs["notch_length"] = notch_length
        if notch_width is not None:
            kwargs["notch_width"] = notch_width

        return _dart_integration.add_dart(
            self,
            dart,
            stitch_style=stitch_style,
            fold_style=fold_style,
            precision_style=precision_style,
            notches=notches,
            precision_tip=precision_tip,
            **kwargs,
        )

    def add_grid_notches(
        self,
        grid_part: PatternPart,
        role_map: dict[str, list[str]],
        tolerance: float = 1.0,
        corner_clearance: float = 15.0,
        min_spacing: float = 8.0,
        length: float = 0.8 * CM,
        width: float = 0.4 * CM,
        is_back: bool = False,
    ) -> list[PatternElement]:
        """Add notches where outline edges intersect construction lines.

        Only elements whose ``role`` attribute appears as a key in *role_map*
        are considered.  For each role the mapped grid-line names are resolved
        from *grid_part* and intersected with the role's outline edges.  Corner
        clearance is applied only at boundary vertices where a role's edges
        meet edges of a different (or absent) role.

        Delegates to :func:`sewpat.pattern._notches.add_grid_notches`.
        See that function for full parameter documentation.
        """
        from . import _notches

        return _notches.add_grid_notches(
            self,
            grid_part,
            role_map=role_map,
            tolerance=tolerance,
            corner_clearance=corner_clearance,
            min_spacing=min_spacing,
            length=length,
            width=width,
            is_back=is_back,
        )

    def add_construction_line(
        self,
        geometry: GeometryType,
        name: str | None = None,
        style: StyleOptions | None = None,
    ) -> PatternElement:
        """Append any geometry as a construction element (never ``is_outline``).

        Accepts any geometry type — :class:`~sewpat.geometry.Segment`,
        :class:`~sewpat.geometry.CubicBezier`, :class:`~sewpat.geometry.Line`,
        :class:`~sewpat.geometry.Ray`, :class:`~sewpat.geometry.Point`, etc.
        The element is always stamped ``is_construction=True`` regardless of
        whether the host part is a
        :class:`~sewpat.pattern.ConstructionGridPart` or a plain
        :class:`PatternPart`.

        *name* is applied directly to *geometry* via ``set_name`` (or
        ``geometry.name`` for immutable types like :class:`~sewpat.geometry.Point`)
        so it becomes the single source of truth and can be retrieved later
        via :meth:`get_element`.

        Args:
            geometry: Any geometry object to add as a construction element.
            name: Optional label applied to *geometry* before appending.
            style: Defaults to :data:`~sewpat.style.STYLE_CONSTRUCTION_GRID`.

        Returns:
            The newly created :class:`PatternElement`.
        """
        if name is not None:
            if hasattr(geometry, "set_name"):
                geometry = geometry.set_name(name)
            else:
                geometry.name = name  # type: ignore[misc]
        return self.append(
            geometry,
            style=style if style is not None else STYLE_CONSTRUCTION_GRID,
            is_construction=True,
        )

    def append_split_at_dart(
        self,
        element: PatternElement,
        dart: Dart,
    ) -> list[PatternElement]:
        """Split *element* at both dart legs and append only the outer parts.

        This is the standard pattern-making operation of *removing the dart
        mouth from a seam edge*: the section of the edge between
        ``dart.leg_a`` and ``dart.leg_b`` is discarded, while the parts
        outside the dart mouth are appended to this part.

        All properties of *element* — ``style``, ``is_outline``,
        ``is_construction``, ``role``, ``name`` — are inherited by every
        resulting sub-element.  There is no need to pass a style separately;
        simply construct *element* as you would any other outline element and
        hand it here instead of calling :meth:`append`::

            sleeve_elem = PatternElement(
                sleeve_back.set_name("Sleeve Back"),
                style=STYLE_STITCH, is_outline=True,
            )
            block_back.append_split_at_dart(sleeve_elem, shoulder_dart_back)

        The method delegates all splitting logic to
        :meth:`PatternElement.split_at_dart`.

        Args:
            element: Source element whose geometry is split.  Must wrap a
                :class:`~sewpat.geometry.Segment` or
                :class:`~sewpat.geometry.CubicBezier`.
            dart: :class:`~sewpat.geometry.Dart` whose ``leg_a`` / ``leg_b``
                define the mouth cut points.

        Returns:
            The list of newly appended :class:`PatternElement` objects
            (one or two, depending on where the legs fall).

        Raises:
            TypeError: Propagated from :meth:`PatternElement.split_at_dart`
                when the geometry type does not support splitting.
        """
        children = element.split_at_dart(dart)
        for child in children:
            self._stamp_construction(child)
            self.elements.append(child)
        return children


class Block(PatternPart):
    """A base-block pattern piece derived from balanced measurements.

    A block captures the fundamental shape of a garment *without* personal
    fitting adjustments or style details.  It serves as a reusable starting
    point for new patterns and can be shown/hidden via the ``show_blocks``
    flag in the SVG export helpers.

    The part is identified by ``isinstance(part, Block)``.
    """

    def __init__(self, name: str, elements: list[PatternElement] | None = None) -> None:
        """Initialise a base-block part with *name* and optional *elements*."""
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
        """Initialise an overlay piece that shares coordinate space with *parent*."""
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
                style=copy.copy(elem.style),
                name=elem.name,
                role=elem.role,
                is_outline=elem.is_outline,
                is_seam_allowance=elem.is_seam_allowance,
                is_construction=elem.is_construction,
            )
            new_elem.is_seam_notch = elem.is_seam_notch
            # Internal SA / dart references: translate point-valued refs,
            # clear geometry-valued refs (they point into the parent's elements).
            new_elem._sa_center = (
                elem._sa_center.translate(dx, dy) if isinstance(elem._sa_center, Point) else None
            )
            new_elem._dart_ref = None  # parent-space Dart; not valid in exploded coords
            new_elem._leg_pt = (
                elem._leg_pt.translate(dx, dy) if isinstance(elem._leg_pt, Point) else None
            )
            exploded.elements.append(new_elem)

        return exploded


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
        """Initialise a pattern with *name*, optional *parts*, and optional page *anchor*."""
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
        from ..style import DEFAULT_STROKE_WIDTH
        from .construction import ConstructionGridPart

        target_part: PatternPart | None = part
        if target_part is None:
            regular = [p for p in self.parts if not isinstance(p, (ConstructionGridPart, Block))]
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
            style=(style if style is not None else StyleOptions(stroke_width=DEFAULT_STROKE_WIDTH)),
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
