"""Dart pattern elements — bridges dart geometry and styled PatternElements.

This module owns everything that connects a pure :class:`~sewpat.geometry.Dart`
to the list of :class:`~sewpat.element.PatternElement` objects that end up on a
pattern piece:

* :class:`DartResult`  — the typed return value of ``PatternPart.add_dart``,
  grouping all created elements by role.
* :class:`DartElements` — factory that builds those elements from a ``Dart``
  plus style/option arguments, without touching any ``PatternPart`` directly.
  Also exposes :meth:`DartElements.from_edge` as the single construction
  entry-point when building a dart from an existing seam edge.
"""

import copy

from .element import PatternElement, PrecisionPoint
from .geometry import (
    CubicBezier,
    Dart,
    InfoBox,
    Point,
    Segment,
)
from .style import (
    STYLE_DART_FOLD,
    STYLE_DART_STITCH,
    StyleOptions,
)
from .units import MM


# ---------------------------------------------------------------------------
# DartResult
# ---------------------------------------------------------------------------


class DartResult:
    """Return value of :meth:`~sewpat.pattern.PatternPart.add_dart`.

    Bundles the :class:`~sewpat.geometry.Dart` with every
    :class:`~sewpat.element.PatternElement` that was added to the part during
    the call, grouped by role.

    Attributes:
        dart: The dart geometry.
        stitch_elements: Stitching-leg segments (``is_outline=False``).
        fold_element: The fold/crease line segment (``None`` for inner darts).
        tip_elements: Precision-mark circles at the tip (may be empty).
        notch_elements: Notch triangles at the dart legs (may be empty).
        cut_elements: Modified cut-line segments for outer darts (empty for inner).
        rhombus_elements: Rhombus outline segments for inner/reverse darts (empty for outer).
    """

    def __init__(
        self,
        dart: Dart,
        stitch_elements: list[PatternElement],
        fold_element: PatternElement | None,
        tip_elements: list[PatternElement],
        notch_elements: list[PatternElement],
        cut_elements: list[PatternElement],
        rhombus_elements: list[PatternElement],
    ) -> None:
        self.dart = dart
        self.stitch_elements = stitch_elements
        self.fold_element = fold_element
        self.tip_elements = tip_elements
        self.notch_elements = notch_elements
        self.cut_elements = cut_elements
        self.rhombus_elements = rhombus_elements

    @property
    def all_elements(self) -> list[PatternElement]:
        """All PatternElements created for this dart in draw order."""
        result = list(self.stitch_elements)
        if self.fold_element is not None:
            result.append(self.fold_element)
        result.extend(self.tip_elements)
        result.extend(self.notch_elements)
        result.extend(self.cut_elements)
        result.extend(self.rhombus_elements)
        return result

    def __repr__(self) -> str:
        return (
            f"DartResult(dart={self.dart!r}, "
            f"elements={len(self.all_elements)})"
        )


# ---------------------------------------------------------------------------
# DartElements
# ---------------------------------------------------------------------------


