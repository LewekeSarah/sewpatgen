#!/usr/bin/env python3
"""Blouse without arms"""


from sewpat.geometry import (
    Point,
    Segment,
    intersect,
    segment_to_intersection,
)
from sewpat.units import CM
from sewpat.measurments import make_blouse_measurements
from sewpat.pages import DinA0
from sewpat.part import PatternPart, Pattern
from sewpat.render import export_pattern_svg_mm
from sewpat.measurments import Allowance, BlouseMeasurements, ModelConfig
from sewpat.person import Person, BalanceAdjustments


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
    return ModelConfig(MoL=55 * CM, BeckenAdjustment=1 * CM)


def make_balance() -> BalanceAdjustments:
    return BalanceAdjustments(VL=-0.9 * CM)


def make_blouse(meas: BlouseMeasurements, model: ModelConfig) -> Pattern:
    # SVG coordinates: x increases right, y increases down

    ## STEP 2.1
    # Anchor: top left
    pt1 = Point(5 * CM, 5 * CM, "p1")

    pattern = Pattern(name="Blouse", anchor=pt1)
    part = PatternPart(name="Grundgerüst")
    pattern.add_part(part)

    ## STEP 2.2
    pt2 = pt1.translate(0, model.MoL)
    part.append(Segment(pt1, pt2, "Modelllänge"))
    seg_saumlinie = Segment(pt2, pt2.translate(60 * CM, 0), "Saumlinie")
    part.append(seg_saumlinie)
    seg_schulterlinie = Segment(pt1, pt1.translate(25 * CM, 0), "Schulterlinie")
    part.append(seg_schulterlinie)

    ## STEP 2.3
    pt3 = pt1.translate(0, meas.AlT)
    seg_brustlinie = Segment(pt3, pt3.translate(60 * CM, 0), "Brustlinie")
    part.append(seg_brustlinie)

    ## STEP 2.4
    pt4 = pt1.translate(0, meas.RüL)
    seg_taillenlinie = Segment(pt4, pt4.translate(60 * CM, 0), "Taillenlinie")
    part.append(seg_taillenlinie)

    ## STEP 2.5
    pt5 = pt4.translate(0, meas.HüT)
    seg_hueftlinie = Segment(pt5, pt5.translate(60 * CM, 0), "Hüftlinie")
    part.append(seg_hueftlinie)

    ## STEP 2.6
    pt6 = pt4.translate(model.BeckenAdjustment, 0)
    pt9 = pt2.translate(model.BeckenAdjustment, 0)
    pt7 = intersect(Segment(pt1, pt6), seg_brustlinie)[0]
    part.append(Segment(pt1, pt6))
    part.append(Segment(pt6, pt9))

    ## STEP 3.1
    pt10 = pt7.translate(meas.RüB, 0)
    # Invertiere die Richtung der Normalen, damit der Strahl korrekt auf den Schnittpunkt zeigt
    _, s = segment_to_intersection(pt10, -seg_brustlinie.unit_normal, seg_schulterlinie)
    s.name = "hintere Armlinie"
    part.append(s)
    _, s = segment_to_intersection(pt10, seg_brustlinie.unit_normal, seg_hueftlinie)
    part.append(s)

    ## STEP 3.2
    pt11 = pt10.translate(meas.ArD * 2 / 3, 0)
    _, s = segment_to_intersection(pt11, seg_saumlinie.unit_normal, seg_hueftlinie)
    s.name = "Seitenlinie RT"
    part.append(s)

    ## STEP 3.3
    pt12 = pt11.translate(10 * CM, 0)
    _, s = segment_to_intersection(pt12, seg_brustlinie.unit_normal, seg_hueftlinie)
    s.name = "Seitenline VT"
    part.append(s)

    ## STEP 3.4
    pt13 = pt12.translate(meas.ArD / 3, 0)
    part.append(Segment(pt13, pt13.translate(0, -25 * CM)))
    _, s = segment_to_intersection(pt13, seg_brustlinie.unit_normal, seg_taillenlinie)
    s.name = "vordere Armlinie"
    part.append(s)

    ## STEP 3.5
    pt14 = pt13.translate(meas.BrB, 0)
    _, s = segment_to_intersection(pt14, seg_brustlinie.unit_normal, seg_hueftlinie)
    s.name = "vordere Mitte (vM)"
    part.append(s)
    part.append(Segment(pt14, pt14.translate(0, -30 * CM)))

    if not (pt14.coords == pt7.translate((meas.BrW / 2 + 10 * CM), 0).coords).all():
        raise ValueError("BrW is plotted incorrect.")

    return pattern


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    balance = make_balance()
    measurements = make_blouse_measurements(person, allowance, balance)
    model_config = make_model_config()
    pattern = make_blouse(measurements, model_config)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename="women/blouse.svg",
    )
