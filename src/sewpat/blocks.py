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
    intersect,
)
from .grids import TopGrid
from .measurements import (
    BlouseMeasurements,
    GarmentConfig,
    HipDistribution,
    WaistDistribution,
    calculate_hip_distribution,
    calculate_waist_distribution,
)
from .pattern import PatternConfig, PatternElement, PatternPart
from .pattern._notches import RoleMap
from .person import PersonalAdjustments
from .style import STYLE_CENTER_LINE, STYLE_HEM, STYLE_STITCH, STYLE_STITCH_BEVEL
from .units import CM

if TYPE_CHECKING:
    from .fitclass import FitClass

# ---------------------------------------------------------------------------
# Role → grid-line maps for TopBlock notch placement
# ---------------------------------------------------------------------------

#: Notch rules for the **back** pattern piece of a top/blouse block.
#: Each key is a :attr:`~sewpat.element.PatternElement.role` tag; each value
#: is a list of construction-grid element names (from :class:`~sewpat.grids.TopGrid`)
#: whose intersections with that role's outline edges produce notches.
#: Roles absent from this map receive no grid notches.
TOP_BLOCK_BACK_ROLE_MAP: RoleMap = {
    "side": ["Hip"],
    "center_back": ["Chest", "Waist", "Hip"],
}

#: Notch rules for the **front** pattern piece of a top/blouse block.
#: Center-front elements carry ``STYLE_CENTER_LINE`` which has ``no_notch=True``,
#: so even though Chest/Waist/Hip are listed here, no notches will appear — the
#: fold-line style suppresses them automatically.
TOP_BLOCK_FRONT_ROLE_MAP: RoleMap = {
    "side": ["Hip"],
    "center_front": ["Chest", "Waist", "Hip"],
}

# ---------------------------------------------------------------------------
# Construction constants
# These are pattern-drafting constants that encode standard ease/lift values.
# ---------------------------------------------------------------------------

#: Ease added to / subtracted from the shoulder (front / back) seam as
#: parallel offset, always constant.
_SHOULDER_EASE: float = 1.0 * CM

#: Shoulder raise at back neckline ending point, applied as vertical offset
#: to the shoulder seam.
_SHOULDER_RAISE: float = 2.0 * CM
_SHOULDER_DART_WIDTH: float = 1.5 * CM

#: Front neckline offset added to the measured neck-to-bust depth.
_NECKLINE_EASE: float = 1.5 * CM

#: Armscye-front control-point offsets (X, Y).
_ARMSCYE_FRONT_CP_X: float = -5.0 * CM
_ARMSCYE_FRONT_CP_Y: float = -3.0 * CM
_ARMSCYE_FRONT_OFFSET: float = 2.0 * CM

#: Length of the control-point tangent for the side-hip Bézier curves.
_SIDE_HIP_TANGENT: float = 15.0 * CM


#: How far the waist construction line is raised above the actual waist grid line.
_WAIST_OFFSET: float = 1.0 * CM

#: Checkpoint for the back armscye curve, placed on the shoulder height at a
#: fixed distance from the armscye line (german: HP).
_ARMSCYE_BACK_AUX_OFFSET: float = 1.5 * CM
_ARMSCYE_BACK_OFFSET: float = 1 * CM

#: Back armscye Bézier control-point offsets (cp1_x, cp2_x, cp_y).
_ARMSCYE_BACK_CP_X: float = 1 * CM
_ARMSCYE_BACK_CP_Y: float = 1 * CM


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
    armscye_control: Point  # armscye notch (pt_vÄP)

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
    waist_offset: Segment


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
    shoulder_drop: float,
    shoulder_gather: float,
) -> _BackGeometry:
    """Compute all key points and curves for the back piece."""
    hem_center_back = intersect(grid.center_back, grid.hem)[0]
    waist_center_back = intersect(grid.center_back, grid.waist)[0]
    hip_center_back = intersect(grid.center_back, grid.hip)[0]
    waist_center_back_adj = waist_center_back.translate(hip_offset, 0)
    hip_center_back_adj = hip_center_back.translate(hip_offset, 0)
    hem_center_back_adj = hem_center_back.translate(hip_offset, 0)

    armscye_chest = intersect(grid.armscye_back, grid.chest)[0]
    side_chest = intersect(grid.side_back, grid.chest)[0]
    armscye_shoulder = intersect(grid.armscye_back, grid.shoulder_back)[0]
    neck_shoulder = intersect(grid.shoulder_back, grid.neck)[0]
    armscye_shoulder_dropped = armscye_shoulder.translate(0, shoulder_drop)

    # Shoulder seam
    shoulder_neckline = neck_shoulder.translate(0, -_SHOULDER_RAISE)
    dart_notch = (
        Segment(armscye_shoulder_dropped, armscye_chest)
        .point_at_t(0.5)
        .translate(_ARMSCYE_BACK_AUX_OFFSET, 0)
    )
    shoulder_blade = Line(dart_notch, (1, 0), name="Shoulder Blade")
    armscye_control = (
        Segment(armscye_shoulder_dropped, armscye_chest)
        .point_at_t(0.75)
        .translate(_ARMSCYE_BACK_OFFSET, 0)
    )
    shoulder_orig = Segment.from_direction(
        shoulder_neckline,
        armscye_shoulder_dropped,
        length=meas.shoulder_width + shoulder_gather,
    )
    shoulder = shoulder_orig.offset(-_SHOULDER_EASE)

    blade_dart_tip = intersect(grid.dart_back, shoulder_blade)[0]

    # Armscye curve — two cubics joined at armscye_control.
    _cp2_y = armscye_control.distance_to_segment(grid.chest) - _ARMSCYE_BACK_CP_Y
    armscye_lower = CubicBezier(
        side_chest,
        side_chest.translate((armscye_control.x - side_chest.x) / 3, -_ARMSCYE_BACK_CP_Y / 2),
        armscye_control.translate(_ARMSCYE_BACK_CP_X, _cp2_y),
        armscye_control,
        name="Armscye Back Lower",
    )
    # Upper: armscye_control → shoulder.p2, using existing CP offsets.
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
    )


