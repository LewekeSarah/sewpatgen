#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import (
    PatternElement,
    STYLE_STITCH,
    STYLE_DEBUG_RED,
    CubicBezier,
    STYLE_DART_FOLD,
    GarmentPart, DartType,
)
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
    shoulder_front_short = Segment(pt26, pt_sHlP_front).offset(1 * CM)

    # Sleeves
    sleeve_front = CubicBezier(pt_SuP, pt_BrP.translate(-4 * CM, -3 * CM), pt12, pt12)
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

    if not (pt14.coords == pt7.translate((meas.BrW / 2 + 10 * CM), 0).coords).all():
        raise ValueError("BrW is plotted incorrect.")

    # STEP Center Back, Neckline, and Shoulder
    back_basic = [
        PatternElement(
            Segment(pt1, pt6, name="Center Back"), style=STYLE_STITCH, is_outline=True
        ),
        PatternElement(
            Segment(pt6, pt9, name="Center Back Hem"), style=STYLE_STITCH, is_outline=True
        ),
        PatternElement(
            CubicBezier(pt1, pt1, pt17, shoulder_back.p1, name="Neckline Back"),
            style=STYLE_STITCH, is_outline=True
        ),
        PatternElement(
            shoulder_back_orig.set_name("Shoulder Back Orig"),
            is_outline=False, is_construction=True
        ),
        PatternElement(shoulder_blade, is_construction=True),
        PatternElement(
            shoulder_back.set_name("Shoulder Back"), style=STYLE_STITCH, is_outline=True
        ),
        PatternElement(sleeve_back.set_name("Sleeve Back"), style=STYLE_STITCH, is_outline=True),
        PatternElement(
            Dart.from_tip_and_legs(
                pt29, pt_HP, sleeve_back.point_along_from(pt_HP, 1.5 * CM)
            ).set_name("Shoulder Dart Back")
        ),
        PatternElement(
            side_seam_back_upper, style=STYLE_STITCH, is_outline=True
        ),
        PatternElement(
            waist_dart_back, style=STYLE_DART_FOLD
        ),
        PatternElement(waist_offset, is_construction=True),
        PatternElement(CubicBezier(
            pt_waist_sb_raised,
            pt_waist_sb_raised,
            intersect(grid.hip, grid.side_back)[0],
            intersect(grid.hip, grid.side_back)[0],
            name="Side Hip Curve Back",
        ), is_outline=True, style=STYLE_STITCH),
        PatternElement(
            Segment(
                intersect(grid.hip, grid.side_back)[0],
                intersect(grid.hip, grid.side_back)[0].translate(0, Segment(pt8, pt9).length),
            ),
            style=STYLE_STITCH, is_outline=True
        )
    ]
    block_back.extend(back_basic)
    block_back.add_notches(pt_hÄP, seam_edge=sleeve_back)

    # STEP Center Front, Neckline, and Shoulder
    front_basic = [
        PatternElement(
            Segment(pt22, intersect(grid.center_front, grid.hem)[0], name="Center Front"),
            style=STYLE_STITCH, is_outline=True,
        ),
        PatternElement(
            CubicBezier(pt22, pt22, pt21.translate(-meas.HlB, meas.HlB), pt_sHlP_front, name="Neckline Front"),
            style=STYLE_STITCH, is_outline=True,
        ),
        PatternElement(
            Segment(pt_SuP, pt25, name="Shoulder Front Orig"),
            is_outline=False, is_construction=True
        ),
        PatternElement(
            Segment(pt_sHlP_front, pt26, name="Shoulder Front Dart Orig"),
            is_outline=False, is_construction=True
        ),
        PatternElement(shoulder_front_long.set_name("Shoulder Front"), style=STYLE_STITCH, is_outline=True),
        PatternElement(shoulder_front_short.set_name("Shoulder Front Dart"), style=STYLE_STITCH, is_outline=True),
        PatternElement(
            Dart.from_tip_and_legs(
                pt_BrP, shoulder_front_short.p1, shoulder_front_long.p2
            ).set_name("Shoulder Dart Front"),
            style=STYLE_STITCH, is_outline=True,
        ),
        PatternElement(sleeve_front.set_name("Sleeve Front"), style=STYLE_STITCH),
        PatternElement(
            side_seam_front_upper, style=STYLE_STITCH, is_outline=True
        ),
        PatternElement(
            waist_dart_front, style=STYLE_DART_FOLD
        ),
        PatternElement(CubicBezier(
            pt_waist_sf_raised,
            pt_waist_sf_raised,
            intersect(grid.hip, grid.side_front)[0],
            intersect(grid.hip, grid.side_front)[0],
            name="Side Hip Curve Front",
        ), is_outline=True, style=STYLE_STITCH),
        PatternElement(
            Segment(
                intersect(grid.hip, grid.side_front)[0],
                intersect(grid.hip, grid.side_front)[0].translate(0, Segment(pt8, pt9).length),
            ),
            style=STYLE_STITCH, is_outline=True
        )
    ]
    block_front.add_notches(pt_vÄP, seam_edge=sleeve_front)
    block_front.extend(front_basic)
    return pattern


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    balance = make_balance()
    measurements = make_blouse_measurements(person, allowance, balance)
    model_config = make_model_config()
    pattern = make_blouse(measurements, model_config)

    pattern_parts = [Part.BLOCK_BACK, Part.BLOCK_FRONT]
    grid_parts = [Part.GRID]

    # With construction grid visible (for building / drafting)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "top_waisted_dart_grid.svg"),
        parts=grid_parts + pattern_parts,
        show_bezier_control_points=True,
        show_construction=True,
    )

# #marker_single  top_waisted_dart.pdf ./
