from click import style

from sewpat import Segment, PatternPart
from sewpat.geometry import (
    CM,
    Point,
    segment_to_intersection,
    intersect,
    Ray,
    Circle,
    CubicBezier,
)
from sewpat.measurments import (
    ModelConfig,
    BlouseMeasurements,
    Allowance,
    make_measurements_trouser,
    TrouserMeasurements,
)
from sewpat.person import Gender, Person
from sewpat.render import render_pattern_part, StyleOptions


def make_person() -> Person:
    return Person(
        KöH=122 * CM,
        BrU=63 * CM,
        TaU=60 * CM,
        HüU=67 * CM,
        HüT=0 * CM,
        BrT=15.6 * CM,
        RüL=29.2 * CM,
        SiH=20.4 * CM,  # SiH = body_rise / Sitzhöhe
        SrH=55 * CM,  # SrH = inside leg / Schritthöhe
        gender=Gender.boy,
    )


def make_allowance() -> Allowance:
    return Allowance(
        SiH=3 * CM,  # baby 4.5 * CM,
        SrH=- 3 * CM,  # baby-2 * CM,
        HüU=4 * 5.5 * CM,  # baby20 * CM,
    )


def make_model_config() -> ModelConfig:
    return ModelConfig(
        MoL=55 * CM,
        ZuvHoB=0.5 * CM,  # baby 1 * CM
        SaW = 14 * CM
    )


