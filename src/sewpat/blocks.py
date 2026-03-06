"""Pre-built garment blocks for common pattern types.

Each block is a pair of frozen dataclasses — one per pattern piece — bundled
in a thin container class that mirrors the :class:`~sewpat.grids.TopGrid`
convention.  Callers never touch fragile string lookups; every key point and
edge is a typed, named attribute with full IDE autocomplete.

Example::

    from sewpat.blocks import TopBlock
    from sewpat.fitclass import FitClass
    from sewpat.measurements import GarmentConfig

    fc    = FitClass(pk=4)
    cfg   = GarmentConfig(length=75 * CM)

    block = TopBlock.from_measurements(meas, fc, hip_offset=1*CM, config=cfg)
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    # Extend the armscye edge with a collar:
    pt_collar = block.back.armscye_control.translate(0, -2 * CM)
"""

from dataclasses import dataclass

from .geometry import (
    Circle,
    CubicBezier,
    Dart,
    DartType,
    Line,
    Point,
    Ray,
    Segment,
    intersect,
)
from .grids import TopGrid
from .measurements import (
    BlouseMeasurements,
    GarmentConfig,
    calculate_hip_distribution,
    calculate_waist_distribution,
)
from .pattern import PatternConfig, PatternPart
from .person import Gender, PersonalAdjustments
from .style import STYLE_HEM, STYLE_STITCH, STYLE_STITCH_BEVEL
from .units import CM

# ---------------------------------------------------------------------------
# Construction constants
# These are pattern-drafting constants that encode standard ease/lift values.
# ---------------------------------------------------------------------------


#: Back neck depth — how far the back neckline drops below the shoulder line, always constant.
_NECK_DEPTH: float = 2.0 * CM

#: Ease added to / subtracted from the shoulder seam, always constant.
_SHOULDER_EASE: float = 1.0 * CM

#: Front neckline offset added to the measured neck-to-bust depth.
_NECKLINE_EASE: float = 1.5 * CM

#: Armscye-front control-point offsets (X, Y).
_ARMSCYE_FRONT_CP_X: float = -5.0 * CM
_ARMSCYE_FRONT_CP_Y: float = -3.0 * CM

#: Length of the control-point tangent for the side-hip Bézier curves.
_SIDE_HIP_TANGENT: float = 15.0 * CM

#: Distance from the waist dart centre to its lower (hem-side) tip — back.
_WAIST_DART_BACK_LOWER_TIP: float = 16.0 * CM

#: Distance from the waist dart centre to its lower (hem-side) tip — front.
_WAIST_DART_FRONT_LOWER_TIP: float = 12.0 * CM

#: How far the waist construction line is raised above the actual waist grid line.
_WAIST_OFFSET: float = 1.0 * CM

#: Checkpoint for the back armscye curve, placed on the shoulder hight at a fixed distance from the armscye line, (german: HP)
_ARMSCYE_BACK_OFFSET: float = 1 * CM

#: Back armscye Bézier control-point offsets (cp1_x, cp2_x, cp_y).
_ARMSCYE_BACK_CP1_X: float = -0.5 * CM
_ARMSCYE_BACK_CP2_X: float = -1.5 * CM
_ARMSCYE_BACK_CP_Y:  float =  3.0 * CM


# ---------------------------------------------------------------------------
# Internal geometry containers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _BackGeometry:
    """All computed geometry for the back piece, prior to assembly."""

    # Key points
    anchor: Point
    hem_center_back: Point
    waist_center_back: Point
    hip_center_back: Point
    waist_center_back_adj: Point
    hip_center_back_adj: Point
    hem_center_back_adj: Point
    armscye_back_chest: Point
    side_back_chest: Point
    armscye_back_shoulder: Point
    armscye_back_shoulder_raised: Point
    neck_back_shoulder: Point
    shoulder_back_neckline: Point
    shoulder_dart_notch: Point
    shoulder_blade_dart_tip: Point
    armscye_control: Point   # armscye notch (pt_hÄP)

    # Curves and segments
    armscye_back: CubicBezier
    neckline_back: CubicBezier
    shoulder_back: Segment
    shoulder_back_orig: Segment
    shoulder_blade: Line


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
    shoulder_armscye_end: Point
    shoulder_neckline_start: Point
    armscye_control: Point   # armscye notch (pt_vÄP)

    # Curves and segments
    armscye_front_lower: CubicBezier
    armscye_front_upper: CubicBezier | None
    neckline_front: CubicBezier
    neckline_front_stub: CubicBezier | None
    shoulder_armscye: Segment
    shoulder_neckline: Segment
    shoulder_front_aux_orig: Segment
    shoulder_front_dart_orig: Segment