def _build_front_geometry(
    grid: TopGrid,
    meas: BlouseMeasurements,
    back: _BackGeometry,
    armscye_fit: float,
) -> _FrontGeometry:
    """Compute all key points and curves for the front piece."""
    side_front_chest = intersect(grid.side_front, grid.chest)[0]
    armscye_front_chest = intersect(grid.armscye_front, grid.chest)[0]

    # Bust point
    bust_point_shoulder_line = intersect(grid.shoulder_front, grid.bust_point)[0]
    bust_point = bust_point_shoulder_line.translate(0, meas.bust_depth)

    # Neckline anchor points
    center_front_shoulder_line = intersect(grid.center_front, grid.shoulder_front)[0]
    neckline_front_start = center_front_shoulder_line.translate(0, meas.neck_size + _NECKLINE_EASE)
    shoulder_front_neckline_pt = center_front_shoulder_line.translate(-meas.neck_size, 0)

    # Armscye / shoulder construction
    armscye_control = armscye_front_chest.translate(0, -0.25 * meas.armscye_width)
    arm_seam_length = (
        Segment(back.armscye_back_shoulder_dropped, back.armscye_back_chest).length
        - _ARMSCYE_FRONT_OFFSET
    )
    armscye_front_chest_upper = armscye_front_chest.translate(0, -arm_seam_length)
    shoulder_upper_pt = Circle(armscye_front_chest, arm_seam_length).point_along_from(
        armscye_front_chest_upper, -(meas.bust / 20 + armscye_fit)
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
    shoulder_armscye = Segment(shoulder_upper_pt, shoulder_armscye_end).offset(_SHOULDER_EASE)
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
    wd: WaistDistribution,
    hd: HipDistribution,
) -> _SideSeams:
    """Compute side-seam points and curves for both pieces."""
    waist_offset = grid.waist.offset(-_WAIST_OFFSET).set_name("Waist Offset")

    # Raised waist points (side_seam_intake = side-seam waist take-in)
    waist_indent_back = intersect(grid.side_back, waist_offset)[0].translate(
        -wd.side_seam_intake, 0
    )
    waist_indent_front = intersect(grid.side_front, waist_offset)[0].translate(
        wd.side_seam_intake, 0
    )

    side_chest_waist_back = Segment(
        waist_indent_back, back.side_back_chest, name="Side Seam Back Upper"
    )
    side_chest_waist_front = Segment(
        waist_indent_front, front.side_front_chest, name="Side Seam Front Upper"
    )

    # Hip outset (hip_shortfall = hip shortfall correction)
    side_back_offset = grid.side_back.offset(hd.hip_shortfall)
    side_front_offset = grid.side_front.offset(-hd.hip_shortfall)
    hip_side_back = intersect(grid.hip, side_back_offset)[0]
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
    side_hip_hem_back = Segment(
        hip_side_back, hip_side_back.translate(0, hem_depth), name="Side Hem Back"
    )
    side_hip_hem_front = Segment(
        hip_side_front, hip_side_front.translate(0, hem_depth), name="Side Hem Front"
    )

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
    armscye_back_elem: PatternElement,
    wd: WaistDistribution,
    config: GarmentConfig,
) -> tuple[_Darts, Dart]:
    """Build all dart objects for both pieces."""
    # Back waist dart
    waist_dart_back_center = intersect(grid.waist, grid.dart_back)[0]
    waist_dart_back = Dart.from_tip_center_width(
        tip=intersect(grid.dart_back, grid.chest)[0],
        center=waist_dart_back_center,
        width=wd.back_dart_width,
        dart_type=DartType.RHOMBUS,
        second_tip=waist_dart_back_center.translate(0, config.waist_dart_back_tip),
    ).set_name("Waist Dart Back")

    # Front waist dart
    bust_point_waist = intersect(grid.bust_point, grid.waist)[0]
    waist_dart_front = Dart.from_tip_center_width(
        tip=front.bust_point,
        center=bust_point_waist,
        width=wd.front_dart_width,
        dart_type=DartType.RHOMBUS,
        second_tip=bust_point_waist.translate(0, config.waist_dart_front_tip),
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
        leg_b=back.armscye_back_upper.point_along_from(
            back.shoulder_dart_notch, _SHOULDER_DART_WIDTH
        ),
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
    grid: TopGrid,
) -> None:
    """Add all elements to the back PatternPart in drawing order.

    Note: ``back.armscye_back_lower`` and ``back.armscye_back_upper`` are **not**
    appended here — they were already appended in :meth:`TopBlock.from_measurements`
    before :func:`_build_darts` is called, so that :class:`~sewpat.geometry.Dart`
    can reference the live ``PatternElement`` for the in-place edge split.
    Appending them a second time would corrupt the outline polygon.
    """
    part.append(
        Segment(back.anchor, back.waist_center_back_adj, name="Center Back"),
        style=STYLE_STITCH,
        is_outline=True,
        role="center_back",
    )
    part.append(
        Segment(
            back.waist_center_back_adj,
            back.hem_center_back_adj,
            name="Center Back Hem",
        ),
        style=STYLE_STITCH,
        is_outline=True,
        role="center_back",
    )
    part.append(back.neckline_back, style=STYLE_STITCH_BEVEL, is_outline=True, role="neckline")
    part.add_construction_line(back.shoulder_back_orig, name="Shoulder Back Orig")
    part.add_construction_line(back.shoulder_blade)
    part.append(
        back.shoulder_back.set_name("Shoulder Back"),
        style=STYLE_STITCH,
        is_outline=True,
        role="shoulder",
    )
    part.add_dart(shoulder_dart_back)
    part.append(sides.side_chest_waist_back, style=STYLE_STITCH, is_outline=True, role="side")
    part.add_dart(darts.waist_dart_back)
    part.add_construction_line(sides.waist_offset)
    part.append(sides.side_waist_hip_back, is_outline=True, style=STYLE_STITCH, role="side")
    part.append(sides.side_hip_hem_back, style=STYLE_STITCH, is_outline=True, role="side")
    part.append(sides.hem_side_to_center_back, style=STYLE_HEM, is_outline=True)

    # Construction reference points — visible when show_construction=True
    part.add_construction_line(
        Point(back.armscye_control.x, back.armscye_control.y, name="Armscye Control Back"),
    )
    part.add_construction_line(
        Point(
            back.shoulder_dart_notch.x,
            back.shoulder_dart_notch.y,
            name="Shoulder Dart Notch Back",
        ),
    )

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)
    part.add_notches(back.armscye_control, seam_edge=back.armscye_back_lower)
    part.add_grid_notches(grid.part, is_back=True, role_map=TOP_BLOCK_BACK_ROLE_MAP)


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
        style=STYLE_CENTER_LINE,
        is_outline=True,
        role="center_front",
    )
    part.append(
        front.neckline_front.set_name("Neckline Front"),
        style=STYLE_STITCH,
        is_outline=True,
        role="neckline",
    )
    if front.neckline_front_stub is not None:
        part.add_construction_line(front.neckline_front_stub, name="Neckline Front Stub")
    part.add_construction_line(front.shoulder_front_aux_orig, name="Shoulder Front Orig")
    part.add_construction_line(front.shoulder_front_dart_orig, name="Shoulder Front Dart Orig")
    part.append(
        front.shoulder_armscye.set_name("Shoulder Front"),
        style=STYLE_STITCH,
        is_outline=True,
        role="shoulder",
    )
    part.append(
        front.shoulder_neckline.set_name("Shoulder Front Dart"),
        style=STYLE_STITCH,
        is_outline=True,
        role="shoulder",
    )
    part.add_dart(darts.shoulder_dart_front)
    if front.armscye_front_upper is not None:
        part.add_construction_line(front.armscye_front_upper, name="Armscye Front Upper")
    part.append(
        front.armscye_front_lower.set_name("Armscye Front"),
        style=STYLE_STITCH,
        is_outline=True,
        role="armscye",
    )
    part.append(sides.side_chest_waist_front, style=STYLE_STITCH, is_outline=True, role="side")
    part.add_dart(darts.waist_dart_front)
    part.append(sides.side_waist_hip_front, is_outline=True, style=STYLE_STITCH, role="side")
    part.append(sides.side_hip_hem_front, style=STYLE_STITCH, is_outline=True, role="side")
    part.append(sides.hem_side_to_center_front, style=STYLE_HEM, is_outline=True, role="hem")

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)
    part.add_notches(front.armscye_control, seam_edge=front.armscye_front_lower)
    part.add_grid_notches(grid.part, role_map=TOP_BLOCK_FRONT_ROLE_MAP)


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
        armscye_lower: Lower armscye curve (side_chest → armscye_control),
            passes through dart_notch at t=0.5.
        armscye_upper: Upper armscye curve (armscye_control → shoulder).
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
    armscye_lower: CubicBezier
    armscye_upper: CubicBezier
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
        shoulder_armscye: Long shoulder seam running toward the armscye
            (from bust-point pivot side).
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
        grid: TopGrid | None = None,
        layout: PatternConfig | None = None,
        back_name: str = "Block Back",
        front_name: str = "Block Front",
    ) -> TopBlock:
        """Build and return a :class:`TopBlock` from measurements.

        Args:
            meas:        Blouse measurements (ease already included).
            config:      Garment-design choices (length, seam allowance).
            fit_class:   :class:`~sewpat.fitclass.FitClass` for construction offsets.
            adjustments: :class:`~sewpat.person.PersonalAdjustments` — provides
                         ``hip_offset`` and ``shoulder_drop``.
            grid:        Pre-built :class:`~sewpat.grids.TopGrid`.  Pass the grid
                         already constructed for the same layout to avoid building
                         it twice and guarantee both are identical.  If ``None``
                         a new grid is built internally.
            layout:      Pattern layout config (anchor, inter-piece margin).
            back_name:   Name for the back part.
            front_name:  Name for the front part.

        Returns:
            A :class:`TopBlock` with fully constructed ``.back`` and ``.front`` pieces.
        """
        adj = adjustments or PersonalAdjustments()
        layout = layout if layout is not None else PatternConfig()
        seam_allowance = config.seam_allowance

        if fit_class is None:
            from .fitclass import FitClass as _FitClass

            fit_class = _FitClass(pk=4)

        if grid is None:
            grid = TopGrid.from_measurements(
                meas=meas,
                fit_class=fit_class,
                hip_offset=adj.hip_offset,
                config=config,
                layout=layout,
            )

        # ── 1. Build geometry for each piece independently ───────────────────
        back_geom = _build_back_geometry(
            grid,
            meas,
            layout.anchor,
            adj.hip_offset,
            adj.shoulder_drop,
            config.shoulder_gather,
        )
        front_geom = _build_front_geometry(grid, meas, back_geom, config.armscye_fit)

        # ── 2. Compute waist / hip distribution ──────────────────────────────
        wd = calculate_waist_distribution(
            meas,
            pt_waist_cf=intersect(grid.center_front, grid.waist)[0],
            pt_waist_sf=intersect(grid.side_front, grid.waist)[0],
            pt_waist_sb=intersect(grid.side_back, grid.waist)[0],
            pt_waist_cb=back_geom.waist_center_back_adj,
        )
        hd = calculate_hip_distribution(
            meas,
            pt_hip_cf=intersect(grid.center_front, grid.hip)[0],
            pt_hip_sf=intersect(grid.side_front, grid.hip)[0],
            pt_hip_sb=intersect(grid.side_back, grid.hip)[0],
            pt_hip_cb=back_geom.hip_center_back_adj,
        )

        # ── 3. Build shared side-seam geometry ───────────────────────────────
        sides = _build_side_seams(grid, meas, back_geom, front_geom, wd, hd)

        # ── 4. Assemble pieces and extract darts ─────────────────────────────
        block_back = PatternPart(name=back_name)
        block_front = PatternPart(name=front_name)

        # Append the armscye lower first (dart edge ref), then upper
        block_back.append(
            back_geom.armscye_back_lower.set_name("Armscye Back Lower"),
            style=STYLE_STITCH,
            is_outline=True,
            role="armscye",
        )
        armscye_back_elem = block_back.append(
            back_geom.armscye_back_upper.set_name("Armscye Back Upper"),
            style=STYLE_STITCH,
            is_outline=True,
            role="armscye",
        )
        darts, shoulder_dart_back = _build_darts(
            grid, meas, back_geom, front_geom, armscye_back_elem, wd, config
        )

        _assemble_back_part(
            block_back, back_geom, sides, darts, shoulder_dart_back, seam_allowance, grid
        )
        _assemble_front_part(block_front, front_geom, sides, darts, grid, seam_allowance)

        # ── 5. Pack into public dataclasses and return ────────────────────────
        back = TopBlockBack(
            part=block_back,
            armscye_lower=back_geom.armscye_back_lower,
            armscye_upper=back_geom.armscye_back_upper,
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
