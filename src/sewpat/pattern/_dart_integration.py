"""Dart integration — free function that operates on a :class:`PatternPart`.

This module owns :func:`add_dart`, which adds all visual elements for a dart
to a part and is wired back into ``PatternPart`` as a thin wrapper method in
:mod:`sewpat.pattern.part`.
"""

import copy
import warnings
from typing import TYPE_CHECKING

from ..element import PatternElement, PrecisionPoint
from ..geometry import CubicBezier, Dart, InfoBox, Point, Segment
from ..style import (
    STYLE_DART_FOLD,
    STYLE_DART_STITCH,
    STYLE_PRECISION_POINT,
    StyleOptions,
)
from ..units import CM, MM
from ._notches import _place_notch_triangles

if TYPE_CHECKING:
    from .part import PatternPart

# Default notch dimensions used by :func:`add_dart` and :class:`PatternPart`.
_DEFAULT_NOTCH_LENGTH: float = 0.8 * CM
_DEFAULT_NOTCH_WIDTH: float = 0.4 * CM


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _roof_style(dart: Dart) -> StyleOptions:
    """Return a :class:`~sewpat.style.StyleOptions` for the dart roof outline.

    Inherits colour and stroke properties from the dart's source edge element
    (``dart._edge_element``) when available, then forces ``corner_join="miter"``
    so the roof peak renders as a sharp point.
    """
    edge_elem = getattr(dart, "_edge_element", None)
    edge_style = getattr(edge_elem, "style", None)
    style = copy.copy(edge_style) if edge_style is not None else StyleOptions()
    style.corner_join = "miter"
    return style


def _split_edge_at_dart_mouth(part: PatternPart, dart: Dart) -> None:
    """Replace the dart's source outline edge with the two outer stubs.

    When a dart is created from a part outline edge via one of the
    ``Dart.from_edge_*`` factories, ``dart._edge_element`` holds a reference
    to that edge.  This function removes the original element and inserts two
    shorter stubs — the portions of the edge *outside* the dart mouth — at the
    same position in ``part.elements``.  The middle sub-segment (the dart mouth
    itself) is discarded so that :func:`add_seam_allowance` sees a correct
    closed outline polygon.

    Only :class:`~sewpat.geometry.Segment` and
    :class:`~sewpat.geometry.CubicBezier` edges are supported.  A
    :exc:`UserWarning` is emitted whenever the split cannot be performed, so
    that callers are never silently misled:

    * ``_edge_element`` is ``None`` — dart was not built from a part edge;
      silent no-op.
    * ``_edge_element`` is not in ``part.elements`` — element was already
      removed or the wrong part was passed.
    * ``_edge_element.is_outline`` is ``False`` — element exists but is not
      an outline edge.
    * Geometry type is unsupported.
    """
    edge_elem = getattr(dart, "_edge_element", None)

    if edge_elem is None:
        # Dart was not created from a part edge — nothing to split, not an error.
        return

    if edge_elem not in part.elements:
        warnings.warn(
            f"add_dart({dart.name!r}): _edge_element is not in the part's element "
            "list — the outline edge will not be split at the dart mouth. "
            "Seam allowance may be incorrect.",
            UserWarning,
            stacklevel=3,
        )
        return

    if not edge_elem.is_outline:
        warnings.warn(
            f"add_dart({dart.name!r}): _edge_element is present but not marked "
            "is_outline=True — skipping edge split.",
            UserWarning,
            stacklevel=3,
        )
        return

    if not isinstance(edge_elem.geometry, (Segment, CubicBezier)):
        warnings.warn(
            f"add_dart({dart.name!r}): _edge_element geometry is "
            f"{type(edge_elem.geometry).__name__!r}, expected Segment or "
            "CubicBezier — skipping edge split.",
            UserWarning,
            stacklevel=3,
        )
        return

    src_style = copy.copy(edge_elem.style) if edge_elem.style is not None else StyleOptions()
    all_subs = edge_elem.geometry.split_at_points([dart.leg_a, dart.leg_b])

    # Keep only the outer two sub-segments; discard the middle (dart mouth).
    outer_subs = all_subs[:1] + (all_subs[-1:] if len(all_subs) > 1 else [])

    edge_name = edge_elem.get_name()
    idx = part.elements.index(edge_elem)
    part.elements.pop(idx)

    for i, geom in enumerate(outer_subs):
        if edge_name:
            geom = geom.set_name(edge_name)
        part.elements.insert(
            idx + i,
            PatternElement(
                geom, name=edge_name, style=src_style, is_outline=True, role="dart_edge_stub"
            ),
        )