@dataclass(frozen=True)
class _SideSeams:
    """Side-seam geometry shared between the two pieces."""

    # Back
    waist_indent_back: Point
    hip_side_back: Point
    side_chest_waist_back: Segment
    side_waist_hip_back: CubicBezier
    side_hip_hem_back: Segment
    hem_side_to_center_back: Segment

    # Front
    waist_indent_front: Point
    hip_side_front: Point
    side_chest_waist_front: Segment
    side_waist_hip_front: CubicBezier
    side_hip_hem_front: Segment
    hem_side_to_center_front: Segment

    # Construction lines
    waist_offset: "Line"


@dataclass(frozen=True)
class _Darts:
    """All dart objects for both pieces."""

    waist_dart_back: Dart
    waist_dart_front: Dart
    shoulder_dart_front: Dart


# ---------------------------------------------------------------------------
# Private geometry builders
# ---------------------------------------------------------------------------

def _build_back_geometry(
    grid: TopGrid,
    meas: BlouseMeasurements,
    anchor: Point,
    hip_offset: float,
    shoulder_raise: float,
    shoulder_gather: float,
) -> _BackGeometry:
    """Compute all key points and curves for the back piece."""

    hem_center_back          = intersect(grid.center_back, grid.hem)[0]
    waist_center_back        = intersect(grid.center_back, grid.waist)[0]
    hip_center_back          = intersect(grid.center_back, grid.hip)[0]
    waist_center_back_adj    = waist_center_back.translate(hip_offset, 0)
    hip_center_back_adj      = hip_center_back.translate(hip_offset, 0)
    hem_center_back_adj      = hem_center_back.translate(hip_offset, 0)

    armscye_chest        = intersect(grid.armscye_back,  grid.chest)[0]
    side_chest           = intersect(grid.side_back,     grid.chest)[0]
    armscye_shoulder     = intersect(grid.armscye_back,  grid.shoulder_back)[0]
    neck_shoulder        = intersect(grid.shoulder_back, grid.neck)[0]
    armscye_shoulder_raised = armscye_shoulder.translate(0, shoulder_raise)

    # Shoulder seam
    shoulder_neckline    = neck_shoulder.translate(0, -_NECK_DEPTH)
    dart_notch           = (
        Segment(armscye_shoulder_raised, armscye_chest)
        .point_at_t(0.5)
        .translate(_ARMSCYE_BACK_OFFSET, 0)
    )
    shoulder_blade = Line(dart_notch, (1, 0), name="Shoulder Blade")
    armscye_control = (
        Segment(armscye_shoulder_raised, armscye_chest)
        .point_at_t(0.75)
        .translate(_NECKLINE_EASE, 0)
    )
    shoulder_orig = Segment.from_direction(
        shoulder_neckline,
        armscye_shoulder_raised,
        length=meas.shoulder_width + shoulder_gather,
    )
    shoulder = shoulder_orig.offset(-_SHOULDER_EASE)

    blade_dart_tip = intersect(grid.dart_back, shoulder_blade)[0]

    # Armscye curve
    armscye = CubicBezier(
        side_chest,
        armscye_control.translate(_ARMSCYE_BACK_CP1_X, _ARMSCYE_BACK_CP_Y),
        armscye_control.translate(_ARMSCYE_BACK_CP2_X, _ARMSCYE_BACK_CP_Y),
        shoulder.p2,
    )

    # Neckline curve
    neckline = CubicBezier(
        anchor,
        anchor,
        neck_shoulder,
        shoulder.p1,
        name="Neckline Back",
    )

    return _BackGeometry(
        anchor=anchor,
        hem_center_back=hem_center_back,
        waist_center_back=waist_center_back,
        hip_center_back=hip_center_back,
        waist_center_back_adj=waist_center_back_adj,
        hip_center_back_adj=hip_center_back_adj,
        hem_center_back_adj=hem_center_back_adj,
        armscye_back_chest=armscye_chest,
        side_back_chest=side_chest,
        armscye_back_shoulder=armscye_shoulder,
        armscye_back_shoulder_raised=armscye_shoulder_raised,
        neck_back_shoulder=neck_shoulder,
        shoulder_back_neckline=shoulder_neckline,
        shoulder_dart_notch=dart_notch,
        shoulder_blade_dart_tip=blade_dart_tip,
        armscye_control=armscye_control,
        armscye_back=armscye,
        neckline_back=neckline,
        shoulder_back=shoulder,
        shoulder_back_orig=shoulder_orig,
        shoulder_blade=shoulder_blade,
    )


