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
        HüU=68 * CM,
        HüT=0 * CM,
        BrT=15.6 * CM,
        RüL=29.2 * CM,
        SiH=20.4 * CM,  # SiH = body_rise / Sitzhöhe
        SrH=55 * CM,  # SrH = inside leg / Schritthöhe
        gender=Gender.boy,
    )


def make_allowance() -> Allowance:
    return Allowance(
        SiH=4.5 * CM,
        SrH=-2 * CM,
        HüU=20 * CM,
    )


def make_model_config() -> ModelConfig:
    return ModelConfig(MoL=55 * CM, ZuvHoB=1 * CM)


def baby_trousers(meas: TrouserMeasurements, config: ModelConfig) -> PatternPart:
    ## Front Section
    # Anchor: top right

    # STEP 1:
    # Grundgerüst
    pt0 = Point(25 * CM, -40 * CM, "p1")
    pt1 = pt0.translate(0, meas.SiH)
    pt2 = pt1.translate(0, meas.SrH)
    pt3 = pt1.translate(0, meas.KnH)
    s_knee = Segment(pt3, pt3.translate(-meas.vHoB, 0), name="Knielinie")
    pt4 = pt1.translate(-meas.vHoB, 0)
    pt5 = pt0.translate(-meas.vHoB, 0)
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
    elems = elems + [
        Segment(
            pt11, pt11.translate(0, -4 * CM), style=StyleOptions(dash_array=[3, 2])
        ),
        s111,
    ]

    # # STEP 5
    # # Innenbeinnaht
    pt14 = pt9.translate(-(pt12.x - pt9.x), 0)
    pt13 = pt10.translate(-(meas.vHoB / 3 + 1 * CM), 0)
    elems = elems + [
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
    back_pt1 = back_pt0.translate(0, meas.SiH)
    back_pt2 = back_pt1.translate(0, meas.SrH)
    back_pt3 = back_pt1.translate(0, meas.KnH)
    s_knee_back = Segment(back_pt3, back_pt3.translate(-meas.vHoB, 0), name="Knielinie")
    back_pt4 = back_pt1.translate(-meas.vHoB, 0)
    back_pt5 = back_pt0.translate(-meas.vHoB, 0)
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
    elems = elems + back_elems
    return PatternPart(name="Baby Trousers with Nappies", elements=elems)


def boy_trousers(measurements, model_config) -> PatternPart:
    ## Front Section
    # Anchor: top right

    # STEP 1:
    # Grundgerüst
    pt0 = Point(25 * CM, -40 * CM, "p1")
    elems = []
    return PatternPart(name="Flat Boy Trousers", elements=elems)


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    measurements = make_measurements_trouser(person, allowance)
    model_config = make_model_config()
    part = baby_trousers(measurements, model_config)

    d = render_pattern_part(part, 60 * CM, 90 * CM)
    d.save_svg("children_shorts.svg")
