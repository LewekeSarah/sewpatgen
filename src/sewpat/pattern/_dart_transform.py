"""Dart transfer — free function that operates on a :class:`PatternPart`.

This module owns :func:`transfer_dart`, which transfers a dart to a new cut-line
position and is wired back into ``PatternPart`` as a thin wrapper method in
:mod:`sewpat.pattern.part`.
"""

from typing import TYPE_CHECKING

from ..element import PatternElement
from ..geometry import Circle, CubicBezier, Dart, InfoBox, Point, Ray, Segment, Triangle
from ..geometry._algorithms import _normalize_vector, _signed_angle
from ..style import STYLE_DART_FOLD, STYLE_PRECISION_POINT, StyleOptions

if TYPE_CHECKING:
    from .part import PatternPart


#: ``GeometryType`` members that implement ``rotate``.  ``Rect``, ``Line``,
#: ``Ray``, and ``Dart`` do not and are left untouched by step 3d.
_ROTATABLE_GEOMETRY = (Point, Segment, Circle, Triangle, CubicBezier, InfoBox)

#: Roles of the old dart's visual elements removed by step 3f before the new
#: dart is added.  ``dart_edge_stub`` is intentionally excluded — it is the
#: split remainder of the part's main outline, not dart-specific debris.
_STALE_DART_ROLES = frozenset(
    {
        "dart_stitch",
        "dart_fold",
        "dart_roof",
        "dart_center_notch",
        "dart_notch",
        "dart_tip",
    }
)


def _cutline_outline_intersection(
    cut_geom: Ray | Segment,
    part: PatternPart,
    tip: Point,
) -> tuple[Point, PatternElement] | None:
    """Return the outline intersection of *cut_geom* farthest from *tip*.

    Iterates all ``is_outline`` elements and collects intersection points,
    returning the ``(point, element)`` pair with the greatest distance from
    *tip* (so the tip itself — which lies on the line — is not selected).
    """
    from ..geometry import intersect

    best: tuple[Point, PatternElement] | None = None
    best_dist = -1.0
    for elem in part.elements:
        if not elem.is_outline:
            continue
        geom = elem.geometry
        if isinstance(geom, Dart):
            continue
        try:
            pts = intersect(cut_geom, geom)
        except Exception:
            continue
        for pt in pts:
            d = tip.distance_to(pt)
            if d > best_dist:
                best_dist = d
                best = (pt, elem)
    return best