def _build_front_geometry(
    grid: TopGrid,
    meas: BlouseMeasurements,
    back: _BackGeometry,
) -> _FrontGeometry:
    """Compute all key points and curves for the front piece."""

    side_front_chest    = intersect(grid.side_front,   grid.chest)[0]
    armscye_front_chest = intersect(grid.armscye_front, grid.chest)[0]

    # Bust point
    bust_point_shoulder_line = intersect(grid.shoulder_front, grid.bust_point)[0]
    bust_point = bust_point_shoulder_line.translate(0, meas.bust_depth)

    # Neckline anchor points
    center_front_shoulder_line = intersect(grid.center_front, grid.shoulder_front)[0]
    neckline_front_start       = center_front_shoulder_line.translate(0, meas.neck_size + _NECKLINE_EASE)
    shoulder_front_neckline_pt = center_front_shoulder_line.translate(-meas.neck_size, 0)

    # Armscye / shoulder construction
    armscye_control = armscye_front_chest.translate(0, -0.25 * meas.armscye_width)
    arm_seam_length = (
        Segment(back.armscye_back_shoulder_raised, back.armscye_back_chest).length
        - 2 * CM # fixed constant
    )
    armscye_front_chest_upper = armscye_front_chest.translate(0, -arm_seam_length)
    shoulder_upper_pt = Circle(armscye_front_chest, arm_seam_length).point_along_from(
        armscye_front_chest_upper, -(meas.bust / 20 + _ARMSCYE_FIT) # _ARMSCYE_FIT in 0, 1. o regular 1 tight fit
    )
    shoulder_front_pivot = intersect(
        Circle(bust_point, meas.bust_depth),
        Circle(shoulder_upper_pt, meas.shoulder_width),
    )[0]
    shoulder_front_aux_seg = Segment(shoulder_front_pivot, shoulder_upper_pt)
    shoulder_armscye_end = shoulder_front_aux_seg.point_along_from(
        shoulder_front_pivot,
        Segment(shoulder_front_neckline_pt, bust_point_shoulder_line).length,
    )
    shoulder_neckline_start = bust_point.translate(
        0, -Segment(bust_point, shoulder_armscye_end).length
    )
    shoulder_armscye   = Segment(shoulder_upper_pt, shoulder_armscye_end).offset(_SHOULDER_EASE)
    _shoulder_neckline_raw = Segment(shoulder_neckline_start, shoulder_front_neckline_pt).offset(
        _SHOULDER_EASE
    )

    # Neckline front Bézier — split at shoulder_neckline ray
    neckline_front_full = CubicBezier(
        neckline_front_start,
        neckline_front_start,
        center_front_shoulder_line.translate(-meas.neck_size, meas.neck_size),
        shoulder_front_neckline_pt,
    )
    _short_ray = Ray(_shoulder_neckline_raw.p1, _shoulder_neckline_raw.unit_direction)
    _neckline_intersections = intersect(neckline_front_full, _short_ray)
    if _neckline_intersections:
        _ix = _neckline_intersections[0]
        shoulder_neckline = Segment(_shoulder_neckline_raw.p1, _ix)
        _neckline_split = neckline_front_full.split_at_points([_ix])
        _nf = _neckline_split[0]
        neckline_front = CubicBezier(_nf.p0, _nf.p1, _nf.p2, _ix)
        neckline_front_stub = _neckline_split[1] if len(_neckline_split) > 1 else None
    else:
        shoulder_neckline = _shoulder_neckline_raw
        neckline_front = neckline_front_full
        neckline_front_stub = None

    # Armscye front curve — split at shoulder_armscye.p1 (the offset shoulder-
    # seam point that projects onto the armscye curve), separating the short
    # construction cap (upper) from the visible stitch armscye (lower).
    armscye_front_full = CubicBezier(
        shoulder_upper_pt,
        bust_point.translate(_ARMSCYE_FRONT_CP_X, _ARMSCYE_FRONT_CP_Y),
        side_front_chest.translate(meas.armscye_width * 0.05, 0),
        side_front_chest,
    )
    _armscye_split = armscye_front_full.split_at_points([shoulder_armscye.p1])
    if len(_armscye_split) > 1:
        armscye_front_upper = _armscye_split[0]
        armscye_front_lower = _armscye_split[1]
    else:
        armscye_front_upper = None
        armscye_front_lower = armscye_front_full

    return _FrontGeometry(
        side_front_chest=side_front_chest,
        armscye_front_chest=armscye_front_chest,
        bust_point=bust_point,
        neckline_front_start=neckline_front_start,
        center_front_shoulder_line=center_front_shoulder_line,
        shoulder_front_neckline_pt=shoulder_front_neckline_pt,
        shoulder_armscye_end=shoulder_armscye_end,
        shoulder_neckline_start=shoulder_neckline_start,
        armscye_control=armscye_control,
        armscye_front_lower=armscye_front_lower,
        armscye_front_upper=armscye_front_upper,
        neckline_front=neckline_front,
        neckline_front_stub=neckline_front_stub,
        shoulder_armscye=shoulder_armscye,
        shoulder_neckline=shoulder_neckline,
        shoulder_front_aux_orig=Segment(shoulder_front_pivot, shoulder_upper_pt),
        shoulder_front_dart_orig=Segment(shoulder_front_neckline_pt, shoulder_neckline_start),
    )