def baby_trousers(meas: TrouserMeasurements, config: ModelConfig) -> PatternPart:
    ## Front Section
    # Anchor: top right

    # STEP 1:
    # Grundgerüst
    pt0 = Point(25 * CM, -40 * CM, "p1")
    pt1, pt2, pt3, pt4, pt5, _ = base_grid_trouser(meas, pt0)
    s_knee = Segment(pt3, pt3.translate(-meas.vHoB, 0), name="Knielinie")
    s45 = Segment(pt4, pt5, name="4-5")
    base_grid = [
        Segment(pt0, pt2, name="Seitlich Taillenhöhe"),
        Segment(pt2, pt2.translate(-meas.vHoB, 0), "Saumlinie"),
        s_knee,
        Segment(pt1, pt4, name="Schrittlinie"),
        Segment(pt5, pt0, name="Taillenlinie"),
        s45,
    ]
    # STEP 2:
    # Hosenbeingitter
    pt6 = pt4.translate(0, -1 / 12 * meas.HüW)
    pt7 = pt4.translate(-(meas.vHoB * 0.25 + config.ZuvHoB), 0)
    s47 = Segment(pt4, pt7, name="Hosenausschnitt")
    pt8 = pt1.translate(-(0.5 * meas.vHoB - 0.5 * CM), 0)
    pt9 = pt3.translate(-(0.5 * meas.vHoB - 0.5 * CM), 0)
    pt10 = pt2.translate(-(0.5 * meas.vHoB - 0.5 * CM), 0)
    base_leg = [s47, Segment(pt8, pt10, name="Vorderhosenbruch / Fadenlauf")]

    #
    # # STEP 3:
    # # Hosenausschnitt
    pt4_aux = intersect(
        Ray(pt4, -s45.unit_normal + s47.unit_normal), Circle(pt4, 1.75 * CM)
    )
    s44_aux = Segment(pt4, pt4_aux[0], style=StyleOptions(dash_array=[3, 2]))
    pt4_bz1 = s44_aux.point_perpendicular(1.5 * CM, rel_pos_on_obj=1)
    pt4_bz2 = s44_aux.point_perpendicular(-1.5 * CM, rel_pos_on_obj=1)
    elems = (
        base_grid
        + base_leg
        + [
            s44_aux,
            CubicBezier(pt6, pt4.translate(0, -3 * CM), pt4_bz1, pt4_aux[0]),
            CubicBezier(pt4_aux[0], pt4_bz2, pt7.translate(0.75 * CM, 0), pt7),
        ]
    )

    # # STEP 4
    # # Seitennaht
    pt11 = pt10.translate(meas.vHoB / 3 + 1 * CM, 0)
    pt11_tmp = pt11.translate(0, -20 * CM)
    s111 = CubicBezier(
        pt11, pt11_tmp, pt3.translate(0, 15 * CM), pt1, name="Seitennaht"
    )
    pt12 = intersect(s111, s_knee)[0]
    elems += [
        Segment(
            pt11, pt11.translate(0, -4 * CM), style=StyleOptions(dash_array=[3, 2])
        ),
        s111,
    ]

    # # STEP 5
    # # Innenbeinnaht
    pt14 = pt9.translate(-(pt12.x - pt9.x), 0)
    pt13 = pt10.translate(-(meas.vHoB / 3 + 1 * CM), 0)
    elems += [
        Segment(pt10, pt13),
        Segment(pt14, pt7, style=StyleOptions(dash_array=[3, 2])),
        CubicBezier(
            pt13, pt13.translate(0, -10 * CM), pt14.translate(1 * CM, 10 * CM), pt14
        ),
        CubicBezier(
            pt14,
            pt14.translate(-1 * CM, -10 * CM),
            pt7.translate(2 * CM, (pt14.y - pt7.y) / 3),
            pt7,
            name="Innenbeinnaht",
        ),
    ]

    # STEP 6
    # Back
    back_pt0 = pt5.translate(-10 * CM, 0)
    back_pt1, back_pt2, back_pt3, back_pt4, back_pt5, _ = base_grid_trouser(meas, back_pt0)
    s_knee_back = Segment(back_pt3, back_pt3.translate(-meas.vHoB, 0), name="Knielinie")
    back_s45 = Segment(back_pt4, back_pt5, name="4-5")
    back_base_grid = [
        Segment(back_pt0, back_pt2, name="Seitlich Taillenhöhe"),
        Segment(back_pt2, back_pt2.translate(-meas.vHoB, 0), "Saumlinie"),
        s_knee_back,
        Segment(back_pt1, back_pt4, name="Schrittlinie"),
        Segment(back_pt5, back_pt0, name="Taillenlinie"),
        back_s45,
    ]

    # STEP 7
    # Waistband
    pt15 = back_pt5.translate(2 * CM, 0)
    pt16 = pt15.translate(0, -2 * CM)
    pt17 = back_pt0.translate(1.5 * CM, 0)
    pt18 = back_pt4.translate(0, -meas.SiH / 2)
    waist_elems = [
        Segment(pt15, pt16, style=StyleOptions(dash_array=[3, 2])),
        Segment(pt16, pt17),
    ]

    # STEP 8
    # Hintere Hosenausschnitt
    pt19 = back_pt4.translate(-(abs(pt7.x - pt4.x) - 0.5), 0)
    pt20 = pt19.translate(0, 0.5 * CM)
    back_elems = (
        back_base_grid +
        waist_elems
        + [
            Segment(back_pt4, pt19, style=StyleOptions(dash_array=[3, 2])),
            CubicBezier(pt16, pt18, back_pt4, pt20),
        ]
    )

    # STEP 9
    # Seitennaht
    pt21 = back_pt1.translate( 0.7 * CM, 0)
    pt22 = back_pt3.translate(- abs(pt3.x-pt12.x) / 2, 0)
    back_pt10 = back_pt2.translate(-(0.5 * meas.vHoB - 0.5 * CM), 0)
    back_pt11 = back_pt10.translate(meas.vHoB / 3 + 1 * CM, 0)
    back_elems = back_elems + [
        CubicBezier(pt17, pt17, pt21, pt21),
        CubicBezier(pt21, pt21, pt22, pt22),
        # TODO Übergang anpassen
        CubicBezier(pt22, pt22, back_pt11.translate(0, - 15 *CM ), back_pt11),
    ]

    # STEP 10
    # Innennaht
    back_pt9 = back_pt3.translate(-(0.5 * meas.vHoB - 0.5 * CM), 0)
    pt23 = back_pt9.translate((back_pt9.x - pt22.x), 0)
    back_pt13 = back_pt10.translate(-(meas.vHoB / 3 + 1 * CM), 0)
    back_elems = back_elems + [
        Segment(pt20, pt23, style=StyleOptions(dash_array=[0, 20])),
        CubicBezier(pt20, back_pt4.translate(0, (pt23.y - pt20.y) / 2), pt23, pt23),
        CubicBezier(pt23, pt23, back_pt13.translate(0, - 15 *CM ), back_pt13),
        Segment(back_pt13, back_pt11)
    ]
    elems += back_elems
    return PatternPart(name="Baby Trousers with Nappies", elements=elems)