def transfer_dart(
    part: PatternPart,
    dart: Dart,
    cut_line: Ray | Segment,
    *,
    sa_distance: float | None = None,
    stitch_style: StyleOptions | None = None,
    fold_style: StyleOptions = STYLE_DART_FOLD,
    precision_style: StyleOptions = STYLE_PRECISION_POINT,
    notches: bool = True,
    precision_tip: bool = True,
    notch_length: float | None = None,
    notch_width: float | None = None,
) -> Dart:
    """Transfer *dart* to the position defined by *cut_line*.

    Rotates the section of *part* between the inner dart leg and *cut_line*
    around ``dart.tip`` to close the dart at its current position, opens a
    new dart along *cut_line*, then atomically removes the old dart's visual
    elements and adds the new dart's visual elements — *part* always has the
    same number of darts before and after this call.

    **Precondition**: *cut_line* must pass through ``dart.tip`` within 1 mm.

    Args:
        part: The pattern part to transform (modified in place).
        dart: The dart to transfer.  ``dart.tip``, ``dart.leg_a``, and
            ``dart.leg_b`` define the geometry.
        cut_line: A :class:`~sewpat.geometry.Ray` or
            :class:`~sewpat.geometry.Segment` that passes through ``dart.tip``
            and points toward the new dart position on the outline.
        sa_distance: If provided and the part has seam-allowance elements, the
            SA is removed and regenerated at this distance after the transfer.
        stitch_style: Forwarded to :meth:`PatternPart.add_dart` for the new
            dart's stitch lines.
        fold_style: Forwarded to :meth:`PatternPart.add_dart` for the new
            dart's fold line.
        precision_style: Forwarded to :meth:`PatternPart.add_dart` for the new
            dart's tip marker.
        notches: Forwarded to :meth:`PatternPart.add_dart`; set ``False`` to
            suppress notch triangles on the new dart.
        precision_tip: Forwarded to :meth:`PatternPart.add_dart`; set
            ``False`` to suppress the new dart's tip circles and label.
        notch_length: Forwarded to :meth:`PatternPart.add_dart`.
        notch_width: Forwarded to :meth:`PatternPart.add_dart`.

    Returns:
        The new :class:`~sewpat.geometry.Dart` object describing the
        transferred dart (tip + two new leg points).  Its visual elements
        have **already been added** to *part* — do not call
        ``part.add_dart(new_dart)`` again.

    Raises:
        ValueError: If *cut_line* does not pass through ``dart.tip`` within 1 mm,
            or if no outline intersection can be found for the new dart legs.
    """
    from .part import PatternPart

    tip = dart.tip

    # --- Precondition: cut_line must pass through dart.tip ----------------
    proj = cut_line.project_point(tip)
    dist_to_cutline = tip.distance_to(proj)
    if dist_to_cutline > 1.0:
        raise ValueError(
            f"cut_line must pass through dart.tip "
            f"(distance={dist_to_cutline:.3f} mm > 1 mm tolerance)"
        )

    # --- 3a: Determine inner leg and rotation angle -----------------------
    cut_dir = cut_line.unit_direction
    dir_a = _normalize_vector(dart.leg_a.coords - tip.coords)
    dir_b = _normalize_vector(dart.leg_b.coords - tip.coords)

    # Signed angle from each leg direction to the cut direction.
    # The inner leg is the one with the smaller unsigned angle to the cut.
    angle_a = _signed_angle(dir_a, cut_dir)
    angle_b = _signed_angle(dir_b, cut_dir)

    if abs(angle_a) <= abs(angle_b):
        inner_leg_dir, outer_leg_dir = dir_a, dir_b
    else:
        inner_leg_dir, outer_leg_dir = dir_b, dir_a

    # Rotating by this angle closes the old dart (inner leg -> outer leg);
    # the cut line sweeps away by the same angle, opening the new dart.
    rotation_angle = _signed_angle(inner_leg_dir, outer_leg_dir)

    # --- 3b: Split outline at cut line ------------------------------------
    cut_elem = part.add_cutline(cut_line)

    # --- 3c: Collect elements to rotate -----------------------------------
    elements_to_rotate = [
        elem
        for elem in part.elements
        if elem is not cut_elem
        and PatternPart._element_is_between(tip, inner_leg_dir, cut_dir, elem)
    ]

    # --- 3d: Apply rotation -----------------------------------------------
    # Capture the pre-rotation centroid as the fallback "inward" reference for
    # seam-allowance offsetting.  Elements without an explicit ``_sa_center``
    # normally fall back to ``part.centroid`` at SA-generation time, but a
    # *fixed* global centroid is no longer a valid "inward" reference for
    # elements that get rotated below: rotating around ``tip`` can flip which
    # side of an element's tangent now faces the (unrotated) centroid, which
    # flips the offset direction and makes the new SA cut across the stitch
    # line.  Pinning each rotated element's ``_sa_center`` to this
    # pre-rotation centroid — and rotating it along with the element — keeps
    # the "inward" reference locally consistent through the rotation.
    centroid = part.centroid
    for elem in elements_to_rotate:
        geom = elem.geometry
        if isinstance(geom, _ROTATABLE_GEOMETRY):
            elem.geometry = geom.rotate(tip, rotation_angle)
        # Rotate any attached reference points, defaulting to the
        # pre-rotation centroid when no per-element override is set.
        sa_center = elem._sa_center if isinstance(elem._sa_center, Point) else centroid
        if isinstance(sa_center, Point):
            elem._sa_center = sa_center.rotate(tip, rotation_angle)
        leg_pt = elem._leg_pt
        if isinstance(leg_pt, Point):
            elem._leg_pt = leg_pt.rotate(tip, rotation_angle)

    # --- 3e: Construct new dart -------------------------------------------
    # Find where the original cut line crosses the post-rotation outline.
    # (cut_line, not cut_elem.geometry: add_cutline may only rename it via
    # set_name, which preserves both type and geometry.)
    hit_a = _cutline_outline_intersection(cut_line, part, tip)

    if hit_a is None:
        raise ValueError(
            "transfer_dart: could not find outline intersection for the new dart leg. "
            "Ensure cut_line passes through dart.tip and intersects the part outline."
        )

    new_leg_a, mouth_elem = hit_a

    # new_leg_b is the rotated image of new_leg_a: 3d already moved the
    # outline element that shares this vertex into place, so rotating the
    # point directly gives the new vertex exactly -- re-deriving it via a
    # fresh ray/outline intersection is numerically fragile right at that
    # vertex (the intersection can fall a hair outside the segment's [0, 1]
    # range depending on absolute coordinates).
    new_leg_b = new_leg_a.rotate(tip, rotation_angle)

    new_dart = Dart.from_edge_at_legs(
        edge=mouth_elem,
        leg_a=new_leg_a,
        leg_b=new_leg_b,
        tip=tip,
        dart_type=dart.dart_type,
        name=dart.name,
    )

    # --- 3f: Replace the old dart with the new dart (atomic) ---------------
    part.elements = [
        e for e in part.elements if e.role not in _STALE_DART_ROLES and e is not cut_elem
    ]

    add_dart_kwargs: dict[str, float] = {}
    if notch_length is not None:
        add_dart_kwargs["notch_length"] = notch_length
    if notch_width is not None:
        add_dart_kwargs["notch_width"] = notch_width

    part.add_dart(
        new_dart,
        stitch_style=stitch_style,
        fold_style=fold_style,
        precision_style=precision_style,
        notches=notches,
        precision_tip=precision_tip,
        **add_dart_kwargs,
    )

    # --- 3g: Update seam allowance ------------------------------------------
    if sa_distance is not None:
        has_sa = any(e.is_seam_allowance for e in part.elements)
        if has_sa:
            from . import _sa

            part.elements = [e for e in part.elements if not e.is_seam_allowance]
            _sa.add_seam_allowance(part, sa_distance)

    return new_dart