def _build_side_seams(
    grid: TopGrid,
    meas: BlouseMeasurements,
    back: _BackGeometry,
    front: _FrontGeometry,
    wd: "WaistDistribution",
    hd: "HipDistribution",
) -> _SideSeams:
    """Compute side-seam points and curves for both pieces."""

    waist_offset = grid.waist.offset(-_WAIST_OFFSET).set_name("Waist Offset")

    # Raised waist points (side_seam_intake = side-seam waist take-in)
    waist_indent_back  = intersect(grid.side_back,  waist_offset)[0].translate(-wd.side_seam_intake, 0)
    waist_indent_front = intersect(grid.side_front, waist_offset)[0].translate( wd.side_seam_intake, 0)

    side_chest_waist_back  = Segment(waist_indent_back,  back.side_back_chest,   name="Side Seam Back Upper")
    side_chest_waist_front = Segment(waist_indent_front, front.side_front_chest, name="Side Seam Front Upper")

    # Hip outset (hip_shortfall = hip shortfall correction)
    side_back_offset  = grid.side_back.offset(  hd.hip_shortfall)
    side_front_offset = grid.side_front.offset(-hd.hip_shortfall)
    hip_side_back  = intersect(grid.hip, side_back_offset )[0]
    hip_side_front = intersect(grid.hip, side_front_offset)[0]

    # Curved hip section
    side_waist_hip_back = CubicBezier(
        waist_indent_back,
        intersect(grid.side_back, waist_offset)[0].translate(-hd.hip_shortfall, _SIDE_HIP_TANGENT),
        hip_side_back,
        hip_side_back,
        name="Side Hip Curve Back",
    )
    side_waist_hip_front = CubicBezier(
        waist_indent_front,
        intersect(grid.side_front, waist_offset)[0].translate(hd.hip_shortfall, _SIDE_HIP_TANGENT),
        hip_side_front,
        hip_side_front,
        name="Side Hip Curve Front",
    )

    # Straight hem section
    hem_depth = Segment(back.hip_center_back_adj, back.hem_center_back_adj).length
    side_hip_hem_back  = Segment(hip_side_back,  hip_side_back.translate( 0, hem_depth), name="Side Hem Back")
    side_hip_hem_front = Segment(hip_side_front, hip_side_front.translate(0, hem_depth), name="Side Hem Front")

    # Bottom hem edges (from side to centre)
    hem_side_to_center_back = Segment(
        intersect(grid.hem, side_back_offset)[0],
        back.hem_center_back_adj,
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
        waist_offset=waist_offset,
    )