def boy_trousers(meas, model) -> PatternPart:
    ## Front Section
    # Anchor: top right

    # STEP 1:
    # Grundgerüst
    pt0 = Point(25 * CM, -40 * CM, "p1")
    pt1, pt2, pt3, pt4, pt5, pt6 = base_grid_trouser(meas, pt0)
    elems = [
        Segment(pt0, pt1),
        Segment(pt1, pt2, style=StyleOptions(dash_array=[3, 2])),
        Ray(pt1, (-pt4.x, 0), "Schrittlinie"),
        Segment(pt4, pt5, style=StyleOptions(dash_array=[3, 2])),
        Ray(pt0, (-pt5.x, 0))
    ]

    # STEP 2:
    # # Hosenausschnitt
    pt7 = pt4.translate(0, -0.25 * meas.SiH)
    pt8 = pt4.translate(- (0.25 * meas.vHoB - model.ZuvHoB), 0)
    bz_control2 = Segment(pt7, pt8).point_perpendicular(-0.5 * CM, rel_pos_on_obj=0.75)
    bz_control3 = pt7.translate(-0.2 * CM, 2.5 * CM)
    elems += [
        # Circle(pt4, 2.5 * CM),
        # pt7,
        # bz_control3,
        # bz_control2,
        CubicBezier(pt6, pt6, pt7, pt7),
        CubicBezier(pt7, bz_control3, bz_control2, pt8),
        Segment(pt6, pt0, name="Bund")
    ]

    # # STEP 3:
    # Hosenbeingitter
    pt9, pt10, pt11, pt12, pt13 = get_leg_grid(meas, model, pt0)
    grain_line = Segment(pt9, pt11, style=StyleOptions(dash_array=[3, 2]))
    knee = Ray(pt3, (-pt10.x, 0), name="Knielinie")
    elems += [
        grain_line,
        Ray(pt2, (-pt10.x, 0), name="Saumlinie"),
        knee,
        Segment(pt12,pt13)
    ]

    # STEP 4:
    # Seitennaht & Innennaht
    side = CubicBezier(pt1,pt1, pt12, pt12)
    pt14 = intersect(side, knee)[0]
    pt15 = pt10.translate(pt10.x - pt14.x, 0)
    inner_seam = Segment(pt8, pt15)
    bz_control = inner_seam.point_perpendicular(-1.6 * CM, rel_pos_on_obj=0.5)
    elems += [
        side,
        Segment(pt13, pt15),
        inner_seam.point_perpendicular(-.8 * CM , rel_pos_on_obj=0.5),
        Segment(pt8, pt15, style=StyleOptions(dash_array=[3, 2])),
        CubicBezier(pt8, bz_control, pt15.translate(-0.1 * CM, - 2 * CM), pt15) # Curve 0.8cm inwards
    ]

    # STEP 5:
    # Rückteil Grundgerüst
    back_pt0 = pt5.translate(- 10 * CM, 0)
    back_pt1, back_pt2, back_pt3, back_pt4, back_pt5, back_pt6 = base_grid_trouser(meas, back_pt0)
    back_pt9, back_pt10, back_pt11, back_pt12, back_pt13 = get_leg_grid(meas, model, back_pt0)
    # STEP 6:
    # Hosenbund
    pt16 = back_pt6.translate(3.5 * CM, 0)
    pt17 = pt16.translate(0, - 3 * CM)
    pt18 = back_pt0.translate(2 * CM, 0)
    back_elems = [
        Segment(back_pt9, back_pt11, style=StyleOptions(dash_array=[3, 2])),
        Segment(pt17, pt18)
    ]

    # STEP 7:
    # Hinternaht
    pt19 = back_pt4.translate(0, - 0.5 * meas.SiH)
    pt20 = back_pt4.translate(- (2 * (pt4.x - pt8.x) - 0.5 * CM), 0)
    pt21 = pt20.translate(0, 1 * CM)
    bz_contol4 = back_pt4.translate(-3.05 *CM, -3.05 * CM)
    back_elems += [
        # 17-19-21 touching a curve 4.5 cm away from 4,
        Segment(pt17, pt19),
        # bz_contol4,
        # Circle(back_pt4, 4.5 * CM),
        CubicBezier(pt19, bz_contol4, bz_contol4, pt21),
    ]

    # STEP 8:
    # Seitennähte / Innenbeinnähte
    pt22 = back_pt12.translate(1 * CM, 0)
    side_back = Segment(pt18, pt22)
    pt23 = intersect(side_back, knee)[0]
    pt24 = back_pt13.translate(- 1 * CM, 0)
    back_shift = pt0.x - back_pt0.x
    back_pt14 = pt14.translate(-back_shift, 0)
    pt25 = pt15.translate(- back_shift + (back_pt14.x - pt23.x), 0)
    outer_back_seam = Segment(pt21, pt25, style=StyleOptions(dash_array=[3, 2]))
    bz_control5 = outer_back_seam.point_perpendicular(-2.5 * CM, rel_pos_on_obj=0.5)
    back_elems += [
        Segment(pt18, pt22),
        Segment(pt24, pt25),
        Segment(pt22, pt24),
        outer_back_seam.point_perpendicular(-1.2 * CM, rel_pos_on_obj=0.5),
        outer_back_seam,
        CubicBezier(pt21, bz_control5, pt25.translate(-0.1 * CM, -2 * CM), pt25)
    ]
    elems += back_elems
    return PatternPart(name="Flat Boy Trousers", elements=elems)