def _add_roof_outline(part: PatternPart, dart: Dart) -> None:
    """Append the two roof outline segments to *part*.

    Creates ``leg_a → roof`` and ``leg_b → roof`` as
    :class:`~sewpat.element.PatternElement` objects with ``is_outline=True``
    and ``role="dart_roof"``.  Style is derived from the dart's source edge
    via :func:`_roof_style`.  ``_sa_center`` is set to ``dart.tip`` so the
    seam-allowance offset is directed away from the tip.
    """
    style = _roof_style(dart)
    roof = dart.roof
    for leg in (dart.leg_a, dart.leg_b):
        elem = PatternElement(
            Segment(leg, roof),
            style=style,
            is_outline=True,
            role="dart_roof",
        )
        elem._sa_center = dart.tip
        part.elements.append(elem)


def _add_center_notch(
    part: PatternPart,
    dart: Dart,
    length: float,
    width: float,
) -> None:
    """Append the center notch triangle at the dart roof peak.

    The notch is a narrow slit (1/5 of *half-width*) aligned along the fold
    line and pointing toward ``dart.tip``.  It is placed at ``dart.roof`` so
    that :func:`~sewpat.pattern._sa._project_dart_notches_to_sa` can
    intersect the fold-line ray with the SA polygon to find the exact
    projected position.

    Emits a :exc:`UserWarning` and returns early when ``dart.tip`` and
    ``dart.center`` coincide (degenerate fold line).
    """
    fold_seg = Segment(dart.center, dart.tip)
    if fold_seg.length < 1e-12:
        warnings.warn(
            f"add_dart({dart.name!r}): tip and center coincide — center notch cannot be placed.",
            UserWarning,
            stacklevel=4,
        )
        return

    # along = left-hand perpendicular to fold; normal = toward tip (into the dart).
    half_slit = (width / 2) / 5  # slit is 1/5 of the half-width
    elems = _place_notch_triangles(
        part,
        dart.roof,
        along=fold_seg.unit_normal,
        normal=fold_seg.unit_direction,
        half_w=half_slit,
        length=length,
        role="dart_center_notch",
    )
    elems[0]._sa_center = dart.tip
    elems[0]._dart_ref = dart


def _add_leg_notch(
    part: PatternPart,
    dart: Dart,
    leg_pt: Point,
    length: float,
    width: float,
) -> None:
    """Append one leg notch triangle at *leg_pt*.

    The notch base is aligned along the ``leg_pt → roof`` direction; the
    normal points inward toward ``dart.tip``.  ``_leg_pt`` is stored on the
    element so that :func:`~sewpat.pattern._sa._project_dart_notches_to_sa`
    can project the leg position onto the SA polygon.

    Emits a :exc:`UserWarning` and returns early when *leg_pt* coincides with
    ``dart.roof`` (degenerate direction).
    """
    roof_seg = Segment(leg_pt, dart.roof)
    if roof_seg.length < 1e-12:
        warnings.warn(
            f"add_dart({dart.name!r}): leg point coincides with roof peak — "
            f"leg notch at {leg_pt!r} cannot be placed.",
            UserWarning,
            stacklevel=4,
        )
        return

    # unit_normal is the left-hand perpendicular; flip toward dart.tip if needed.
    perp = roof_seg.unit_normal
    if float(perp @ (dart.tip.coords - leg_pt.coords)) < 0:
        perp = -perp

    elems = _place_notch_triangles(
        part,
        leg_pt,
        along=roof_seg.unit_direction,
        normal=perp,
        half_w=width / 2,
        length=length,
        role="dart_notch",
    )
    elems[0]._leg_pt = leg_pt


def _add_precision_tip(
    part: PatternPart,
    dart: Dart,
    style: StyleOptions,
    tip: Point,
) -> None:
    """Append precision circles and an optional name label at *tip*.

    Delegates circle rendering to :class:`~sewpat.element.PrecisionPoint`.
    When ``dart.name`` is set an :class:`~sewpat.geometry.InfoBox` label is
    placed 14 mm below *tip*.  All created elements receive ``role="dart_tip"``.
    """
    for e in PrecisionPoint(tip, style=style).build_elements():
        e.role = "dart_tip"
        part.elements.append(e)
    if dart.name:
        part.elements.append(
            PatternElement(
                InfoBox(tip - Point(0, 14 * MM), header=dart.name),
                role="dart_tip",
            )
        )