def _build_darts(
    grid: TopGrid,
    meas: BlouseMeasurements,
    back: _BackGeometry,
    front: _FrontGeometry,
    armscye_back_elem: "PatternPart",
    wd: "WaistDistribution",
) -> "_Darts":
    """Build all dart objects for both pieces."""

    # Back waist dart
    waist_dart_back_center = intersect(grid.waist, grid.dart_back)[0]
    waist_dart_back = Dart.from_tip_center_width(
        tip=intersect(grid.dart_back, grid.chest)[0],
        center=waist_dart_back_center,
        width=wd.back_dart_width,
        dart_type=DartType.RHOMBUS,
        second_tip=waist_dart_back_center.translate(0, _WAIST_DART_BACK_LOWER_TIP),
    ).set_name("Waist Dart Back")

    # Front waist dart
    bust_point_waist = intersect(grid.bust_point, grid.waist)[0]
    waist_dart_front = Dart.from_tip_center_width(
        tip=front.bust_point,
        center=bust_point_waist,
        width=wd.front_dart_width,
        dart_type=DartType.RHOMBUS,
        second_tip=bust_point_waist.translate(0, _WAIST_DART_FRONT_LOWER_TIP),
    ).set_name("Waist Dart Front")

    # Front shoulder dart
    shoulder_dart_front = Dart.from_tip_and_legs(
        front.bust_point,
        front.shoulder_neckline.p1,
        front.shoulder_armscye.p2,
    ).set_name("Shoulder Dart Front")

    # Back shoulder dart (needs the appended armscye edge element)
    shoulder_dart_back = Dart.from_edge_at_legs(
        armscye_back_elem,
        leg_a=back.shoulder_dart_notch,
        leg_b=back.armscye_back.point_along_from(back.shoulder_dart_notch, _NECKLINE_EASE),
        tip=back.shoulder_blade_dart_tip,
        name="Shoulder Dart Back",
    )

    return _Darts(
        waist_dart_back=waist_dart_back,
        waist_dart_front=waist_dart_front,
        shoulder_dart_front=shoulder_dart_front,
    ), shoulder_dart_back


