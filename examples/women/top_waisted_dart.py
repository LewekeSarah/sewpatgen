#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import (
    STYLE_STITCH,
    CubicBezier,
    GarmentPart,
    DartType,
    STYLE_HEM,
)
from sewpat.style import StyleOptions
from sewpat.geometry import (
    Circle,
    Dart,
    Line,
    Point,
    Ray,
    Segment,
    intersect,
)
from sewpat.grids import TopGrid
from sewpat.measurements import (
    Allowance,
    BlouseMeasurements,
    ModelConfig,
    WaistDistribution,
    calculate_waist_distribution,
    calculate_hip_distribution,
    make_blouse_measurements,
)
from sewpat.pages import DinA0
from sewpat.pattern import ConstructionGrid, Pattern, PatternPart, PatternConfig
from sewpat.person import BalanceAdjustments, Person
from sewpat.render import export_pattern_svg_mm
from sewpat.units import CM


def make_person() -> Person:
    return Person(
        KöH=159 * CM,
        BrU=83.5 * CM,
        TaU=69.5 * CM,
        HüU=93 * CM,
        HüT=24 * CM,
        BrT=27.5 * CM,
        HlB=6.5 * CM,
        BrPA=8.3 * CM,
        SuB=12.1 * CM,
        RüL=39 * CM,
        VL=43.4 * CM,
    )


def make_allowance() -> Allowance:
    return Allowance(
        RüB=1.0 * CM,
        ArD=2.0 * CM,
        BrB=1.5 * CM,
        AlT=1.5 * CM,
        TaU=8.0 * CM,
        HüU=6.0 * CM,
    )


def make_model_config() -> ModelConfig:
    # TODO the ZuBrA depends on the Passformklasse PK <4: 0-0.5cm, 5 <= PK < 8: 1cm, PK >=0: 1.5cm
    return ModelConfig(MoL=75 * CM, BeckenAdjustment=1 * CM, ZuBrA=0.5 * CM)


def make_balance() -> BalanceAdjustments:
    return BalanceAdjustments(VL=-0.9 * CM)


class Part(GarmentPart):
    """Pattern parts for the waisted top with darts."""
    GRID        = "Grid"
    BLOCK_BACK  = "Block Back"
    BLOCK_FRONT = "Block Front"


