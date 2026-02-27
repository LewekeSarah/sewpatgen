from .style import StyleOptions, STYLE_GRAINLINE
from .geometry import Rect, Point, Segment, Circle, Triangle, InfoBox
from .units import CM, MM
import numpy as np


class PatternElement:
    """A pattern element combining a geometric shape with a style.

    Attributes:
        geometry: The geometric shape (Point, Segment, Rect, Circle, CubicBezier, …).
        style: Visual style for rendering this element.
        name: Optional label override. If None, the geometry's own name is used.
    """

    def __init__(
        self,
        geometry: object,
        style: "StyleOptions | None" = None,
        name: "str | None" = None,
    ) -> None:
        self.geometry = geometry
        self.style = style if style is not None else StyleOptions()
        self.name = name

    def get_name(self) -> "str | None":
        """Return the effective name (element name overrides geometry name)."""
        if self.name is not None:
            return self.name
        return getattr(self.geometry, "name", None)


class PatternPart:
    """A collection of pattern elements forming one pattern piece."""

    def __init__(
        self, name: str, elements: "list[PatternElement] | None" = None
    ) -> None:
        self.name = name
        self.elements: list[PatternElement] = elements if elements is not None else []

    def append(
        self,
        geometry: object,
        style: "StyleOptions | None" = None,
        name: "str | None" = None,
    ) -> "PatternElement":
        """Create a PatternElement from geometry + style and append it to this part.

        Args:
            geometry: The geometric shape to add.
            style: Optional style for the element. Defaults to StyleOptions().
            name: Optional label override for the element.

        Returns:
            The newly created PatternElement.
        """
        elem = PatternElement(geometry=geometry, style=style, name=name)
        self.elements.append(elem)
        return elem

    def extend(self, elements: "list[PatternElement]") -> None:
        """Append multiple PatternElements at once.

        Args:
            elements: List of PatternElement objects to add.
        """
        self.elements.extend(elements)

    @property
    def centroid(self) -> "Point | None":
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
    ) -> "PatternElement":
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
        self, header: str | None = None, notes: "list[str] | None" = None
    ) -> "PatternElement | None":
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
            self.append(Circle(center, radius=5 * MM))
            self.append(Circle(center, radius=0.5 * MM))

    def add_notches(
        self,
        *points: Point,
        segment: "Segment | None" = None,
        length: float = 0.8 * CM,
        width: float = 0.4 * CM,
    ) -> None:
        """Add notch marks at the given points, always facing inward.

        Notches are small filled triangles standing on the seam edge and
        pointing inward (toward the fabric), as per standard sewing pattern
        conventions.

        If ``segment`` is provided, each point is projected orthogonally onto
        that segment. The triangle base sits on the seam edge and the tip
        points inward. The inward direction is determined automatically from
        the part's centroid.

        Without ``segment``, a vertical triangle centred on the point is used.

        Args:
            *points: One or more reference points for the notches.
            segment: Segment (seam edge) on which the notches stand.
            length: Distance from base to tip of the triangle. Defaults to 0.8 cm.
            width: Width of the triangle base on the seam edge. Defaults to 0.4 cm.
        """
        inward_ref = self.centroid
        half_w = width / 2
        for pt in points:
            if segment is not None:
                # Orthogonal projection of pt onto the segment line
                p1 = segment.p1.coords
                d = segment.p2.coords - p1
                t = float(np.dot(pt.coords - p1, d) / np.dot(d, d))
                notch_pt = Point(*(p1 + t * d))

                # Inward normal — flip if pointing away from centroid
                normal = segment.unit_normal
                if inward_ref is not None:
                    to_inner = inward_ref.coords - notch_pt.coords
                    if np.dot(normal, to_inner) < 0:
                        normal = -normal

                # Along-edge direction (unit_direction of segment)
                along = segment.unit_direction
                nx, ny = normal
                ax, ay = along

                base_left = notch_pt.translate(-half_w * ax, -half_w * ay)
                base_right = notch_pt.translate(half_w * ax, half_w * ay)
                tip = notch_pt.translate(nx * length, ny * length)
            else:
                base_left = pt.translate(-half_w, 0)
                base_right = pt.translate(half_w, 0)
                tip = pt.translate(0, -length)

            self.append(Triangle(base_left, base_right, tip))


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
        parts: "list[PatternPart] | None" = None,
        anchor: "Point | None" = None,
    ) -> None:
        self.name = name
        self.parts: list[PatternPart] = parts if parts is not None else []
        self.reference_square: PatternElement | None = None
        self.anchor: Point = anchor if anchor is not None else Point(1.5 * CM, 1.5 * CM)

    def set_reference_square(
        self,
        origin: Point,
        edge_length: float = 3 * CM,
        style: "StyleOptions | None" = None,
    ) -> "PatternElement":
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

    def add_part(self, part: "PatternPart") -> "PatternPart":
        """Append a PatternPart to this pattern.

        Args:
            part: The PatternPart to add.

        Returns:
            The added PatternPart (for chaining).
        """
        self.parts.append(part)
        return part

    def get_part(self, name: str) -> "PatternPart":
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