def base_grid_trouser(meas, pt0: Point) -> tuple[Point, Point, Point, Point, Point, Point]:
    pt1 = pt0.translate(0, meas.SiH)
    pt2 = pt1.translate(0, meas.SrH)
    pt3 = pt1.translate(0, meas.KnH)
    pt4 = pt1.translate(-meas.vHoB, 0)
    pt5 = pt0.translate(-meas.vHoB, 0)
    pt6 = pt5.translate(1 * CM, 0)
    return pt1, pt2, pt3, pt4, pt5, pt6


def get_leg_grid(meas, model, pt0: Point) -> tuple[Point, Point, Point, Point, Point]:
    base_grid = base_grid_trouser(meas, pt0)
    pt9 = base_grid[0].translate(- 0.5 * meas.vHoB, 0)
    pt10 = base_grid[2].translate(- 0.5 * meas.vHoB, 0)
    pt11 = base_grid[1].translate(- 0.5 * meas.vHoB, 0)
    pt12 = pt11.translate(model.SaW / 2 + 0.5 * CM, 0)
    pt13 = pt11.translate(-(model.SaW / 2 + 0.5 * CM), 0)
    return  pt9, pt10, pt11, pt12, pt13


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    measurements = make_measurements_trouser(person, allowance)
    model_config = make_model_config()
    part = boy_trousers(measurements, model_config)

    d = render_pattern_part(part, 60 * CM, 90 * CM)
    d.save_svg("boy_shorts.svg")