# -----------------------------------------------------------------------
def make_blouse(meas: BlouseMeasurements, model: ModelConfig) -> Pattern:

    config = PatternConfig()
    pattern = Pattern(name="Waisted Top with Darts Block", anchor=config.anchor)

    # -----------------------------------------------------------------------
    # Grid — construction detail lines built on top of the grid
    # -----------------------------------------------------------------------
    grid = TopGrid.from_measurements(meas=meas, model=model, config=config)
    pattern.add_part(grid.part)

    # -----------------------------------------------------------------------
    # Block — construction detail lines built on top of the grid
    # -----------------------------------------------------------------------
    block_back = PatternPart(name=Part.BLOCK_BACK)
    pattern.add_part(block_back)
    block_front = PatternPart(name=Part.BLOCK_FRONT)
    pattern.add_part(block_front)

    # STEP Grid Intersections
    pt1 = config.anchor
    pt2 = pt1.translate(0, model.MoL)
    pt4 = pt1.translate(0, meas.RüL)
    pt5 = intersect(grid.center_back, grid.hip)[0]
    pt6 = pt4.translate(model.BeckenAdjustment, 0)
    pt8 = pt5.translate(model.BeckenAdjustment, 0)
    pt9 = pt2.translate(model.BeckenAdjustment, 0)
    pt7 = intersect(Segment(pt1, pt6), grid.chest)[0]
    pt10 = intersect(grid.sleeve_back, grid.chest)[0]
    pt11 = intersect(grid.side_back, grid.chest)[0]
    pt12 = intersect(grid.side_front, grid.chest)[0]
    pt13 = intersect(grid.sleeve_front, grid.chest)[0]
    pt14 = intersect(grid.center_front, grid.chest)[0]
    pt15 = intersect(grid.bust_point, grid.chest)[0]
    pt16 = intersect(grid.sleeve_back, grid.shoulder_back)[0]
    pt17 = intersect(grid.shoulder_back, grid.neck)[0]
    pt18 = pt16.translate(0, 1.5 * CM)  # TODO don't hard-code

    # Shoulder back
    pt_sHlP = pt17.translate(0, -2 * CM)  # TODO don't hard-code
    pt_HP = (
        Segment(pt18, pt10).point_at_t(0.5).translate(1 * CM, 0)
    )  # TODO don't hard-code
    shoulder_blade = Line(pt_HP, (1, 0), name="Shoulder Blade")
    pt_hÄP = (
        Segment(pt18, pt10).point_at_t(0.75).translate(1.5 * CM, 0)
    )  # TODO don't hard-code
    shoulder_back_orig = Segment.from_direction(pt_sHlP, pt18, length=meas.SuB + 1 * CM)
    shoulder_back = shoulder_back_orig.offset(- 1 * CM)

    # Neckline front
    pt19 = intersect(grid.bust_point, grid.waist)[0]
    pt20 = intersect(grid.shoulder_front, grid.bust_point)[0]
    pt_BrP = pt20.translate(0, meas.BrT)  # TODO check BrT vs BrT2
    pt21 = intersect(grid.center_front, grid.shoulder_front)[0]
    pt22 = pt21.translate(0, meas.HlB + 1.5 * CM)  # TODO don't hard-code
    pt_sHlP_front = pt21.translate(-meas.HlB, 0)

    # Shoulder front with Dart
    pt_vÄP = pt13.translate(0, -0.25 * meas.ArD)
    aux_l = Segment(pt18, pt10).length - 2 * CM
    pt23 = pt13.translate(0, -aux_l)  # TODO don't hard-code
    pt_SuP = Circle(pt13, aux_l).point_along_from(
        pt23, -meas.BrU / 20 + 0 * CM
    )  # TODO don't hard-code
    pt24 = intersect(Circle(pt_BrP, meas.BrT), Circle(pt_SuP, meas.SuB))[0]
    shoulder_front_aux = Segment(pt24, pt_SuP)
    pt25 = shoulder_front_aux.point_along_from(pt24, Segment(pt_sHlP_front, pt20).length)
    pt26 = pt_BrP.translate(0, -Segment(pt_BrP, pt25).length)
    shoulder_front_long = Segment(pt_SuP, pt25).offset(1 * CM)
    # Proper parallel offset — stays exactly 1 cm from Segment(pt26, pt_sHlP_front).
    _shoulder_front_short_raw = Segment(pt26, pt_sHlP_front).offset(1 * CM)

    # Neckline front Bézier — split at the intersection with the Ray extending
    # shoulder_front_short, then snap shoulder_front_short.p2 to that exact
    # intersection point so the two elements share a common endpoint with zero
    # gap — same pattern as the sleeve/shoulder and back neckline/shoulder splits.
    neckline_front_full = CubicBezier(pt22, pt22, pt21.translate(-meas.HlB, meas.HlB), pt_sHlP_front)
    _short_ray = Ray(_shoulder_front_short_raw.p1, _shoulder_front_short_raw.unit_direction)
    _neckline_intersections = intersect(neckline_front_full, _short_ray)
    if _neckline_intersections:
        _ix = _neckline_intersections[0]
        # Rebuild short shoulder so p2 lands exactly on the neckline intersection
        shoulder_front_short = Segment(_shoulder_front_short_raw.p1, _ix)
        _neckline_split = neckline_front_full.split_at_points([_ix])
        # Snap the neckline end to exactly _ix to eliminate any floating-point epsilon
        _nf = _neckline_split[0]
        neckline_front = CubicBezier(_nf.p0, _nf.p1, _nf.p2, _ix)  # pt22 → _ix (outline)
        neckline_front_stub = _neckline_split[1] if len(_neckline_split) > 1 else None
    else:
        shoulder_front_short = _shoulder_front_short_raw
        neckline_front = neckline_front_full
        neckline_front_stub = None

    # Sleeves
    sleeve_front = CubicBezier(pt_SuP, pt_BrP.translate(-4 * CM, -3 * CM), pt12, pt12)
    # Split sleeve_front at exactly shoulder_front_long.p1 (projected onto the
    # curve) so the lower part starts flush at the shoulder endpoint — no gap.
    _sleeve_split_parts = sleeve_front.split_at_points([shoulder_front_long.p1])
    if len(_sleeve_split_parts) > 1:
        sleeve_front_upper = _sleeve_split_parts[0]   # pt_SuP → shoulder_front_long.p1 (construction)
        sleeve_front_lower = _sleeve_split_parts[1]   # shoulder_front_long.p1 → pt12   (outline)
    else:
        sleeve_front_upper = None
        sleeve_front_lower = sleeve_front
    sleeve_back = CubicBezier(
        pt11,
        pt_hÄP.translate(-0.5 * CM, 3 * CM),
        pt_hÄP.translate(-1.5 * CM, 3 * CM),
        shoulder_back.p2,
    )

    # Darts on the Back
    pt27 = intersect(grid.waist, grid.sleeve_back)[0]
    pt28 = intersect(grid.waist, grid.dart_back)[0]
    pt29 = intersect(grid.dart_back, shoulder_blade)[0]


    # STEP Waist dart distribution (Ausfallbetrag)
    waist_offset = grid.waist.offset(-1 * CM).set_name("Waist Offset")  # TODO don't hard-code
    pt_waist_cf = intersect(grid.center_front, grid.waist)[0]
    pt_waist_sf = intersect(grid.side_front,   grid.waist)[0]
    pt_waist_sb = intersect(grid.side_back,    grid.waist)[0]
    wd: WaistDistribution = calculate_waist_distribution(
        meas,
        pt_waist_cf=pt_waist_cf,
        pt_waist_sf=pt_waist_sf,
        pt_waist_sb=pt_waist_sb,
        pt_waist_cb=pt6,
    )

    # STEP Hip distribution (Fehlbetrag Hüftweite)
    pt_hip_cf = intersect(grid.center_front, grid.hip)[0]
    pt_hip_sf = intersect(grid.side_front,   grid.hip)[0]
    pt_hip_sb = intersect(grid.side_back,    grid.hip)[0]
    pt_hip_cb = pt8  # center-back hip point (with BeckenAdjustment)
    hd = calculate_hip_distribution(
        meas,
        pt_hip_cf=pt_hip_cf,
        pt_hip_sf=pt_hip_sf,
        pt_hip_sb=pt_hip_sb,
        pt_hip_cb=pt_hip_cb,
    )

    # Raise side-seam waist points by SaEinzug (toward bust line, y decreases)
    pt_waist_sb_raised = intersect(grid.side_back, waist_offset)[0].translate(-wd.SaEinzug, 0)
    pt_waist_sf_raised = intersect(grid.side_front, waist_offset)[0].translate(wd.SaEinzug, 0)

    # Upper side seam drawn straight from raised waist point to bust line
    side_seam_back_upper  = Segment(pt_waist_sb_raised, pt11, name="Side Seam Back Upper")
    side_seam_front_upper = Segment(pt_waist_sf_raised, pt12, name="Side Seam Front Upper")

    # Back waist dart  — mouth on waist line at dart_back position, tip upward
    _DART_LENGTH_BACK  = 10 * CM
    _DART_LENGTH_FRONT =  8 * CM
    pt_back_dart_tip = pt28.translate(0, -_DART_LENGTH_BACK)
    waist_dart_back = Dart.from_tip_center_width(
        tip=intersect(grid.dart_back, grid.chest)[0],
        center=pt28,
        width=wd.hAbI,
        dart_type=DartType.RHOMBUS,
        second_tip=pt28.translate(0, 16 * CM) # TODO don't hard-code
    ).set_name("Waist Dart Back")

    # Front waist dart — mouth on waist line at bust_point position, tip upward
    waist_dart_front = Dart.from_tip_center_width(
        tip=pt_BrP,
        center=pt19,
        width=wd.vAbI,
        dart_type=DartType.RHOMBUS,
        second_tip=pt19.translate(0, 12 * CM) # TODO don't hard-code
    ).set_name("Waist Dart Front")

    side_back_offset = grid.side_back.offset(hd.Fehlbetrag)
    side_front_offset = grid.side_front.offset(-hd.Fehlbetrag)
    pt37 = intersect(grid.hip, side_back_offset)[0]
    pt37_front = intersect(grid.hip, side_front_offset)[0]

    side_back_curved = CubicBezier(
                pt_waist_sb_raised,
                intersect(grid.side_back, waist_offset)[0].translate(- hd.Fehlbetrag, 15 * CM),
                pt37,
                pt37,
                name="Side Hip Curve Back",
            )

    side_front_curved = CubicBezier(
            pt_waist_sf_raised,
            intersect(grid.side_front, waist_offset)[0].translate(hd.Fehlbetrag, 15 * CM),
            pt37_front,
            pt37_front,
            name="Side Hip Curve Front",
        )

    if not (pt14.coords == pt7.translate((meas.BrW / 2 + 10 * CM), 0).coords).all():
        raise ValueError("BrW is plotted incorrect.")

    # STEP Center Back, Neckline, and Shoulder
    sleeve_back_elem = block_back.append(
        sleeve_back.set_name("Sleeve Back"), style=STYLE_STITCH, is_outline=True
    )
    shoulder_dart_back = Dart.from_edge_at_legs(
        sleeve_back_elem,
        leg_a=pt_HP,
        leg_b=sleeve_back.point_along_from(pt_HP, 1.5 * CM),
        tip=pt29,
        name="Shoulder Dart Back",
    )

    block_back.append(Segment(pt1, pt6, name="Center Back"), style=STYLE_STITCH, is_outline=True)
    block_back.append(Segment(pt6, pt9, name="Center Back Hem"), style=STYLE_STITCH, is_outline=True)
    block_back.append(CubicBezier(pt1, pt1, pt17, shoulder_back.p1, name="Neckline Back"), style=StyleOptions(dash_array=[5.0, 2.0], corner_join="bevel"), is_outline=True)
    block_back.append(shoulder_back_orig.set_name("Shoulder Back Orig"), is_construction=True)
    block_back.append(shoulder_blade, is_construction=True)
    block_back.append(shoulder_back.set_name("Shoulder Back"), style=STYLE_STITCH, is_outline=True)
    block_back.add_dart(shoulder_dart_back)
    block_back.append(side_seam_back_upper, style=STYLE_STITCH, is_outline=True)
    block_back.add_dart(waist_dart_back)
    block_back.append(waist_offset, is_construction=True)
    block_back.append(side_back_curved, is_outline=True, style=STYLE_STITCH)
    block_back.append(Segment(pt37, pt37.translate(0, Segment(pt8, pt9).length)), style=STYLE_STITCH, is_outline=True)
    block_back.append(Segment(intersect(grid.hem, side_back_offset)[0], pt9), style=STYLE_HEM, is_outline=True)
    block_back.add_seam_allowance(model.seam_allowance)
    block_back.add_notches(pt_hÄP, seam_edge=sleeve_back)

    # STEP Center Front, Neckline, and Shoulder
    block_front.append(Segment(pt22, intersect(grid.center_front, grid.hem)[0], name="Center Front"), style=StyleOptions(dash_array=[5.0, 2.0], corner_join="bevel"), is_outline=True)
    block_front.append(neckline_front.set_name("Neckline Front"), style=STYLE_STITCH, is_outline=True)
    if neckline_front_stub is not None:
        block_front.append(neckline_front_stub.set_name("Neckline Front Stub"), is_construction=True)
    block_front.append(Segment(pt_SuP, pt25, name="Shoulder Front Orig"), is_construction=True)
    block_front.append(Segment(pt_sHlP_front, pt26, name="Shoulder Front Dart Orig"), is_construction=True)
    block_front.append(shoulder_front_long.set_name("Shoulder Front"), style=STYLE_STITCH, is_outline=True)
    block_front.append(shoulder_front_short.set_name("Shoulder Front Dart"), style=STYLE_STITCH, is_outline=True)
    block_front.add_dart(
        Dart.from_tip_and_legs(pt_BrP, shoulder_front_short.p1, shoulder_front_long.p2).set_name("Shoulder Dart Front")
    )
    block_front.append(side_seam_front_upper, style=STYLE_STITCH, is_outline=True)
    if sleeve_front_upper is not None:
        block_front.append(sleeve_front_upper.set_name("Sleeve Front Upper"), is_construction=True)
    block_front.append(sleeve_front_lower.set_name("Sleeve Front"), style=STYLE_STITCH, is_outline=True)
    block_front.add_notches(pt_vÄP, seam_edge=sleeve_front_lower)

    block_front.add_dart(waist_dart_front)
    block_front.append(side_front_curved, is_outline=True, style=STYLE_STITCH)
    block_front.append(Segment(pt37_front, pt37_front.translate(0, Segment(pt8, pt9).length)), style=STYLE_STITCH, is_outline=True)
    block_front.append(Segment(intersect(grid.hem, side_front_offset)[0], intersect(grid.hem, grid.center_front)[0]), style=STYLE_HEM, is_outline=True)
    block_front.add_seam_allowance(model.seam_allowance)
    return pattern


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    balance = make_balance()
    measurements = make_blouse_measurements(person, allowance, balance)
    model_config = make_model_config()
    pattern = make_blouse(measurements, model_config)

    pattern_parts = [Part.BLOCK_BACK, Part.BLOCK_FRONT]
    grid_parts = [] # [Part.GRID]

    # With construction grid visible (for building / drafting)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "top_waisted_dart_grid.svg"),
        parts=grid_parts + pattern_parts,
        show_bezier_control_points=False,
        show_construction=True,
        show_seam_allowance=True
    )

# #marker_single  top_waisted_dart.pdf ./
