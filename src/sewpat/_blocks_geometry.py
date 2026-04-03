"""Internal geometry builders for :mod:`sewpat.blocks`.

All names here are private (prefixed ``_``).  External code should only ever
import from :mod:`sewpat.blocks`.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .geometry import (
    Circle,
    CubicBezier,
    Dart,
    DartType,
    Line,
    Point,
    Ray,
    Segment,
    fit_cubic_bezier,
    fit_cubic_bezier_free,
    intersect,
    seam_length,
    split_bezier_seam_fn,
)
from .grids import TopGrid, WideSleeveGrid
from .measurements import (
    BlouseMeasurements,
    GarmentConfig,
    HipDistribution,
    WaistDistribution,
)
from .pleat import Pleat
from .units import CM

if TYPE_CHECKING:
    from .blocks import BlockConfig
    from .pattern import PatternElement
    from .sleeve import SleeveArmhole, SleeveConfig


# ---------------------------------------------------------------------------
# Internal dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _BackGeometry:
    """All computed geometry for the back piece, prior to assembly."""

    # Key points
    anchor: Point
    waist_center_back: Point
    hip_center_back: Point
    waist_center_back_adj: Point
    hip_center_back_adj: Point
    hem_center_back_outline: Point
    """Bottom end-point of the center-back outline edge.

    For the waisted-dart block this is ``center_back ∩ hem`` translated by
    ``hip_offset`` (a vertical line, so x = hip_offset).
    For the casual block it is the intersection of the angled center-back
    line with the hem grid — a different x-position because the line is not
    vertical.
    """
    armscye_back_chest: Point
    side_back_chest: Point
    armscye_back_shoulder: Point
    armscye_back_shoulder_dropped: Point
    neck_back_shoulder: Point
    shoulder_back_neckline: Point
    shoulder_dart_notch: Point
    shoulder_blade_dart_tip: Point
    armscye_control: Point  # armscye notch (pt_hÄP)

    # Curves and segments
    armscye_back_lower: CubicBezier  # side_chest → armscye_control, through dart_notch
    armscye_back_upper: CubicBezier  # armscye_control → shoulder.p2
    neckline_back: CubicBezier
    shoulder_back: Segment
    shoulder_back_orig: Segment
    shoulder_blade: Line
    center_back_segments: list[Segment]
    """One segment (casual/straight) or two segments (waisted-dart/kinked)."""


@dataclass(frozen=True)
class _FrontGeometry:
    """All computed geometry for the front piece, prior to assembly."""

    # Key points
    side_front_chest: Point
    armscye_front_chest: Point
    bust_point: Point
    neckline_front_start: Point
    center_front_shoulder_line: Point
    shoulder_front_neckline_pt: Point
    armscye_control: Point  # armscye notch (pt_vÄP)

    # Curves and segments
    armscye_front_lower: CubicBezier
    armscye_front_upper: CubicBezier | None
    neckline_front: CubicBezier
    neckline_front_stub: CubicBezier | None
    shoulder_armscye: Segment
    shoulder_neckline: Segment | None
    """The short shoulder segment toward the neckline, containing the dart mouth.
    ``None`` when ``has_shoulder_dart`` is ``False`` — the shoulder is a single
    unbroken seam and ``shoulder_armscye`` covers the full length."""
    shoulder_front_aux_orig: Segment | None
    """Waisted-dart only: construction segment used to derive the shoulder split."""
    shoulder_front_dart_orig: Segment | None
    """Waisted-dart only: construction segment for the neckline side of the dart."""


@dataclass(frozen=True)
class _SideSeams:
    """Side-seam geometry shared between the two pieces."""

    # Back
    waist_indent_back: Point
    hip_side_back: Point
    side_chest_waist_back: Segment
    side_waist_hip_back: CubicBezier
    side_hip_hem_back: Segment
    hem_side_to_center_back: Segment | CubicBezier

    # Front
    waist_indent_front: Point
    hip_side_front: Point
    side_chest_waist_front: Segment
    side_waist_hip_front: CubicBezier
    side_hip_hem_front: Segment
    hem_side_to_center_front: Segment | CubicBezier

    # Construction lines
    waist_offset: Segment


@dataclass(frozen=True)
class _Darts:
    """All dart objects for both pieces."""

    waist_dart_back: Dart | None
    """``None`` when ``has_waist_dart`` is ``False``."""
    waist_dart_front: Dart | None
    """``None`` when ``has_waist_dart`` is ``False``."""
    shoulder_dart_front: Dart | None
    """``None`` when ``has_shoulder_dart`` is ``False``."""


# ---------------------------------------------------------------------------
# Back geometry
# ---------------------------------------------------------------------------


def _build_back_geometry(
    grid: TopGrid,
    meas: BlouseMeasurements,
    anchor: Point,
    hip_offset: float,
    shoulder_drop: float,
    shoulder_gather: float,
    block_config: BlockConfig,
) -> _BackGeometry:
    """Compute all key points and curves for the back piece."""
    waist_center_back = intersect(grid.center_back, grid.waist)[0]
    hip_center_back = intersect(grid.center_back, grid.hip)[0]
    waist_center_back_adj = waist_center_back.translate(hip_offset, 0)
    hip_center_back_adj = hip_center_back.translate(hip_offset, 0)

    armscye_chest = intersect(grid.armscye_back, grid.chest)[0]
    side_chest = intersect(grid.side_back, grid.chest)[0]
    armscye_shoulder = intersect(grid.armscye_back, grid.shoulder_back)[0]
    neck_shoulder = intersect(grid.shoulder_back, grid.neck)[0]
    armscye_shoulder_dropped = armscye_shoulder.translate(0, shoulder_drop)

    # Shoulder seam
    shoulder_neckline = neck_shoulder.translate(0, -block_config.shoulder_raise)
    dart_notch = (
        Segment(armscye_shoulder_dropped, armscye_chest)
        .point_at_t(0.5)
        .translate(block_config.armscye_back_aux_offset, 0)
    )
    shoulder_blade = Line(dart_notch, (1, 0), name="Shoulder Blade")
    armscye_control = (
        Segment(armscye_shoulder_dropped, armscye_chest)
        .point_at_t(0.75)
        .translate(block_config.armscye_back_offset, 0)
    )
    shoulder_orig = Segment.from_direction(
        shoulder_neckline,
        armscye_shoulder_dropped,
        length=meas.shoulder_width + shoulder_gather,
    )
    shoulder = shoulder_orig.offset(-block_config.shoulder_ease)

    blade_dart_tip = intersect(grid.dart_back, shoulder_blade)[0]

    # Armscye curve — two cubics joined at armscye_control.
    _cp2_y = armscye_control.distance_to_segment(grid.chest) - block_config.armscye_back_cp_y
    armscye_lower = CubicBezier(
        side_chest,
        side_chest.translate(
            (armscye_control.x - side_chest.x) / 3,
            -block_config.armscye_back_cp_y / 2,
        ),
        armscye_control.translate(block_config.armscye_back_cp_x, _cp2_y),
        armscye_control,
        name="Armscye Back Lower",
    )
    armscye_upper = CubicBezier(
        armscye_control,
        dart_notch.translate(-(dart_notch.x - armscye_control.x) / 2, 0),
        dart_notch.translate(-(dart_notch.x - armscye_control.x) / 2, 0),
        shoulder.p2,
        name="Armscye Back Upper",
    )

    # Neckline curve
    neckline = CubicBezier(
        anchor,
        anchor,
        neck_shoulder,
        shoulder.p1,
        name="Neckline Back",
    )

    # Center-back line(s)
    if block_config.straight_center_back:
        cb_shoulder = intersect(grid.center_back, grid.shoulder_back)[0]
        hem_cb_straight = intersect(
            Ray(cb_shoulder, (hip_center_back_adj - cb_shoulder).coords), grid.hem
        )[0]
        center_back_segs: list[Segment] = [
            Segment(cb_shoulder, hem_cb_straight, name="Center Back"),
        ]
        hem_cb_outline = hem_cb_straight
    else:
        hem_cb_outline = intersect(grid.center_back, grid.hem)[0].translate(hip_offset, 0)
        center_back_segs = [
            Segment(anchor, waist_center_back_adj, name="Center Back"),
            Segment(waist_center_back_adj, hem_cb_outline, name="Center Back Hem"),
        ]

    return _BackGeometry(
        anchor=anchor,
        waist_center_back=waist_center_back,
        hip_center_back=hip_center_back,
        waist_center_back_adj=waist_center_back_adj,
        hip_center_back_adj=hip_center_back_adj,
        hem_center_back_outline=hem_cb_outline,
        armscye_back_chest=armscye_chest,
        side_back_chest=side_chest,
        armscye_back_shoulder=armscye_shoulder,
        armscye_back_shoulder_dropped=armscye_shoulder_dropped,
        neck_back_shoulder=neck_shoulder,
        shoulder_back_neckline=shoulder_neckline,
        shoulder_dart_notch=dart_notch,
        shoulder_blade_dart_tip=blade_dart_tip,
        armscye_control=armscye_control,
        armscye_back_lower=armscye_lower,
        armscye_back_upper=armscye_upper,
        neckline_back=neckline,
        shoulder_back=shoulder,
        shoulder_back_orig=shoulder_orig,
        shoulder_blade=shoulder_blade,
        center_back_segments=center_back_segs,
    )


# ---------------------------------------------------------------------------
# Front geometry — shoulder helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ShoulderGeometry:
    """Intermediate results from the shoulder construction, shared by both paths."""

    shoulder_upper_pt: Point
    shoulder_armscye: Segment
    _shoulder_neckline_raw: Segment
    shoulder_neckline: Segment | None
    shoulder_front_aux_orig: Segment | None
    shoulder_front_dart_orig: Segment | None


def _build_shoulder_no_dart(
    armscye_front_chest: Point,
    shoulder_front_neckline_pt: Point,
    arm_seam_length: float,
    block_config: BlockConfig,
    meas: BlouseMeasurements,
) -> _ShoulderGeometry:
    """Single unbroken shoulder seam — no dart (casual path)."""
    shoulder_upper_pt = intersect(
        Circle(armscye_front_chest, arm_seam_length),
        Circle(shoulder_front_neckline_pt, meas.shoulder_width),
    )[1]
    _shoulder_orig = Segment(shoulder_upper_pt, shoulder_front_neckline_pt)
    shoulder_armscye = _shoulder_orig.offset(block_config.shoulder_ease)
    return _ShoulderGeometry(
        shoulder_upper_pt=shoulder_upper_pt,
        shoulder_armscye=shoulder_armscye,
        _shoulder_neckline_raw=shoulder_armscye,
        shoulder_neckline=None,
        shoulder_front_aux_orig=_shoulder_orig,
        shoulder_front_dart_orig=None,
    )


def _build_shoulder_dart(
    armscye_front_chest: Point,
    armscye_front_chest_upper: Point,
    shoulder_front_neckline_pt: Point,
    bust_point: Point,
    bust_point_shoulder_line: Point,
    arm_seam_length: float,
    armscye_fit: float,
    block_config: BlockConfig,
    meas: BlouseMeasurements,
) -> _ShoulderGeometry:
    """Bust-point pivot construction — split shoulder seam with dart (waisted path)."""
    shoulder_upper_pt = Circle(armscye_front_chest, arm_seam_length).point_along_from(
        armscye_front_chest_upper, -(meas.bust / 20 + armscye_fit)
    )
    shoulder_front_pivot = intersect(
        Circle(bust_point, meas.bust_depth),
        Circle(shoulder_upper_pt, meas.shoulder_width),
    )[0]
    shoulder_front_aux_seg = Segment(shoulder_front_pivot, shoulder_upper_pt)
    _shoulder_armscye_end = shoulder_front_aux_seg.point_along_from(
        shoulder_front_pivot,
        Segment(shoulder_front_neckline_pt, bust_point_shoulder_line).length,
    )
    _shoulder_neckline_start = bust_point.translate(
        0, -Segment(bust_point, _shoulder_armscye_end).length
    )
    shoulder_armscye = Segment(shoulder_upper_pt, _shoulder_armscye_end).offset(
        block_config.shoulder_ease
    )
    _shoulder_neckline_raw = Segment(_shoulder_neckline_start, shoulder_front_neckline_pt).offset(
        block_config.shoulder_ease
    )
    # M&S approach: use _shoulder_neckline_raw.p1 directly as the dart mouth.
    # The parallel offset shifts p1 by shoulder_ease (~1 cm) sideways from the
    # bustpoint grid line, introducing a small leg-length asymmetry — acceptable
    # in practice as the dart opening is small and the difference negligible.
    #
    # Alternative — Hofenbitzer approach (geometrically exact, equal dart legs):
    # After the offset, extend _shoulder_neckline_raw as a Ray and intersect
    # with grid.bust_point to recover the on-grid endpoint, then replace the
    # segment with the extended version.  This enlarges the short shoulder seam
    # slightly but keeps both dart legs exactly equal.
    #
    #   _extended = intersect(
    #       Ray(_shoulder_neckline_raw.p1, _shoulder_neckline_raw.unit_direction),
    #       grid.bust_point,
    #   )
    #   if _extended:
    #       _shoulder_neckline_raw = Segment(_extended[0], _shoulder_neckline_raw.p2)
    return _ShoulderGeometry(
        shoulder_upper_pt=shoulder_upper_pt,
        shoulder_armscye=shoulder_armscye,
        _shoulder_neckline_raw=_shoulder_neckline_raw,
        shoulder_neckline=None,  # set after neckline split
        shoulder_front_aux_orig=Segment(shoulder_front_pivot, shoulder_upper_pt),
        shoulder_front_dart_orig=Segment(shoulder_front_neckline_pt, _shoulder_neckline_start),
    )


def _split_neckline_and_armscye(
    sh: _ShoulderGeometry,
    neckline_front_start: Point,
    center_front_shoulder_line: Point,
    shoulder_front_neckline_pt: Point,
    bust_point: Point,
    side_front_chest: Point,
    block_config: BlockConfig,
    meas: BlouseMeasurements,
) -> tuple[
    Segment,
    Segment | None,
    CubicBezier,
    CubicBezier | None,
    CubicBezier | None,
    CubicBezier,
]:
    """Split neckline and armscye at their intersections with the shoulder seam."""
    # p1 is offset slightly LEFT of p0 (horizontal tangent at the CF end) so the
    # neckline meets the vertical center-front at a right angle.  The original
    # p1 = p0 was degenerate (zero tangent) which caused the SA algorithm to
    # arrive at the CF corner diagonally.  10 % of neck_size is enough to define
    # the direction without meaningfully shifting the neckline/shoulder split point.
    neckline_front_full = CubicBezier(
        neckline_front_start,
        neckline_front_start.translate(-meas.neck_size * 0.1, 0),
        center_front_shoulder_line.translate(-meas.neck_size, meas.neck_size),
        shoulder_front_neckline_pt,
    )
    _neckline_ray = Ray(sh._shoulder_neckline_raw.p1, sh._shoulder_neckline_raw.unit_direction)
    _neckline_intersections = intersect(neckline_front_full, _neckline_ray)
    if _neckline_intersections:
        _ix = _neckline_intersections[0]
        shoulder_neckline: Segment | None = (
            Segment(sh._shoulder_neckline_raw.p1, _ix) if block_config.has_shoulder_dart else None
        )
        _nf = neckline_front_full.split_at_points([_ix])
        neckline_front = CubicBezier(_nf[0].p0, _nf[0].p1, _nf[0].p2, _ix)
        neckline_front_stub: CubicBezier | None = _nf[1] if len(_nf) > 1 else None
        _ix_neckline: Point | None = _ix
    else:  # pragma: no cover  — neckline ray always intersects for valid measurements
        shoulder_neckline = sh._shoulder_neckline_raw if block_config.has_shoulder_dart else None
        neckline_front = neckline_front_full
        neckline_front_stub = None
        _ix_neckline = None

    armscye_front_full = CubicBezier(
        sh.shoulder_upper_pt,
        bust_point.translate(block_config.armscye_front_cp_x, block_config.armscye_front_cp_y),
        side_front_chest.translate(meas.armscye_width * 0.05, 0),
        side_front_chest,
    )
    _armscye_end = sh.shoulder_armscye.p1
    _armscye_split = armscye_front_full.split_at_points([_armscye_end])
    if len(_armscye_split) > 1:
        armscye_front_upper: CubicBezier | None = _armscye_split[0]
        armscye_front_lower = _armscye_split[1]
    else:  # pragma: no cover  — split point always found for valid measurements
        armscye_front_upper = None
        armscye_front_lower = armscye_front_full

    # No-dart: trim shoulder_armscye to [_armscye_end → neckline intersection].
    shoulder_armscye = sh.shoulder_armscye
    if not block_config.has_shoulder_dart and _ix_neckline is not None:
        shoulder_armscye = Segment(_armscye_end, _ix_neckline, name="Shoulder Front")

    return (
        shoulder_armscye,
        shoulder_neckline,
        neckline_front,
        neckline_front_stub,
        armscye_front_upper,
        armscye_front_lower,
    )


def _build_front_geometry(
    grid: TopGrid,
    meas: BlouseMeasurements,
    back: _BackGeometry,
    armscye_fit: float,
    block_config: BlockConfig,
) -> _FrontGeometry:
    """Compute all key points and curves for the front piece."""
    side_front_chest = intersect(grid.side_front, grid.chest)[0]
    armscye_front_chest = intersect(grid.armscye_front, grid.chest)[0]

    bust_point_shoulder_line = intersect(grid.shoulder_front, grid.bust_point)[0]
    bust_point = bust_point_shoulder_line.translate(0, meas.bust_depth)

    center_front_shoulder_line = intersect(grid.center_front, grid.shoulder_front)[0]
    neckline_front_start = center_front_shoulder_line.translate(
        0, meas.neck_size + block_config.neckline_ease_y
    )
    shoulder_front_neckline_pt = center_front_shoulder_line.translate(
        -(meas.neck_size + block_config.neckline_ease_x), 0
    )

    armscye_control = armscye_front_chest.translate(0, -0.25 * meas.armscye_width)
    arm_seam_length = (
        Segment(back.armscye_back_shoulder_dropped, back.armscye_back_chest).length
        - block_config.armscye_front_offset
    )
    armscye_front_chest_upper = armscye_front_chest.translate(0, -arm_seam_length)

    if not block_config.has_shoulder_dart:
        sh = _build_shoulder_no_dart(
            armscye_front_chest,
            shoulder_front_neckline_pt,
            arm_seam_length,
            block_config,
            meas,
        )
    else:
        sh = _build_shoulder_dart(
            armscye_front_chest,
            armscye_front_chest_upper,
            shoulder_front_neckline_pt,
            bust_point,
            bust_point_shoulder_line,
            arm_seam_length,
            armscye_fit,
            block_config,
            meas,
        )

    (
        shoulder_armscye,
        shoulder_neckline,
        neckline_front,
        neckline_front_stub,
        armscye_front_upper,
        armscye_front_lower,
    ) = _split_neckline_and_armscye(
        sh,
        neckline_front_start,
        center_front_shoulder_line,
        shoulder_front_neckline_pt,
        bust_point,
        side_front_chest,
        block_config,
        meas,
    )

    return _FrontGeometry(
        side_front_chest=side_front_chest,
        armscye_front_chest=armscye_front_chest,
        bust_point=bust_point,
        neckline_front_start=neckline_front_start,
        center_front_shoulder_line=center_front_shoulder_line,
        shoulder_front_neckline_pt=shoulder_front_neckline_pt,
        armscye_control=armscye_control,
        armscye_front_lower=armscye_front_lower,
        armscye_front_upper=armscye_front_upper,
        neckline_front=neckline_front,
        neckline_front_stub=neckline_front_stub,
        shoulder_armscye=shoulder_armscye,
        shoulder_neckline=shoulder_neckline,
        shoulder_front_aux_orig=sh.shoulder_front_aux_orig,
        shoulder_front_dart_orig=sh.shoulder_front_dart_orig,
    )


# ---------------------------------------------------------------------------
# Side seams
# ---------------------------------------------------------------------------


def _build_hip_curves(
    grid: TopGrid,
    back: _BackGeometry,
    front: _FrontGeometry,
    wd: WaistDistribution,
    hd: HipDistribution,
    block_config: BlockConfig,
    waist_offset_line: Segment,
    waist_indent_back: Point,
    waist_indent_front: Point,
) -> tuple[Point, Point, CubicBezier, CubicBezier]:
    """Return (hip_side_back, hip_side_front, side_waist_hip_back, side_waist_hip_front).

    Builds the hip outset points and the waist-to-hip Bézier curves for both
    pieces.  The curves end with p2 == p3 (a cusp tangent); the casual path
    will later replace side_waist_hip_back with a version that has a proper
    end-tangent aligned to the angled side-hem segment.
    """
    side_back_offset = grid.side_back.offset(hd.hip_shortfall / 2)
    side_front_offset = grid.side_front.offset(-hd.hip_shortfall / 2)
    hip_side_back = intersect(grid.hip, side_back_offset)[0]
    hip_side_front = intersect(grid.hip, side_front_offset)[0]

    side_waist_hip_back = CubicBezier(
        waist_indent_back,
        intersect(grid.side_back, waist_offset_line)[0].translate(
            -hd.hip_shortfall / 2, block_config.side_hip_tangent
        ),
        hip_side_back,
        hip_side_back,
        name="Side Hip Curve Back",
    )
    side_waist_hip_front = CubicBezier(
        waist_indent_front,
        intersect(grid.side_front, waist_offset_line)[0].translate(
            hd.hip_shortfall / 2, block_config.side_hip_tangent
        ),
        hip_side_front,
        hip_side_front,
        name="Side Hip Curve Front",
    )
    return hip_side_back, hip_side_front, side_waist_hip_back, side_waist_hip_front


def _build_casual_back_hem(
    back: _BackGeometry,
    hip_side_back: Point,
    side_waist_hip_back: CubicBezier,
) -> tuple[Segment, Segment, CubicBezier]:
    """Return (hem_back, side_hip_hem_back, side_waist_hip_back) for the casual path.

    The hem is a straight Segment orthogonal to the center-back edge.
    The side-hem runs along the CB direction so it arrives orthogonal to the hem.
    The hip curve is rebuilt with a proper end-tangent (aligned to the CB
    direction) so the SA miter between the two edges is well-defined.
    """
    cb_seg = back.center_back_segments[0]

    # Hem ray: from hem_cb_outline orthogonal to CB (right-hand normal).
    hem_ray = Ray(back.hem_center_back_outline, -cb_seg.unit_normal)

    # Side-hem ray: from hip_side_back along the CB direction.
    # Their intersection satisfies both: hem ⊥ CB and side ‖ CB.
    side_ray = Ray(hip_side_back, cb_seg.unit_direction)
    hem_back_end = intersect(hem_ray, side_ray)[0]

    hem_back = Segment(back.hem_center_back_outline, hem_back_end, name="Hem Back")
    side_hip_hem_back = Segment(hip_side_back, hem_back_end, name="Side Hem Back")

    # Fix the hip curve end-tangent: pull p2 back along the reversed CB direction
    # so the Bézier ends tangentially aligned with side_hip_hem_back, giving the
    # SA algorithm a valid non-zero tangent for the corner miter.
    p2_offset = side_hip_hem_back.length / 3
    side_waist_hip_back = CubicBezier(
        side_waist_hip_back.p0,
        side_waist_hip_back.p1,
        hip_side_back + Point(*(-cb_seg.unit_direction * p2_offset)),
        hip_side_back,
        name="Side Hip Curve Back",
    )
    return hem_back, side_hip_hem_back, side_waist_hip_back


def _build_casual_front_hem(
    grid: TopGrid,
    hip_side_front: Point,
    side_waist_hip_front: CubicBezier,
    side_hip_hem_front: Segment,
    back_side_total: float,
) -> tuple[Segment, CubicBezier]:
    """Return (side_hip_hem_front, hem_front) for the casual path.

    Crops the front side-hem so that the total side length (hip curve + hem
    segment) equals *back_side_total*, then builds a near-straight Bézier hem
    from the center-front hem point to the cropped side end.
    """
    front_remaining = back_side_total - side_waist_hip_front.length
    hem_front_side_pt = side_hip_hem_front.point_at_length(front_remaining)
    side_hip_hem_front = Segment(hip_side_front, hem_front_side_pt, name="Side Hem Front")

    hem_front_start = intersect(grid.hem, grid.center_front)[0]
    cp_bust = intersect(grid.hem, grid.bust_point)[0]
    hem_front = CubicBezier(
        hem_front_start,
        cp_bust,
        cp_bust,
        hem_front_side_pt,
        name="Hem Front",
    )
    return side_hip_hem_front, hem_front


def _build_side_seams(
    grid: TopGrid,
    meas: BlouseMeasurements,
    config: GarmentConfig,
    back: _BackGeometry,
    front: _FrontGeometry,
    wd: WaistDistribution,
    hd: HipDistribution,
    block_config: BlockConfig,
) -> _SideSeams:
    """Compute side-seam points and curves for both pieces."""
    waist_offset_line = grid.waist.offset(-block_config.waist_offset).set_name("Waist Offset")

    waist_indent_back = intersect(grid.side_back, waist_offset_line)[0].translate(
        -wd.side_seam_intake, 0
    )
    waist_indent_front = intersect(grid.side_front, waist_offset_line)[0].translate(
        wd.side_seam_intake, 0
    )

    side_chest_waist_back = Segment(
        waist_indent_back, back.side_back_chest, name="Side Seam Back Upper"
    )
    side_chest_waist_front = Segment(
        waist_indent_front, front.side_front_chest, name="Side Seam Front Upper"
    )

    hip_side_back, hip_side_front, side_waist_hip_back, side_waist_hip_front = _build_hip_curves(
        grid,
        back,
        front,
        wd,
        hd,
        block_config,
        waist_offset_line,
        waist_indent_back,
        waist_indent_front,
    )

    hem_depth = config.length - (meas.back_length + meas.hip_depth)
    side_hip_hem_back = Segment(
        hip_side_back, hip_side_back.translate(0, hem_depth), name="Side Hem Back"
    )
    side_hip_hem_front = Segment(
        hip_side_front, hip_side_front.translate(0, hem_depth), name="Side Hem Front"
    )

    hem_side_to_center_back: Segment | CubicBezier
    hem_side_to_center_front: Segment | CubicBezier

    if block_config.straight_center_back:
        hem_side_to_center_back, side_hip_hem_back, side_waist_hip_back = _build_casual_back_hem(
            back, hip_side_back, side_waist_hip_back
        )
        side_hip_hem_front, hem_side_to_center_front = _build_casual_front_hem(
            grid,
            hip_side_front,
            side_waist_hip_front,
            side_hip_hem_front,
            back_side_total=seam_length([side_waist_hip_back, side_hip_hem_back]),
        )
    else:
        side_back_offset = grid.side_back.offset(hd.hip_shortfall / 2)
        side_front_offset = grid.side_front.offset(-hd.hip_shortfall / 2)
        hem_side_to_center_back = Segment(
            intersect(grid.hem, side_back_offset)[0],
            back.hem_center_back_outline,
        )
        hem_side_to_center_front = Segment(
            intersect(grid.hem, side_front_offset)[0],
            intersect(grid.hem, grid.center_front)[0],
        )

    return _SideSeams(
        waist_indent_back=waist_indent_back,
        hip_side_back=hip_side_back,
        side_chest_waist_back=side_chest_waist_back,
        side_waist_hip_back=side_waist_hip_back,
        side_hip_hem_back=side_hip_hem_back,
        hem_side_to_center_back=hem_side_to_center_back,
        waist_indent_front=waist_indent_front,
        hip_side_front=hip_side_front,
        side_chest_waist_front=side_chest_waist_front,
        side_waist_hip_front=side_waist_hip_front,
        side_hip_hem_front=side_hip_hem_front,
        hem_side_to_center_front=hem_side_to_center_front,
        waist_offset=waist_offset_line,
    )


# ---------------------------------------------------------------------------
# Darts
# ---------------------------------------------------------------------------


def _build_darts(
    grid: TopGrid,
    meas: BlouseMeasurements,
    back: _BackGeometry,
    front: _FrontGeometry,
    armscye_back_elem: PatternElement,
    wd: WaistDistribution,
    config: GarmentConfig,
    block_config: BlockConfig,
) -> tuple[_Darts, Dart | None]:
    """Build all dart objects for both pieces."""
    if block_config.has_waist_dart:
        waist_dart_back_center = intersect(grid.waist, grid.dart_back)[0]
        waist_dart_back: Dart | None = Dart.from_tip_center_width(
            tip=intersect(grid.dart_back, grid.chest)[0],
            center=waist_dart_back_center,
            width=wd.back_dart_width,
            dart_type=DartType.RHOMBUS,
            second_tip=waist_dart_back_center.translate(0, config.waist_dart_back_tip),
        ).set_name("Waist Dart Back")

        bust_point_waist = intersect(grid.bust_point, grid.waist)[0]
        waist_dart_front: Dart | None = Dart.from_tip_center_width(
            tip=front.bust_point,
            center=bust_point_waist,
            width=wd.front_dart_width,
            dart_type=DartType.RHOMBUS,
            second_tip=bust_point_waist.translate(0, config.waist_dart_front_tip),
        ).set_name("Waist Dart Front")
    else:
        waist_dart_back = None
        waist_dart_front = None

    if front.shoulder_neckline is not None:
        shoulder_dart_front: Dart | None = Dart.from_tip_and_legs(
            front.bust_point,
            front.shoulder_neckline.p1,
            front.shoulder_armscye.p2,
        ).set_name("Shoulder Dart Front")
    else:
        shoulder_dart_front = None

    if block_config.has_shoulder_dart:
        shoulder_dart_back: Dart | None = Dart.from_edge_at_legs(
            armscye_back_elem,
            leg_a=back.shoulder_dart_notch,
            leg_b=back.armscye_back_upper.point_along_from(
                back.shoulder_dart_notch, block_config.shoulder_dart_width
            ),
            tip=back.shoulder_blade_dart_tip,
            name="Shoulder Dart Back",
        )
    else:
        shoulder_dart_back = None

    return _Darts(
        waist_dart_back=waist_dart_back,
        waist_dart_front=waist_dart_front,
        shoulder_dart_front=shoulder_dart_front,
    ), shoulder_dart_back


# ---------------------------------------------------------------------------
# Wide-sleeve geometry
# ---------------------------------------------------------------------------

# Notch offsets for the sleeve cap slopes (t along slope, perpendicular offset in mm).
# cap-LEFT slope travels crown→cap_left; Bézier t-params are 0.25/0.50/0.75 in the
# opposite direction, so slope-t 0.75/0.50/0.25 maps to Bézier t 0.25/0.50/0.75.
_CAP_LEFT_NOTCH_PARAMS: tuple[tuple[float, float], ...] = (
    (0.75, -0.8 * CM),
    (0.50, 0.5 * CM),
    (0.25, 1.5 * CM),
)
# cap-RIGHT slope travels cap_right→crown (same direction as the Bézier).
_CAP_RIGHT_NOTCH_PARAMS: tuple[tuple[float, float], ...] = (
    (0.25, 0.0 * CM),
    (0.50, 1.5 * CM),
    (0.75, 2.0 * CM),
)
# Hem reference points: (t along straight hem, perpendicular offset in mm).
# ref 3 (t=0.5) is the split / junction midpoint shared by both Bézier halves.
_HEM_NOTCH_PARAMS: tuple[tuple[float, float], ...] = (
    (1 / 6, -0.5 * CM),
    (2 / 6, 0.0 * CM),
    (3 / 6, 1.0 * CM),  # split point
    (4 / 6, 1.5 * CM),
    (5 / 6, 0.8 * CM),
)


@dataclass(frozen=True)
class _WideSleeveGeometry:
    """All computed geometry for the wide sleeve block, prior to part assembly."""

    # ── Key points ────────────────────────────────────────────────────────────
    cap_crown: Point
    cap_left: Point
    cap_right: Point
    hem_left: Point
    hem_right: Point

    # ── Auxiliary construction lines (straight triangle legs) ─────────────────
    cap_left_slope: Segment  # crown → cap_left
    cap_right_slope: Segment  # cap_right → crown

    # ── Sleeve cap Bézier stitch curves ───────────────────────────────────────
    cap_left_curve: CubicBezier
    cap_right_curve: CubicBezier

    # ── Rectangle body outline ────────────────────────────────────────────────
    left_side: CubicBezier
    hem: Segment
    hem_left_curve: CubicBezier
    hem_right_curve: CubicBezier
    right_side: CubicBezier

    # ── Cut line (construction reference only) ────────────────────────────────
    cut_seg: Segment

    # ── Optional feature markings ─────────────────────────────────────────────
    slit: Segment | None
    pleats: tuple[Pleat, ...]

    # ── Construction / debug reference points ─────────────────────────────────
    cap_left_notch_pts: tuple[Point, ...]
    cap_right_notch_pts: tuple[Point, ...]
    hem_ref_pts: tuple[Point, ...]

    # ── Cap notch points (set when armhole is supplied) ───────────────────────
    front_armscye_notch_on_cap: Point | None  # front armscye notch on left cap curve
    shoulder_on_cap: Point | None  # shoulder alignment notch on left cap curve
    back_armscye_notch_on_cap: Point | None  # back armscye notch on right cap curve


# ---------------------------------------------------------------------------
# Cuff geometry
# ---------------------------------------------------------------------------

_BUTTON_MIN_MARGIN: float = 10.0  # mm — min distance from top edge / fold line (1 cm)
_BUTTON_MIN_SIDE: float = 5.0  # mm — min distance from section boundaries (0.5 cm)


@dataclass(frozen=True)
class _CuffButtonRow:
    """Geometry for one button/buttonhole pair on the outer cuff face.

    For the two-button case (``num_buttons=2`` with underlap) *button2* holds the
    second button circle.  Both buttons share a single buttonhole mark and are
    placed at the same Y height.
    """

    button: Point  # centre of the first (or only) button circle
    button_radius: float  # circle radius in mm
    hole_start: Point  # left end of the buttonhole mark
    hole_end: Point  # right end of the buttonhole mark
    button2: Point | None = None  # second button (side-by-side); None for single-button rows


@dataclass(frozen=True)
class _CuffGeometry:
    """All computed geometry for the cuff pattern piece, prior to assembly."""

    # ── Dimensions ────────────────────────────────────────────────────────────
    cuff_length: float  # Bündchenlänge — flat circumference (mm)
    cuff_height: float  # single (folded) height — full cut height is 2× (mm)
    underlap: float  # width of left extension, 0 when absent (mm)
    overlap: float  # width of right extension, 0 when absent (mm)

    # ── Key outline points ────────────────────────────────────────────────────
    top_left: Point
    top_right: Point
    bottom_right: Point
    bottom_left: Point

    # ── Fold line ─────────────────────────────────────────────────────────────
    fold_left: Point
    fold_right: Point

    # ── Division line x-coordinates ──────────────────────────────────────────
    # main_left_x: x of the underlap|main boundary (= anchor.x + underlap)
    # main_right_x: x of the main|overlap boundary (= anchor.x + underlap + cuff_length)
    main_left_x: float
    main_right_x: float

    # ── Button / buttonhole rows (empty tuple when none configured) ───────────
    button_rows: tuple[_CuffButtonRow, ...]


def _build_button_rows(
    num_buttons: int,
    button_diameter: float,
    buttonhole_ease: float,
    margin: float,
    ax: float,
    ay: float,
    cuff_height: float,
    cuff_length: float,
    underlap: float,
    overlap: float,
) -> tuple[_CuffButtonRow, ...]:
    """Compute button and buttonhole positions for the outer cuff face.

    Always returns at most one _CuffButtonRow. Both button(s) and the single
    buttonhole are placed at the vertical midpoint of the cuff.

    For num_buttons=2 with an underlap wide enough for button_diameter, a second
    button is placed side-by-side (different X, same Y) via button2. Both
    buttons share a single buttonhole. Falls back to single-button layout when
    no adequate underlap is present.

    Placement rules:
      Only overlap:    button at main_right_x - overlap/2; buttonhole centred in overlap.
      Only underlap:   button AT main_left_x; buttonhole in cuff starting at main_left_x.
      Both laps:       button AT main_left_x; buttonhole AT main_right_x.
      No extensions:   both centred in main cuff body.
      num_buttons=2 + underlap: first button at centre of underlap, second at same
                                distance into cuff; single buttonhole per overlap rule.

    Returns:
        Tuple with a single _CuffButtonRow, or empty when height band is too small.
    """
    if num_buttons == 0:
        return ()

    # ── Y-position: always the single vertical midpoint ───────────────────────
    valid_min = ay + margin
    valid_max = ay + cuff_height - margin
    if valid_min >= valid_max:
        return ()

    y_mid = (valid_min + valid_max) / 2.0

    # ── Derived boundaries ────────────────────────────────────────────────────
    main_left_x = ax + underlap
    main_right_x = main_left_x + cuff_length
    buttonhole_length = button_diameter + buttonhole_ease
    half_hole = buttonhole_length / 2.0
    half_btn = button_diameter / 2.0
    has_underlap = underlap > 0
    has_overlap = overlap > 0

    # A cuff without any lap extension closes with elastic — no button closure
    # marks are needed or meaningful.
    if not has_underlap and not has_overlap:
        return ()

    # ── Button X position(s) ──────────────────────────────────────────────────
    button2: Point | None = None
    if num_buttons == 2 and underlap >= button_diameter:
        d = underlap / 2.0
        btn_x = ax + d  # centre of underlap
        button2 = Point(main_left_x + d, y_mid, "Button")  # same distance into cuff
    elif has_underlap:
        btn_x = main_left_x  # at the closure line
    else:  # has_overlap only
        # Button near LEFT edge so it aligns with the buttonhole when the
        # overlap folds closed (symmetric: both overlap/2 from their edge).
        btn_x = ax + overlap / 2.0

    # ── Buttonhole X position (always exactly one) ────────────────────────────
    if has_overlap and has_underlap:
        hole_center_x = main_right_x  # at the main|overlap closure line
    elif has_overlap:
        hole_center_x = main_right_x + overlap / 2.0  # centred in overlap
    else:  # has_underlap only
        # Buttonhole near RIGHT edge, one full underlap-width inward.
        hole_center_x = main_right_x - underlap

    return (
        _CuffButtonRow(
            button=Point(btn_x, y_mid, "Button"),
            button_radius=half_btn,
            hole_start=Point(hole_center_x - half_hole, y_mid, "Buttonhole Start"),
            hole_end=Point(hole_center_x + half_hole, y_mid, "Buttonhole End"),
            button2=button2,
        ),
    )


def _build_cuff_geometry(
    sleeve_config: SleeveConfig,
    anchor: Point,
) -> _CuffGeometry | None:
    """Compute the key points for the cuff pattern piece.

    Returns ``None`` when *sleeve_config* has no :attr:`~SleeveConfig.cuff_config`.

    Args:
        sleeve_config: Reads :attr:`~SleeveConfig.cuff_config`.
        anchor:        Top-left origin of the whole piece.

    Returns:
        Fully populated :class:`_CuffGeometry`, or ``None``.
    """
    cc = sleeve_config.cuff_config
    if cc is None:
        return None

    cuff_length = cc.length
    cuff_height = cc.width  # single (folded) height; full cut = 2×
    underlap = cc.underlap
    overlap = cc.overlap
    total_width = underlap + cuff_length + overlap
    total_height = 2.0 * cuff_height

    ax, ay = anchor.x, anchor.y

    # ── Button rows ───────────────────────────────────────────────────────────
    bc = cc.button_config
    if bc is not None and bc.num_buttons > 0:
        button_rows = _build_button_rows(
            num_buttons=bc.num_buttons,
            button_diameter=bc.button_diameter,
            buttonhole_ease=bc.buttonhole_ease,
            margin=bc.margin,
            ax=ax,
            ay=ay,
            cuff_height=cuff_height,
            cuff_length=cuff_length,
            underlap=underlap,
            overlap=overlap,
        )
    else:
        button_rows = ()

    return _CuffGeometry(
        cuff_length=cuff_length,
        cuff_height=cuff_height,
        underlap=underlap,
        overlap=overlap,
        top_left=Point(ax, ay, "Cuff TL"),
        top_right=Point(ax + total_width, ay, "Cuff TR"),
        bottom_right=Point(ax + total_width, ay + total_height, "Cuff BR"),
        bottom_left=Point(ax, ay + total_height, "Cuff BL"),
        fold_left=Point(ax, ay + cuff_height, "Fold Left"),
        fold_right=Point(ax + total_width, ay + cuff_height, "Fold Right"),
        main_left_x=ax + underlap,
        main_right_x=ax + underlap + cuff_length,
        button_rows=button_rows,
    )


def _build_wide_sleeve_geometry(
    grid: WideSleeveGrid,
    sleeve_config: SleeveConfig,
    armhole: SleeveArmhole | None = None,
) -> _WideSleeveGeometry:
    """Build all geometric elements for the wide sleeve block.

    Computes key intersection points, applies hem shortening, fits the cap and
    hem Béziers, and resolves the slit / pleat markings.  The result is a pure
    data object — no :class:`~sewpat.pattern.PatternPart` is touched.

    Args:
        grid:          Constructed wide sleeve grid with all construction lines.
        sleeve_config: Garment config — slit height, pleat config, cuff dims.
        armhole:       Optional armhole seam data used to fit the cap curve.

    Returns:
        Fully populated :class:`_WideSleeveGeometry`.
    """
    # ── Key intersection points ──────────────────────────────────��────────────
    cap_left = intersect(grid.left_sleeve, grid.cap_line)[0]
    cap_right = intersect(grid.right_sleeve, grid.cap_line)[0]
    hem_left = intersect(grid.left_sleeve, grid.hem_line)[0]
    hem_right = intersect(grid.right_sleeve, grid.hem_line)[0]

    # ── Hem shortening — symmetric around the centre fold ─────────────────────
    # Shorten by (full_width − cuff_width) / 2 on each side using arc-length
    # projection so the result is orientation-independent.
    sleeve_hem_width = grid.construction_measures.sleeve_hem_width
    if sleeve_hem_width is not None:
        shortening = (2 * grid.sleeve_width - sleeve_hem_width) / 2
        if shortening > 0:
            hem_raw = Segment(hem_left, hem_right)
            hem_left = hem_raw.point_along_from(hem_left, shortening)
            hem_right = hem_raw.point_along_from(hem_right, -shortening)

    # ── Cap crown (apex) ──────────────────────────────────────────────────────
    crown_y = grid.cap_line.p1.y - grid.cap_height
    cap_crown = Point(grid.center_sleeve.p1.x, crown_y, "Cap Crown")

    # ── Auxiliary construction lines ──────────────────────────────────────────
    cap_left_slope = Segment(cap_crown, cap_left, "Cap Left Slope")
    cap_right_slope = Segment(cap_right, cap_crown, "Cap Right Slope")

    # ── Precision reference points along the cap slopes ───────────────────────
    cap_left_notch_pts = tuple(
        cap_left_slope.point_perpendicular(off, t=t) for t, off in _CAP_LEFT_NOTCH_PARAMS
    )
    cap_right_notch_pts = tuple(
        cap_right_slope.point_perpendicular(off, t=t) for t, off in _CAP_RIGHT_NOTCH_PARAMS
    )

    # ── Sleeve cap Bézier stitch curves ───────────────────────────────────────
    cap_left_curve = fit_cubic_bezier(cap_left, cap_crown, cap_left_notch_pts).set_name(
        "Cap Left Curve"
    )
    cap_right_curve = fit_cubic_bezier(cap_right, cap_crown, cap_right_notch_pts).set_name(
        "Cap Right Curve"
    )

    # ── Rectangle body ────────────────────────────────────────────────────────
    # Side seams: gently curved 1 cm inward at mid-height.
    # A temporary straight segment is used to find the perpendicular reference
    # point; unit_normal is the left-hand normal, so negative distance moves
    # inward (toward the sleeve centre) for both sides.
    _left_straight = Segment(cap_left, hem_left)
    _left_mid = _left_straight.point_perpendicular(distance=-1.0 * CM, t=0.5)
    left_side = fit_cubic_bezier_free(cap_left, hem_left, [_left_mid], [0.5]).set_name("Left Side")

    hem = Segment(hem_left, hem_right, "Hem")

    _right_straight = Segment(hem_right, cap_right)
    _right_mid = _right_straight.point_perpendicular(distance=-1.0 * CM, t=0.5)
    right_side = fit_cubic_bezier_free(hem_right, cap_right, [_right_mid], [0.5]).set_name(
        "Right Side"
    )

    # ── Shaped hem Bézier — split at midpoint (ref 3) for exact fit ───────────
    # Each half is fitted with its two interior refs at t=1/3 and t=2/3,
    # giving a square 2×2 system solved exactly through all 5 reference points.
    hem_ref_pts = tuple(hem.point_perpendicular(off, t=t) for t, off in _HEM_NOTCH_PARAMS)
    mid_hem = hem_ref_pts[2]
    hem_left_curve = fit_cubic_bezier_free(
        hem_left,
        mid_hem,
        [hem_ref_pts[0], hem_ref_pts[1]],
        t_params=(1 / 3, 2 / 3),
    ).set_name("Hem Left")
    hem_right_curve = fit_cubic_bezier_free(
        mid_hem,
        hem_right,
        [hem_ref_pts[3], hem_ref_pts[4]],
        t_params=(1 / 3, 2 / 3),
    ).set_name("Hem Right")

    # ── Direction vector: hem edge → sleeve interior ──────────────────────────
    # center_sleeve runs cap→hem; negate to get the hem→cap (inward) direction.
    _dc = grid.center_sleeve.unit_direction
    d_up = Point(-float(_dc[0]), -float(_dc[1]))

    # slit_bottom is always hem_ref_pts[3] (4/6 of hem, 1.5 cm outward).
    slit_bottom = hem_ref_pts[3]

    # ── Slit — parallel to the centre sleeve line at the 4/6 position ─────────
    slit: Segment | None = None
    if sleeve_config.slit_height is not None and sleeve_config.slit_height > 0:
        slit_top = slit_bottom + d_up * sleeve_config.slit_height
        slit = Segment(slit_bottom, slit_top, "Slit")

    # ── Pleats — left and right of the slit ───────────────────────────────────
    pleats: tuple[Pleat, ...]
    if (
        slit is not None
        and sleeve_config.pleat_config is not None
        and sleeve_config.pleat_config.num_pleats > 0
        and sleeve_config.pleat_config.depth > 0
    ):
        hem_base = split_bezier_seam_fn(
            hem_left_curve, hem_right_curve, hem.project_length(hem_right)
        )
        slit_proj = hem.project_length(slit_bottom)
        pleats = tuple(
            Pleat.build_along_seam(
                sleeve_config.pleat_config,
                hem,
                hem_base,
                slit_proj,
                d_up,
            )
        )
    else:
        pleats = ()

    # ── Cut line (sleeve length — construction reference only) ────────────────
    cut_left = intersect(grid.left_sleeve, grid.sleeve_length_line)[0]
    cut_right = intersect(grid.right_sleeve, grid.sleeve_length_line)[0]
    cut_seg = Segment(cut_left, cut_right, "Sleeve Length")

    # ── Cap notch points (requires armhole geometry) ──────────────────────────
    # Each distance is measured from the side-seam corner of the respective
    # cap curve (cap_left for front / left, cap_right for back / right).
    # Sleeve ease is split ¼ front + ¼ back; the remaining ½ stays at the crown.
    front_armscye_notch_on_cap: Point | None = None
    shoulder_on_cap: Point | None = None
    back_armscye_notch_on_cap: Point | None = None

    if armhole is not None:
        _cap_seam = seam_length([cap_left_curve, cap_right_curve])
        _sleeve_ease = _cap_seam - grid.construction_measures.armscye_circumference
        _ease_q = 0.25 * _sleeve_ease  # ¼ of ease distributed to each side

        # Front armscye notch: same arc distance from cap_left as front_armscye_notch
        # has from the side-seam end of front_armscye.
        _d_front = armhole.front_armscye.arc_length_from_end(armhole.front_armscye_notch)
        if 0.0 < _d_front < cap_left_curve.length:
            _p = cap_left_curve.point_at_length(_d_front)
            front_armscye_notch_on_cap = Point(_p.x, _p.y, "Front Armscye Notch")

        # Shoulder notch — front armscye full length + ¼ ease from cap_left.
        _d_shoulder = armhole.front_armscye.length + _ease_q
        if 0.0 < _d_shoulder < cap_left_curve.length:
            _p = cap_left_curve.point_at_length(_d_shoulder)
            shoulder_on_cap = Point(_p.x, _p.y, "Shoulder Notch")

        # Back armscye notch: back_armscye_lower.length + ¼ ease from cap_right.
        _d_back = armhole.back_armscye_lower.length + _ease_q
        if 0.0 < _d_back < cap_right_curve.length:
            _p = cap_right_curve.point_at_length(_d_back)
            back_armscye_notch_on_cap = Point(_p.x, _p.y, "Back Armscye Notch")

    return _WideSleeveGeometry(
        cap_crown=cap_crown,
        cap_left=cap_left,
        cap_right=cap_right,
        hem_left=hem_left,
        hem_right=hem_right,
        cap_left_slope=cap_left_slope,
        cap_right_slope=cap_right_slope,
        cap_left_curve=cap_left_curve,
        cap_right_curve=cap_right_curve,
        left_side=left_side,
        hem=hem,
        hem_left_curve=hem_left_curve,
        hem_right_curve=hem_right_curve,
        right_side=right_side,
        cut_seg=cut_seg,
        slit=slit,
        pleats=pleats,
        cap_left_notch_pts=cap_left_notch_pts,
        cap_right_notch_pts=cap_right_notch_pts,
        hem_ref_pts=hem_ref_pts,
        front_armscye_notch_on_cap=front_armscye_notch_on_cap,
        shoulder_on_cap=shoulder_on_cap,
        back_armscye_notch_on_cap=back_armscye_notch_on_cap,
    )
