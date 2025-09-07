from sewpat import Segment, PatternPart
from sewpat.geometry import CM, Point, segment_to_intersection, intersect, Ray, Circle, CubicBezier
from sewpat.measurments import ModelConfig, BlouseMeasurements, Allowance, make_measurements_trouser, \
    TrouserMeasurements
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
        SiH=20.4 * CM, # SiH = body_rise / Sitzhöhe
        SrH=55 * CM, # SrH = inside leg / Schritthöhe
        gender=Gender.boy
    )


def make_allowance() -> Allowance:
    return Allowance(
        SiH=4.5 * CM,
        SrH=- 2 * CM,
        HüU=5 * CM,
    )


def make_model_config() -> ModelConfig:
    return ModelConfig(MoL=55 * CM, ZuvHoB=1 * CM)


def shorts(meas: TrouserMeasurements, config: ModelConfig) -> PatternPart:
    ## Front Section
    # Anchor: top right

    # STEP 1:
    # Grundgerüst
    pt0 = Point(20 * CM, -40 * CM, "p1")
    pt1 = pt0.translate(0, meas.SiH)
    pt2 = pt1.translate(0, meas.SrH)
    pt3 = pt1.translate(0, meas.KnH)
    s_knee = Segment(pt3, pt3.translate(meas.vHoB, 0), name="Knielinie")
    pt4 = pt1.translate(meas.vHoB, 0)
    pt5 = pt0.translate(meas.vHoB, 0)
    s45 = Segment(pt4, pt5, name="4-5")
    base_grid = [
        Segment(pt0, pt2, name="Seitlich Taillenhöhe"),
        Segment(pt2, pt2.translate(meas.vHoB, 0), "Saumlinie"),
        s_knee,
        Segment(pt1, pt4, name="Schrittlinie"),
        Segment(pt5, pt0, name="Taillenlinie"),
        s45
    ]

    # STEP 2:
    # Hosenbeingitter
    pt6 = pt4.translate(0, -1/12 * meas.HüW)
    pt7 = pt4.translate(meas.vHoB * 0.25 + config.ZuvHoB, 0)
    s47 = Segment(pt4, pt7, name="Hosenausschnitt")
    pt8 = pt1.translate(0.5 * meas.vHoB - 0.5 *CM, 0)
    pt9 = pt3.translate(0.5 * meas.vHoB - 0.5 *CM, 0)
    pt10 = pt2.translate(0.5 * meas.vHoB - 0.5 *CM, 0)
    base_leg = [
        s47,
        Segment(pt8, pt10, name="Vorderhosenbruch / Fadenlauf")
    ]

    # STEP 3:
    # Hosenausschnitt
    pt4_aux = intersect(Ray(pt4, - s45.unit_normal + s47.unit_normal), Circle(pt4, 1.75*CM))
    s44_aux = Segment(pt4, pt4_aux[0], style=StyleOptions(dash_array=[3, 2]))
    pt4_bz1 = s44_aux.point_perpendicular(0.3 *CM, rel_pos_on_obj=1).translate(0, -0.1 * CM)
    pt4_bz2 = s44_aux.point_perpendicular(-0.3*CM, rel_pos_on_obj=1).translate(0, 0.1 * CM)
    elems = base_grid + base_leg + [
        s44_aux,
        CubicBezier(pt6, pt4.translate(0, - 3 * CM), pt4_bz1, pt4_aux[0]),
        CubicBezier(pt4_aux[0], pt4_bz2, pt7.translate(0.75 * CM, 0), pt7),
    ]

    # STEP 4
    # Seitennaht
    pt11 = pt10.translate(- (meas.vHoB / 3 + 1 * CM), 0)
    pt11_tmp = pt11.translate(0, -20 * CM)
    s111 = CubicBezier(pt11, pt11_tmp, pt3.translate(0, 20 * CM), pt1)
    pt12 = intersect(s111, s_knee)[0]
    elems = elems + [
        pt3.translate(0, 20 * CM),
        pt11.translate(0, -4 * CM),
        Segment(pt11, pt11.translate(0, -4 * CM), style=StyleOptions(dash_array=[3, 2]), name="Seitennaht"),
        s111,
    ]

    # STEP 5
    # Innenbeinnaht
    pt14 = pt9.translate(-(pt12.x - pt9.x), 0)
    pt13 = pt10.translate(meas.vHoB / 3 + 1 * CM, 0)
    elems = elems + [
        Segment(pt10, pt13, name="Innenbeinnaht"),
        Segment(pt14, pt7, style=StyleOptions(dash_array=[3, 2])),
        CubicBezier(pt13, pt13.translate(0, - 10 * CM), pt14.translate(1.5 * CM, 10 * CM), pt14),
        CubicBezier(pt14, pt14.translate(-1.5 * CM, -10 * CM), pt7.translate(2 * CM, (pt14.y - pt7.y) / 3), pt7),
    ]


    back_start = pt5.translate(- 20 * CM, 0)
    pt15 = back_start.translate(2 * CM, 0)
    pt16 = pt15.translate(0, 2 * CM)
    back_elems = [
        Segment(back_start, pt15),
        Segment(pt15, pt16),
    ]
    elems = elems + back_elems
    return PatternPart(name="Children Shorts", elements=elems)


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    measurements = make_measurements_trouser(person, allowance)
    model_config = make_model_config()
    part = shorts(measurements, model_config)

    d = render_pattern_part(part, 50 * CM, 90 * CM)
    d.save_svg("children_shorts.svg")