def _add_triangle_dart(
    part: PatternPart,
    dart: Dart,
    *,
    stitch_style: StyleOptions,
    fold_style: StyleOptions,
    precision_style: StyleOptions,
    notches: bool,
    precision_tip: bool,
    notch_length: float,
    notch_width: float,
) -> None:
    """Add all visual elements for a triangle dart to *part*.

    Appends in order: stitch lines, fold line, roof outline stubs, notches
    (center + two leg), precision tip mark.  Notches are skipped when
    *notches* is ``False``; the tip mark is skipped when *precision_tip* is
    ``False``.
    """
    part.elements.append(PatternElement(dart.stitch_line_a, style=stitch_style, role="dart_stitch"))
    part.elements.append(PatternElement(dart.stitch_line_b, style=stitch_style, role="dart_stitch"))
    part.elements.append(PatternElement(dart.fold_line, style=fold_style, role="dart_fold"))

    _add_roof_outline(part, dart)

    if notches:
        _add_center_notch(part, dart, length=notch_length, width=notch_width)
        for leg_pt in (dart.leg_a, dart.leg_b):
            _add_leg_notch(part, dart, leg_pt, length=notch_length, width=notch_width)

    if precision_tip:
        _add_precision_tip(part, dart, precision_style, dart.tip)


def _add_rhombus_dart(
    part: PatternPart,
    dart: Dart,
    *,
    stitch_style: StyleOptions,
    fold_style: StyleOptions,
    precision_style: StyleOptions,
    precision_tip: bool,
) -> None:
    """Add all visual elements for a rhombus dart to *part*.

    Appends the four diamond sides (``leg_a → tip → leg_b → second_tip →
    leg_a``), a fold / crease line from ``tip`` to ``effective_second_tip``,
    and optional precision marks at both apices.
    """
    st = dart.effective_second_tip
    for p1, p2 in (
        (dart.leg_a, dart.tip),
        (dart.tip, dart.leg_b),
        (dart.leg_b, st),
        (st, dart.leg_a),
    ):
        part.elements.append(
            PatternElement(Segment(p1, p2), style=stitch_style, role="dart_stitch")
        )

    part.elements.append(PatternElement(dart.fold_line, style=fold_style, role="dart_fold"))

    if precision_tip:
        for tip in (dart.tip, st):
            _add_precision_tip(part, dart, precision_style, tip)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def add_dart(
    part: PatternPart,
    dart: Dart,
    *,
    stitch_style: StyleOptions | None = None,
    fold_style: StyleOptions = STYLE_DART_FOLD,
    precision_style: StyleOptions = STYLE_PRECISION_POINT,
    notches: bool = True,
    precision_tip: bool = True,
    notch_length: float = _DEFAULT_NOTCH_LENGTH,
    notch_width: float = _DEFAULT_NOTCH_WIDTH,
) -> None:
    """Add all visual elements for *dart* to *part*.

    Dispatches to :func:`_add_triangle_dart` or :func:`_add_rhombus_dart`
    depending on ``dart.dart_type``.

    **Triangle dart** — splits the source outline edge at the dart mouth via
    :func:`_split_edge_at_dart_mouth`, then appends stitch lines, fold line,
    roof outline segments (``is_outline=True``), notch triangles, and a
    precision tip mark.

    **Rhombus dart** — appends four diamond sides, a fold / crease line
    (``tip → effective_second_tip``), and precision marks at both apices.

    Style overrides: *stitch_style* defaults to :data:`~sewpat.style.STYLE_DART_STITCH`,
    *fold_style* to :data:`~sewpat.style.STYLE_DART_FOLD`, and *precision_style* to
    :data:`~sewpat.style.STYLE_PRECISION_POINT`.  The roof outline inherits the
    style of the dart's source edge element (``dart._edge_element``) when
    available; see :func:`_roof_style`.

    Set *notches* to ``False`` to suppress notch triangles (triangle darts
    only).  Set *precision_tip* to ``False`` to suppress tip circles and
    labels.  *notch_length* and *notch_width* control the notch triangle
    dimensions (defaults :data:`_DEFAULT_NOTCH_LENGTH` and
    :data:`_DEFAULT_NOTCH_WIDTH`).

    A :exc:`UserWarning` is emitted for every step that cannot be completed
    so that callers are never silently misled.
    """
    _stitch = stitch_style if stitch_style is not None else STYLE_DART_STITCH

    if dart.is_triangle:
        _split_edge_at_dart_mouth(part, dart)
        _add_triangle_dart(
            part,
            dart,
            stitch_style=_stitch,
            fold_style=fold_style,
            precision_style=precision_style,
            notches=notches,
            precision_tip=precision_tip,
            notch_length=notch_length,
            notch_width=notch_width,
        )
    else:
        _add_rhombus_dart(
            part,
            dart,
            stitch_style=_stitch,
            fold_style=fold_style,
            precision_style=precision_style,
            precision_tip=precision_tip,
        )