class DartElements:
    """Factory that converts a :class:`~sewpat.geometry.Dart` into a list of
    :class:`~sewpat.element.PatternElement` objects.

    The factory is decoupled from :class:`~sewpat.pattern.PatternPart`; it only
    knows about geometry and styling.  Callers are responsible for appending the
    result to a part.

    The preferred construction path when placing a dart on an existing seam edge
    is :meth:`from_edge`, which accepts a :class:`~sewpat.element.PatternElement`
    and inherits its style automatically::

        factory = DartElements.from_edge(
            side_seam_element,
            position_t=0.4,
            width=22 * MM,
            depth=90 * MM,
            name="Taille",
        )
        result = part.add_dart(factory.dart, ...)

    When a :class:`~sewpat.geometry.Dart` already exists (e.g. after
    :func:`~sewpat.geometry.transfer_dart`), construct directly::

        factory = DartElements(dart, stitch_style=..., fold_style=...)
    """

    def __init__(
        self,
        dart: Dart,
        stitch_style: StyleOptions | None = None,
        fold_style: StyleOptions | None = None,
        edge_style: StyleOptions | None = None,
        precision_style: StyleOptions | None = None,
    ) -> None:
        self.dart = dart
        self.stitch_style = stitch_style if stitch_style is not None else STYLE_DART_STITCH
        self.fold_style = fold_style if fold_style is not None else STYLE_DART_FOLD
        self.edge_style = edge_style if edge_style is not None else STYLE_DART_STITCH
        self.precision_style: StyleOptions | None = precision_style
    # ------------------------------------------------------------------
    # Construction from a styled PatternElement edge
    # ------------------------------------------------------------------

    @classmethod
    def from_edge(
        cls,
        edge: PatternElement,
        position_t: float,
        width: float,
        depth: float | None = None,
        reference_point: Point | None = None,
        tip_shortfall: float = 20.0,
        fold_direction: str = "inward",
        name: str | None = None,
        stitch_style: StyleOptions | None = None,
        fold_style: StyleOptions | None = None,
        precision_style: StyleOptions | None = None,
    ) -> "DartElements":
        """Build a :class:`DartElements` factory from a styled seam-edge element.

        The *edge* **must** be a :class:`~sewpat.element.PatternElement` wrapping
        a :class:`~sewpat.geometry.Segment` or :class:`~sewpat.geometry.CubicBezier`.
        Its style is captured on :attr:`Dart.edge_style` so the cut-line mouth
        segments produced by :meth:`build_cut_elements` are visually identical to
        the rest of that seam — no manual ``edge_style`` argument is ever needed.

        Args:
            edge: The seam-edge ``PatternElement`` to place the dart on.
            position_t: Parameter ∈ [0, 1] along *edge* for the dart mouth center.
            width: Total dart-mouth opening in mm.
            depth: Explicit dart depth in mm.  Mutually exclusive with
                   *reference_point*.
            reference_point: Landmark point (e.g. bust point) the tip aims toward.
                             The tip is placed *tip_shortfall* mm short of it.
            tip_shortfall: Shortfall in mm from *reference_point* (default 20 mm).
                           Ignored when *depth* is given.
            fold_direction: ``"inward"`` (default) or ``"outward"``.
            name: Optional label for the dart.
            stitch_style: Overrides the default dart-stitch style.
            fold_style: Overrides the default dart-fold style.
            precision_style: Style for the two concentric precision circles at the
                tip.  The center is always taken from the dart tip geometry.
                Defaults to :data:`~sewpat.style.STYLE_PRECISION_POINT`.

        Returns:
            A fully configured :class:`DartElements` instance whose
            :attr:`dart` carries the computed geometry and the inherited
            ``edge_style``.

        Raises:
            TypeError: If *edge* is not a :class:`~sewpat.element.PatternElement`.
            ValueError: If the wrapped geometry is not a ``Segment`` or
                        ``CubicBezier``, or if the depth/reference_point
                        constraints are violated.
        """
        if not isinstance(edge, PatternElement):
            raise TypeError(
                f"DartElements.from_edge requires a PatternElement, got {type(edge).__name__!r}."
            )
        geom = edge.geometry
        if not isinstance(geom, (Segment, CubicBezier)):
            raise ValueError(
                "The PatternElement passed to DartElements.from_edge must wrap a "
                f"Segment or CubicBezier, got {type(geom).__name__!r}."
            )
        if depth is not None and reference_point is not None:
            raise ValueError("Provide exactly one of 'depth' or 'reference_point'.")
        if depth is None and reference_point is None:
            raise ValueError("Provide exactly one of 'depth' or 'reference_point'.")
        if not (0.0 <= position_t <= 1.0):
            raise ValueError(f"position_t must be in [0, 1], got {position_t}")

        # ── Mouth center ──────────────────────────────────────────────────
        center = geom.point_at_t(position_t)
        if isinstance(geom, CubicBezier):
            inward_normal = geom.normal_at_t(position_t)
        else:
            inward_normal = geom.unit_normal

        half_w = width / 2.0
        leg_a = center.move_towards(geom, -half_w)
        leg_b = center.move_towards(geom, +half_w)

        # ── Tip placement ─────────────────────────────────────────────────
        if reference_point is not None:
            # Move from reference_point toward center by tip_shortfall along
            # the straight fold line — keeps the tip on that line.
            fold_line = Segment(reference_point, center)
            tip = reference_point.move_towards(fold_line, tip_shortfall)
        else:
            assert depth is not None
            tip = Point(
                center.x + depth * float(inward_normal[0]),
                center.y + depth * float(inward_normal[1]),
            )

        dart = Dart(
            leg_a=leg_a,
            leg_b=leg_b,
            center=center,
            tip=tip,
            fold_direction=fold_direction,
            name=name,
        )
        return cls(dart, stitch_style=stitch_style, fold_style=fold_style, edge_style=edge.style, precision_style=precision_style)

    # ------------------------------------------------------------------
    # Low-level element builders (pure — no side effects on any part)
    # ------------------------------------------------------------------

    def build_stitch_elements(self) -> list[PatternElement]:
        """Return the two stitching-leg PatternElements (outer dart)."""
        dart = self.dart
        return [
            PatternElement(dart.stitch_line_a, style=self.stitch_style),
            PatternElement(dart.stitch_line_b, style=self.stitch_style),
        ]

    def build_fold_element(self) -> PatternElement:
        """Return the fold/crease-line PatternElement (outer dart)."""
        return PatternElement(self.dart.fold_line, style=self.fold_style)

    def build_cut_elements(self) -> list[PatternElement]:
        """Return the two outline cut-segments replacing the dart mouth (outer dart).

        Both segments carry ``is_outline=True`` and get ``seam_allowance=0.0``
        with ``corner_join="miter"`` so the SA engine closes the dart wedge
        cleanly.  The style is inherited from :attr:`Dart.edge_style` (set by
        :meth:`from_edge`), so the mouth segments are visually identical to the
        rest of the seam without any manual style argument.
        """
        dart = self.dart
        dart_cut_style = copy.copy(self.edge_style)
        dart_cut_style.corner_join = "miter"
        return [
            PatternElement(
                Segment(dart.leg_a, dart.center),
                style=dart_cut_style,
                is_outline=True,
            ),
            PatternElement(
                Segment(dart.center, dart.leg_b),
                style=dart_cut_style,
                is_outline=True,
            ),
        ]

    def build_rhombus_elements(self) -> list[PatternElement]:
        """Return the four rhombus-outline PatternElements (inner/reverse dart)."""
        dart = self.dart
        points = [
            (dart.leg_a, dart.tip),
            (dart.tip, dart.leg_b),
            (dart.leg_b, dart.center),
            (dart.center, dart.leg_a),
        ]
        return [
            PatternElement(Segment(p1, p2), style=self.stitch_style)
            for p1, p2 in points
        ]

    def build_tip_elements(self) -> list[PatternElement]:
        """Return the precision-mark circles and optional name label at the tip."""
        dart = self.dart
        pp = PrecisionPoint(dart.tip, style=self.precision_style)
        elements: list[PatternElement] = pp.build_elements()
        if dart.name:
            label = InfoBox(
                position=Point(dart.tip.x, dart.tip.y - 14 * MM),
                header=dart.name,
            )
            elements.append(PatternElement(label))
        return elements



