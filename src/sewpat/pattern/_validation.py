"""Pattern quality validation — seam-length and width checks.

This module owns all validation types and the standalone functions that power
:meth:`~sewpat.pattern.Pattern.validate_seam_pairs` and
:meth:`~sewpat.pattern.Pattern.validate_widths`.  Both are wired back into
:class:`~sewpat.pattern.Pattern` as thin one-liner wrappers in
:mod:`sewpat.pattern.part`.

Public names
------------
SeamPairSpec, SeamPairResult, SeamValidationResult
WidthLevelSpec, WidthCheckResult, WidthValidationResult
validate_seam_pairs, validate_widths
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..geometry import CubicBezier, Line, Point, Segment
from ..geometry import intersect as _geom_intersect

if TYPE_CHECKING:
    from ..element import PatternElement
    from .part import Pattern, PatternPart


# ---------------------------------------------------------------------------
# Seam-pair validation
# ---------------------------------------------------------------------------

#: Type alias for one seam-pair specification passed to
#: :func:`validate_seam_pairs`.
#:
#: Each entry is a 4-, 5-, or 6-tuple::
#:
#:     (part_a, role_a, part_b, role_b)                      # global tolerance
#:     (part_a, role_a, part_b, role_b, max_tol)             # override upper bound
#:     (part_a, role_a, part_b, role_b, max_tol, min_delta)  # range: min_delta ≤ Δ ≤ max_tol
#:
#: The optional 6th element *min_delta* is a **signed** lower bound on
#: ``length_a − length_b`` (e.g. ``10.0`` means *part_a* must be at least
#: 10 mm longer than *part_b*).
#:
#: Each part is either a :class:`~sewpat.pattern.PatternPart` object or a
#: name string (including :class:`~sewpat.pattern.GarmentPart` enum values).
type SeamPairSpec = (
    tuple["PatternPart | str", str, "PatternPart | str", str]
    | tuple["PatternPart | str", str, "PatternPart | str", str, float]
    | tuple["PatternPart | str", str, "PatternPart | str", str, float, float]
)


@dataclass
class SeamPairResult:
    """Measurement result for a single matched seam pair.

    Attributes:
        part_a: Name of the first pattern part.
        role_a: Role tag used to select elements in *part_a*.
        length_a: Total seam length in mm for the matched elements in *part_a*.
        part_b: Name of the second pattern part.
        role_b: Role tag used to select elements in *part_b*.
        length_b: Total seam length in mm for the matched elements in *part_b*.
        delta_mm: Signed difference ``length_a - length_b`` in mm.
            Positive means *part_a* is longer, negative means *part_b* is longer.
        tolerance_mm: The upper tolerance applied to this pair: ``delta_mm`` must
            not exceed this value in absolute terms.
        min_delta_mm: Optional signed lower bound.  When set, ``delta_mm`` must
            also be ``>= min_delta_mm`` for the pair to be ``ok``.
            ``None`` means no lower bound is enforced.
        ok: ``True`` when all active bounds are satisfied:
            ``abs(delta_mm) <= tolerance_mm`` and, if set,
            ``delta_mm >= min_delta_mm``.
    """

    part_a: str
    role_a: str
    length_a: float
    part_b: str
    role_b: str
    length_b: float
    delta_mm: float
    tolerance_mm: float
    ok: bool
    min_delta_mm: float | None = None


@dataclass
class SeamValidationResult:
    """Aggregated result of :func:`validate_seam_pairs`.

    Attributes:
        pairs: One :class:`SeamPairResult` per checked seam pair, in the order
            they were supplied.
        all_ok: ``True`` when every pair is within tolerance.
        tolerance_mm: The tolerance value that was used.
    """

    pairs: list[SeamPairResult] = field(default_factory=list)
    all_ok: bool = True
    tolerance_mm: float = 2.0

    def __str__(self) -> str:
        """Human-readable summary, one line per pair."""
        lines: list[str] = [
            f"Seam validation  {'✓ all OK' if self.all_ok else '✗ mismatches found'}"
        ]
        for r in self.pairs:
            mark = "✓" if r.ok else "✗"
            if r.min_delta_mm is not None:
                bound_str = f"({r.min_delta_mm:+.1f}..{r.tolerance_mm:+.1f} mm)"
            else:
                bound_str = f"(±{r.tolerance_mm:.1f} mm)"
            lines.append(
                f"  {mark} {r.part_a!r}[{r.role_a}] {r.length_a:.1f} mm"
                f"  vs  {r.part_b!r}[{r.role_b}] {r.length_b:.1f} mm"
                f"  Δ = {r.delta_mm:+.1f} mm  {bound_str}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Width-level validation
# ---------------------------------------------------------------------------

#: Type alias for one width-level specification passed to
#: :func:`validate_widths`.
#:
#: Each entry is a 9- or 10-tuple::
#:
#:     (back, back_center_role, back_side_role,
#:      front, front_center_role, front_side_role,
#:      label, grid_segment, expected_mm)            # global tolerance
#:
#:     (back, back_center_role, back_side_role,
#:      front, front_center_role, front_side_role,
#:      label, grid_segment, expected_mm, tol_mm)    # per-level override
#:
#: Each part is either a :class:`~sewpat.pattern.PatternPart` object or a
#: name string.  *grid_segment* is the :class:`~sewpat.geometry.Segment` of
#: the construction grid at the level to check (e.g. ``grid.chest``).  The
#: width is measured as the distance between the center-seam intersection and
#: the side-seam intersection of that grid segment on each pattern piece.
type WidthLevelSpec = (
    tuple[
        "PatternPart | str",
        str,
        str,  # back_part, back_center_role, back_side_role
        "PatternPart | str",
        str,
        str,  # front_part, front_center_role, front_side_role
        str,  # label
        Segment,  # grid_segment
        float,  # expected_mm
    ]
    | tuple[
        "PatternPart | str",
        str,
        str,
        "PatternPart | str",
        str,
        str,
        str,
        Segment,
        float,
        float,  # tolerance_mm override
    ]
)


@dataclass
class WidthCheckResult:
    """Measurement result for a single horizontal-width level check.

    Attributes:
        label: Human-readable level label, e.g. ``"Bust"``, ``"Waist"``,
            ``"Hip"``.
        back_part: Name of the back pattern part.
        back_center_role: Role used to locate the center-back intersection.
        back_side_role: Role used to locate the side-seam intersection on the
            back piece.
        front_part: Name of the front pattern part.
        front_center_role: Role used to locate the center-front intersection.
        front_side_role: Role used to locate the side-seam intersection on the
            front piece.
        back_width_mm: Distance from the back-center to the back side-seam
            intersection on *grid_segment*.
        front_width_mm: Distance from the front-center to the front side-seam
            intersection on *grid_segment*.
        total_width_mm: ``back_width_mm + front_width_mm`` — the combined
            half-width of the garment at this level.
        expected_mm: Expected total width (e.g. ``meas.bust_width / 2``).
        delta_mm: Signed difference ``total_width_mm - expected_mm``.
        tolerance_mm: Maximum allowed absolute value of *delta_mm*.
        ok: ``True`` when ``abs(delta_mm) <= tolerance_mm``.
    """

    label: str
    back_part: str
    back_center_role: str
    back_side_role: str
    front_part: str
    front_center_role: str
    front_side_role: str
    back_width_mm: float
    front_width_mm: float
    total_width_mm: float
    expected_mm: float
    delta_mm: float
    tolerance_mm: float
    ok: bool


@dataclass
class WidthValidationResult:
    """Aggregated result of :func:`validate_widths`.

    Attributes:
        checks: One :class:`WidthCheckResult` per checked level, in the order
            they were supplied.
        all_ok: ``True`` when every check is within tolerance.
        tolerance_mm: The default tolerance value that was used.
    """

    checks: list[WidthCheckResult] = field(default_factory=list)
    all_ok: bool = True
    tolerance_mm: float = 5.0

    def __str__(self) -> str:
        """Human-readable summary, one line per level."""
        lines: list[str] = [
            f"Width validation  {'✓ all OK' if self.all_ok else '✗ mismatches found'}"
        ]
        for r in self.checks:
            mark = "✓" if r.ok else "✗"
            lines.append(
                f"  {mark} {r.label}:  "
                f"back({r.back_part!r})[{r.back_center_role}↔{r.back_side_role}]"
                f" {r.back_width_mm:.1f} mm"
                f"  + front({r.front_part!r})[{r.front_center_role}↔{r.front_side_role}]"
                f" {r.front_width_mm:.1f} mm"
                f"  = {r.total_width_mm:.1f} mm"
                f"  vs {r.expected_mm:.1f} mm"
                f"  Δ = {r.delta_mm:+.1f} mm  (±{r.tolerance_mm:.1f} mm)"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _intersect_grid_with_role(
    part: PatternPart,
    role: str,
    grid_seg: Segment,
) -> Point:
    """Return the intersection of *grid_seg* with the role-tagged outline elements.

    The *grid_seg* is first extended to an infinite :class:`~sewpat.geometry.Line`
    so that the check is robust regardless of how the pattern is positioned on
    the page.  The intersection is then verified to lie within the bounds of
    the matching outline element.

    Args:
        part: The pattern piece to search.
        role: The ``role`` tag used to filter ``is_outline`` elements.
        grid_seg: Construction-grid segment defining the level (e.g.
            ``grid.chest`` for the bust level).

    Returns:
        The single intersection point found.

    Raises:
        ValueError: If no ``is_outline`` elements carry *role*, or none of
            them intersect the grid line at this level.
    """
    elems = [e for e in part.elements if e.role == role and e.is_outline]
    if not elems:
        raise ValueError(f"No is_outline elements with role {role!r} found in part {part.name!r}.")

    # Convert the finite grid segment to an infinite line so the intersection
    # is not affected by the segment's endpoints — the pattern may be freely
    # positioned on the page and the "level" line extends without bounds.
    grid_line = Line(grid_seg.p1, grid_seg.unit_direction)

    pts: list[Point] = []
    for elem in elems:
        geom = elem.geometry
        if isinstance(geom, (Segment, CubicBezier)):
            pts.extend(_geom_intersect(grid_line, geom))

    if not pts:
        raise ValueError(
            f"Grid line at {grid_seg.name!r} does not intersect any is_outline element "
            f"with role {role!r} in part {part.name!r}."
        )

    # Deduplicate: drop any point within 0.5 mm of a previous one.
    unique: list[Point] = []
    for pt in pts:
        if not any(pt.distance_to(u) < 0.5 for u in unique):
            unique.append(pt)

    if len(unique) == 1:
        return unique[0]

    # Multiple distinct intersections (non-convex outline): return the one
    # closest to the midpoint of the grid segment as a best-effort heuristic.
    mid = grid_seg.midpoint  # pragma: no cover
    return min(unique, key=lambda p: p.distance_to(mid))  # pragma: no cover


# ---------------------------------------------------------------------------
# Standalone validation functions
# ---------------------------------------------------------------------------


def validate_seam_pairs(
    pattern: Pattern,
    pairs: list[SeamPairSpec],
    *,
    tolerance_mm: float = 2.0,
    warn: bool = True,
) -> SeamValidationResult:
    """Compare seam lengths across pattern parts.

    See :meth:`sewpat.pattern.Pattern.validate_seam_pairs` for the full
    docstring.  This standalone function implements the logic; the method is
    a one-line wrapper.
    """
    from .part import PatternPart  # lazy import — breaks the circular dependency

    result = SeamValidationResult(tolerance_mm=tolerance_mm)

    for entry in pairs:
        part_a_ref, role_a, part_b_ref, role_b = entry[0], entry[1], entry[2], entry[3]
        pair_tolerance = entry[4] if len(entry) >= 5 else tolerance_mm
        pair_min_delta: float | None = entry[5] if len(entry) == 6 else None

        part_a = part_a_ref if isinstance(part_a_ref, PatternPart) else pattern.get_part(part_a_ref)
        part_b = part_b_ref if isinstance(part_b_ref, PatternPart) else pattern.get_part(part_b_ref)

        elems_a: list[PatternElement | str] = [
            e for e in part_a.elements if e.role == role_a and e.is_outline
        ]
        elems_b: list[PatternElement | str] = [
            e for e in part_b.elements if e.role == role_b and e.is_outline
        ]

        if not elems_a:
            raise ValueError(
                f"No is_outline elements with role {role_a!r} found in part {part_a.name!r}."
            )
        if not elems_b:
            raise ValueError(
                f"No is_outline elements with role {role_b!r} found in part {part_b.name!r}."
            )

        len_a = part_a.seam_length(elems_a)
        len_b = part_b.seam_length(elems_b)
        delta = len_a - len_b
        ok = abs(delta) <= pair_tolerance and (pair_min_delta is None or delta >= pair_min_delta)

        pair_result = SeamPairResult(
            part_a=part_a.name,
            role_a=role_a,
            length_a=len_a,
            part_b=part_b.name,
            role_b=role_b,
            length_b=len_b,
            delta_mm=delta,
            tolerance_mm=pair_tolerance,
            ok=ok,
            min_delta_mm=pair_min_delta,
        )
        result.pairs.append(pair_result)
        if not ok:
            result.all_ok = False
            if warn:
                if pair_min_delta is not None:
                    bound_str = f"expected {pair_min_delta:+.1f}..{pair_tolerance:+.1f} mm"
                else:
                    bound_str = f"tolerance ±{pair_tolerance:.1f} mm"
                warnings.warn(
                    f"Seam mismatch: {part_a.name!r}[{role_a}] "
                    f"({len_a:.1f} mm) vs {part_b.name!r}[{role_b}] "
                    f"({len_b:.1f} mm) — Δ = {delta:+.1f} mm "
                    f"({bound_str})",
                    UserWarning,
                    stacklevel=3,
                )

    return result


def validate_widths(
    pattern: Pattern,
    specs: list[WidthLevelSpec],
    *,
    tolerance_mm: float = 5.0,
    warn: bool = True,
) -> WidthValidationResult:
    """Check that the combined back + front widths at key levels match measurements.

    See :meth:`sewpat.pattern.Pattern.validate_widths` for the full docstring.
    This standalone function implements the logic; the method is a one-line
    wrapper.
    """
    from .part import PatternPart  # lazy import — breaks the circular dependency

    result = WidthValidationResult(tolerance_mm=tolerance_mm)

    for entry in specs:
        back_ref, back_center_role, back_side_role = entry[0], entry[1], entry[2]
        front_ref, front_center_role, front_side_role = entry[3], entry[4], entry[5]
        label, grid_seg, expected_mm = entry[6], entry[7], entry[8]
        level_tolerance = entry[9] if len(entry) == 10 else tolerance_mm  # type: ignore[misc]

        back_part = back_ref if isinstance(back_ref, PatternPart) else pattern.get_part(back_ref)
        front_part = (
            front_ref if isinstance(front_ref, PatternPart) else pattern.get_part(front_ref)
        )

        # Intersect the grid line with the center and side seams on each piece.
        back_center_pt = _intersect_grid_with_role(back_part, back_center_role, grid_seg)
        back_side_pt = _intersect_grid_with_role(back_part, back_side_role, grid_seg)
        front_center_pt = _intersect_grid_with_role(front_part, front_center_role, grid_seg)
        front_side_pt = _intersect_grid_with_role(front_part, front_side_role, grid_seg)

        back_width = back_center_pt.distance_to(back_side_pt)
        front_width = front_center_pt.distance_to(front_side_pt)
        total = back_width + front_width
        delta = total - expected_mm
        ok = abs(delta) <= level_tolerance

        check = WidthCheckResult(
            label=label,
            back_part=back_part.name,
            back_center_role=back_center_role,
            back_side_role=back_side_role,
            front_part=front_part.name,
            front_center_role=front_center_role,
            front_side_role=front_side_role,
            back_width_mm=back_width,
            front_width_mm=front_width,
            total_width_mm=total,
            expected_mm=expected_mm,
            delta_mm=delta,
            tolerance_mm=level_tolerance,
            ok=ok,
        )
        result.checks.append(check)
        if not ok:
            result.all_ok = False
            if warn:
                warnings.warn(
                    f"Width mismatch at {label!r}: "
                    f"back({back_part.name!r})[{back_center_role}↔{back_side_role}]"
                    f" {back_width:.1f} mm"
                    f" + front({front_part.name!r})[{front_center_role}↔{front_side_role}]"
                    f" {front_width:.1f} mm"
                    f" = {total:.1f} mm vs expected {expected_mm:.1f} mm —"
                    f" Δ = {delta:+.1f} mm (tolerance ±{level_tolerance:.1f} mm)",
                    UserWarning,
                    stacklevel=3,
                )

    return result
