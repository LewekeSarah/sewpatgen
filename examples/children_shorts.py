from sewpat import Segment, PatternPart
from sewpat.geometry import CM, Point, segment_to_intersection, intersect, Ray, Circle
from sewpat.measurments import ModelConfig, BlouseMeasurements, Allowance, make_measurements_trouser, \
    TrouserMeasurements
from sewpat.person import Gender, Person
from sewpat.render import render_pattern_part


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
        gender=Gender.male
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
    pt0 = Point(20 * CM, -40 * CM, "p1")
    pt1 = pt0.translate(0, meas.SiH)
    pt2 = pt1.translate(0, meas.SrH)
    pt3 = pt1.translate(0, 0.5 * meas.SrH)
    pt4 = pt1.translate(meas.vHoB, 0)
    pt5 = pt0.translate(meas.vHoB, 0)
    s45 = Segment(pt4, pt5, name="4-5")
    pt6 = pt4.translate(0, -1/12 * meas.HüW)
    pt7 = pt4.translate(meas.vHoB * 0.25 + config.ZuvHoB, 0)
    s47 = Segment(pt4, pt7, name="4-7")
    pt4_aux = intersect(Ray(pt4, - s45.unit_normal + s47.unit_normal), Circle(pt4, 1.75*CM))
    pt8 = pt1.translate(0.5 * meas.vHoB - 0.5 *CM, 0)
    pt9 = pt3.translate(0.5 * meas.vHoB - 0.5 *CM, 0)
    pt10 = pt2.translate(0.5 * meas.vHoB - 0.5 *CM, 0)
    pt11 = pt10.translate(- (meas.vHoB / 3 + 1 * CM), 0)
    pt11_tmp = pt11.translate(0, -4 * CM)
    pt13 = pt10.translate(meas.vHoB / 3 + 1 * CM, 0)
    # TODO att pt 14 as distance 9-12 other side
    elems = [
        Segment(pt0, pt1, name="0-1"),
        Segment(pt1, pt2, name="1-2"),
        Segment(pt1, pt3, name="1-3"),
        Segment(pt3, pt3.translate(meas.vHoB, 0)),
        Segment(pt1, pt4, name="1-4"),
        Segment(pt5, pt0),
        s45,
        s47,
        Segment(pt4, pt4_aux[0]),
        # TODO add curve 5-6-7 over aux point 1.75cm away from 4
        Segment(pt8, pt10, name="8-10"),
        Segment(pt10, pt11, name="10-11"),
        Segment(pt11, pt11_tmp),
        # TODO add curve 11_tmp-1 mark intersection with knee as 12
        Segment(pt10, pt13, name="10-13"),
        # TODO add line 14-7
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