def _assemble_back_part(
    part: PatternPart,
    back: _BackGeometry,
    sides: _SideSeams,
    darts: _Darts,
    shoulder_dart_back: Dart,
    seam_allowance: float,
) -> None:
    """Add all elements to the back PatternPart in drawing order.

    Note: ``back.armscye_back`` is **not** appended here — it was already
    appended in :meth:`TopBlock.from_measurements` before
    :func:`_build_darts` is called, so that :class:`~sewpat.geometry.Dart`
    can reference the live ``PatternElement`` for the in-place edge split.
    Appending it a second time would corrupt the outline polygon and produce
    wrong SA corners at the shoulder/armscye junction.
    """
    part.append(Segment(back.anchor, back.waist_center_back_adj,       name="Center Back"),     style=STYLE_STITCH, is_outline=True)
    part.append(Segment(back.waist_center_back_adj, back.hem_center_back_adj, name="Center Back Hem"), style=STYLE_STITCH, is_outline=True)
    part.append(
        back.neckline_back,
        style=STYLE_STITCH_BEVEL,
        is_outline=True,
    )
    part.append(back.shoulder_back_orig.set_name("Shoulder Back Orig"), is_construction=True)
    part.append(back.shoulder_blade,                                     is_construction=True)
    part.append(back.shoulder_back.set_name("Shoulder Back"),           style=STYLE_STITCH, is_outline=True)
    part.add_dart(shoulder_dart_back)
    part.append(sides.side_chest_waist_back,                            style=STYLE_STITCH, is_outline=True)
    part.add_dart(darts.waist_dart_back)
    part.append(sides.waist_offset,                                     is_construction=True)
    part.append(sides.side_waist_hip_back,                              is_outline=True, style=STYLE_STITCH)
    part.append(sides.side_hip_hem_back,                                style=STYLE_STITCH, is_outline=True)
    part.append(sides.hem_side_to_center_back,                          style=STYLE_HEM, is_outline=True)

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)
    part.add_notches(back.armscye_control, seam_edge=back.armscye_back)


def _assemble_front_part(
    part: PatternPart,
    front: _FrontGeometry,
    sides: _SideSeams,
    darts: _Darts,
    grid: TopGrid,
    seam_allowance: float,
) -> None:
    """Add all elements to the front PatternPart in drawing order."""

    part.append(
        Segment(
            front.neckline_front_start,
            intersect(grid.center_front, grid.hem)[0],
            name="Center Front",
        ),
        style=STYLE_STITCH_BEVEL,
        is_outline=True,
    )
    part.append(front.neckline_front.set_name("Neckline Front"),                style=STYLE_STITCH, is_outline=True)
    if front.neckline_front_stub is not None:
        part.append(front.neckline_front_stub.set_name("Neckline Front Stub"),  is_construction=True)
    part.append(front.shoulder_front_aux_orig.set_name("Shoulder Front Orig"),  is_construction=True)
    part.append(front.shoulder_front_dart_orig.set_name("Shoulder Front Dart Orig"), is_construction=True)
    part.append(front.shoulder_armscye.set_name("Shoulder Front"),               style=STYLE_STITCH, is_outline=True)
    part.append(front.shoulder_neckline.set_name("Shoulder Front Dart"),         style=STYLE_STITCH, is_outline=True)
    part.add_dart(darts.shoulder_dart_front)
    if front.armscye_front_upper is not None:
        part.append(front.armscye_front_upper.set_name("Armscye Front Upper"),  is_construction=True)
    part.append(front.armscye_front_lower.set_name("Armscye Front"),              style=STYLE_STITCH, is_outline=True)
    part.append(sides.side_chest_waist_front,                                    style=STYLE_STITCH, is_outline=True)
    part.add_dart(darts.waist_dart_front)
    part.append(sides.side_waist_hip_front,                                      is_outline=True, style=STYLE_STITCH)
    part.append(sides.side_hip_hem_front,                                        style=STYLE_STITCH, is_outline=True)
    part.append(sides.hem_side_to_center_front,                                  style=STYLE_HEM, is_outline=True)

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)
    part.add_notches(front.armscye_control, seam_edge=front.armscye_front_lower)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TopBlockBack:
    """The back piece of a sleeveless women's waisted-top block.

    Attributes:
        part: The :class:`~sewpat.pattern.PatternPart` ready to add to a
            :class:`~sewpat.pattern.Pattern`.  It already contains all outline
            segments, darts, and — when *seam_allowance* > 0 — the SA offset.
        armscye: Armscye curve of the back piece (armscye intersection → shoulder).
        neckline: Neckline Bézier curve of the back piece.
        shoulder: Shoulder seam (parallel-offset construction line).
        side_chest_waist: Straight side-seam segment from raised waist
            point to the armscye.
        side_waist_hip: Curved side-seam section from raised waist point to
            the hip (waist_indent → side_hip).
        side_hip_hem: Straight side-seam section from hip to hem
            (side_hip → hem).
        waist_dart: Rhombus waist dart geometry.
        shoulder_dart: Triangle shoulder dart cut into the armscye.
        armscye_control: Armscye notch reference point on the back armscye edge.
        waist_indent: Raised waist point at the back side seam
            (after SaEinzug correction).
        hip_outset: Hip point at the back side seam shifted outward
            (after Fehlbetrag correction).
    """

    part: PatternPart
    armscye: CubicBezier
    neckline: CubicBezier
    shoulder: Segment
    side_chest_waist: Segment
    side_waist_hip: CubicBezier
    side_hip_hem: Segment
    waist_dart: Dart
    shoulder_dart: Dart
    armscye_control: Point
    waist_indent: Point
    hip_outset: Point


@dataclass(frozen=True)
class TopBlockFront:
    """The front piece of a sleeveless women's waisted-top block.

    Attributes:
        part: The :class:`~sewpat.pattern.PatternPart` ready to add to a
            :class:`~sewpat.pattern.Pattern`.  It already contains all outline
            segments, darts, and — when *seam_allowance* > 0 — the SA offset.
        armscye: Armscye curve of the front piece, lower section
            (shoulder endpoint → side-chest intersection).
        neckline: Neckline Bézier curve of the front piece.
        shoulder_armscye: Long shoulder seam running toward the armscye (from bust-point pivot side).
        shoulder_neckline: Short shoulder seam running toward the neckline (dart side).
        side_chest_waist: Straight side-seam segment from raised waist
            point to the armscye.
        side_waist_hip: Curved side-seam section from raised waist point to
            the hip (waist_indent → side_hip).
        side_hip_hem: Straight side-seam section from hip to hem
            (side_hip → hem).
        waist_dart: Rhombus waist dart geometry.
        shoulder_dart: Triangle shoulder dart (bust-dart rotated to shoulder).
        armscye_control: Armscye notch reference point on the front armscye edge.
        waist_indent: Raised waist point at the front side seam
            (after SaEinzug correction).
        hip_outset: Hip point at the front side seam shifted outward
            (after Fehlbetrag correction).
        bust_point: Bust point.
    """

    part: PatternPart
    armscye: CubicBezier
    neckline: CubicBezier
    shoulder_armscye: Segment
    shoulder_neckline: Segment
    side_chest_waist: Segment
    side_waist_hip: CubicBezier
    side_hip_hem: Segment
    waist_dart: Dart
    shoulder_dart: Dart
    armscye_control: Point
    waist_indent: Point
    hip_outset: Point
    bust_point: Point


@dataclass(frozen=True)
class TopBlock:
    """Both pieces of the sleeveless women's waisted-top block.

    Build via :meth:`TopBlock.from_measurements`; then add ``.back.part``
    and ``.front.part`` to your pattern.  All key points and edges on each
    piece are available as typed attributes with full IDE autocomplete.

    Example::

        block = TopBlock.from_measurements(meas, model, config)
        pattern.add_part(block.back.part)
        pattern.add_part(block.front.part)

        # Draw a new sleeve:
        armscye = CubicBezier(block.back.armscye.p0, ..., block.back.armscye_control)

    Attributes:
        back:  :class:`TopBlockBack` — the complete back piece with typed geometry.
        front: :class:`TopBlockFront` — the complete front piece with typed geometry.
    """

    back: TopBlockBack
    front: TopBlockFront

    @classmethod
    def from_measurements(
        cls,
        meas: BlouseMeasurements,
        config: GarmentConfig,
        fit_class: FitClass | None = None,
        adjustments: PersonalAdjustments | None = None,
        layout: PatternConfig = PatternConfig(),
        back_name: str = "Block Back",
        front_name: str = "Block Front",
    ) -> "TopBlock":
        """Build and return a :class:`TopBlock` from measurements.

        Args:
            meas:        Blouse measurements (ease already included).
            fit_class:   :class:`~sewpat.fitclass.FitClass` for construction offsets.
            adjustments: :class:`~sewpat.person.PersonalAdjustments` — provides
                         ``hip_offset`` and ``shoulder_raise``.
            config:      Garment-design choices (length, seam allowance).
            layout:      Pattern layout config (anchor, inter-piece margin).
            back_name:   Name for the back part.
            front_name:  Name for the front part.

        Returns:
            A :class:`TopBlock` with fully constructed ``.back`` and ``.front`` pieces.
        """
        adj              = adjustments or PersonalAdjustments()
        seam_allowance   = config.seam_allowance

        grid = TopGrid.from_measurements(
            meas=meas,
            fit_class=fit_class,
            hip_offset=adj.hip_offset,
            config=config,
            layout=layout,
        )

        # ── 1. Build geometry for each piece independently ───────────────────
        back_geom  = _build_back_geometry(grid, meas, layout.anchor, adj.hip_offset, adj.shoulder_raise, config.shoulder_gather)
        front_geom = _build_front_geometry(grid, meas, back_geom)

        # ── 2. Compute waist / hip distribution ──────────────────────────────
        wd = calculate_waist_distribution(
            meas,
            pt_waist_cf=intersect(grid.center_front, grid.waist)[0],
            pt_waist_sf=intersect(grid.side_front,   grid.waist)[0],
            pt_waist_sb=intersect(grid.side_back,    grid.waist)[0],
            pt_waist_cb=back_geom.waist_center_back_adj,
        )
        hd = calculate_hip_distribution(
            meas,
            pt_hip_cf=intersect(grid.center_front, grid.hip)[0],
            pt_hip_sf=intersect(grid.side_front,   grid.hip)[0],
            pt_hip_sb=intersect(grid.side_back,    grid.hip)[0],
            pt_hip_cb=back_geom.hip_center_back_adj,
        )

        # ── 3. Build shared side-seam geometry ───────────────────────────────
        sides = _build_side_seams(grid, meas, back_geom, front_geom, wd, hd)

        # ── 4. Assemble pieces and extract darts ─────────────────────────────
        block_back  = PatternPart(name=back_name)
        block_front = PatternPart(name=front_name)

        # Append the armscye first so we have the edge element for the shoulder dart
        armscye_back_elem = block_back.append(
            back_geom.armscye_back.set_name("Armscye Back"),
            style=STYLE_STITCH,
            is_outline=True,
        )
        darts, shoulder_dart_back = _build_darts(grid, meas, back_geom, front_geom, armscye_back_elem, wd)

        _assemble_back_part(block_back,  back_geom,  sides, darts, shoulder_dart_back, seam_allowance)
        _assemble_front_part(block_front, front_geom, sides, darts, grid, seam_allowance)

        # ── 5. Pack into public dataclasses and return ────────────────────────
        back = TopBlockBack(
            part=block_back,
            armscye=back_geom.armscye_back,
            neckline=back_geom.neckline_back,
            shoulder=back_geom.shoulder_back,
            side_chest_waist=sides.side_chest_waist_back,
            side_waist_hip=sides.side_waist_hip_back,
            side_hip_hem=sides.side_hip_hem_back,
            waist_dart=darts.waist_dart_back,
            shoulder_dart=shoulder_dart_back,
            armscye_control=back_geom.armscye_control,
            waist_indent=sides.waist_indent_back,
            hip_outset=sides.hip_side_back,
        )
        front = TopBlockFront(
            part=block_front,
            armscye=front_geom.armscye_front_lower,
            neckline=front_geom.neckline_front,
            shoulder_armscye=front_geom.shoulder_armscye,
            shoulder_neckline=front_geom.shoulder_neckline,
            side_chest_waist=sides.side_chest_waist_front,
            side_waist_hip=sides.side_waist_hip_front,
            side_hip_hem=sides.side_hip_hem_front,
            waist_dart=darts.waist_dart_front,
            shoulder_dart=darts.shoulder_dart_front,
            armscye_control=front_geom.armscye_control,
            waist_indent=sides.waist_indent_front,
            hip_outset=sides.hip_side_front,
            bust_point=front_geom.bust_point,
        )
        return cls(back=back, front=front)

