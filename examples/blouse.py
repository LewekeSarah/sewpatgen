#!/usr/bin/env python3
"""Blouse without arms"""

import math
import numpy as np

from sewpat.geometry import (
    Point,
    Segment,
    Line,
    Ray,
    Circle,
    intersect,
    segment_to_intersection,
    CM,
    MM,
)
from sewpat.measurments import BalanceAdjustements, make_measurements
from sewpat.part import PatternPart
from sewpat.render import render_pattern_part
from sewpat.measurments import Person, Allowance, ConstructionMeasurments, ModelConfig


def make_person() -> Person:
    return Person(
        KöH=159 * CM,
        BrU=83.5 * CM,
        TaU=69.5 * CM,
        HüU=93 * CM,
        AlT=19.4 * CM,
        HüT=24 * CM,
        BrT=27.5 * CM,
        HlB=6.5 * CM,
        RüB=16 * CM,
        ArD=8.9 * CM,
        BrB=16.8 * CM,
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


def make_balance() -> BalanceAdjustements:
    return BalanceAdjustements(
        VL=-0.9 * CM
    )


def make_blouse(meas: ConstructionMeasurments, model: ModelConfig) -> PatternPart:
    elems = []

    # SVG coordinates: x increases right, y increases down

    ## STEP 2.1
    # Anchor: top right
    pt1 = Point(0, 0, "p1")

    ## STEP 2.2
    pt2 = pt1.translate(0, model.MoL)
    elems.append(Segment(pt1, pt2, "Modelllänge"))
    segSaumlinie = Segment(pt2, pt2.translate(-60 * CM, 0), "Saumlinie")
    elems.append(segSaumlinie)
    segSchulterlinie = Segment(pt1, pt1.translate(-25 * CM, 0), "Schulterlinie")
    elems.append(segSchulterlinie)

    ## STEP 2.3
    pt3 = pt1.translate(0, meas.AlT)
    segBrustlinie = Segment(pt3, pt3.translate(-60 * CM, 0), "Brustlinie")
    elems.append(segBrustlinie)

    ## STEP 2.4
    pt4 = pt1.translate(0, meas.RüL)
    segTaillenlinie = Segment(pt4, pt4.translate(-60 * CM, 0), "Taillenlinie")
    elems.append(segTaillenlinie)

    ## STEP 2.5
    pt5 = pt4.translate(0, meas.HüT)
    segHüftlinie = Segment(pt5, pt5.translate(-60 * CM, 0), "Hüftlinie")
    elems.append(segHüftlinie)

    ## STEP 2.6
    pt6 = pt4.translate(-model.BeckenAdjustment, 0)
    pt9 = pt2.translate(-model.BeckenAdjustment, 0)
    pt7 = intersect(Segment(pt1, pt6), segBrustlinie)[0]
    elems.append(Segment(pt1, pt6))
    elems.append(Segment(pt6, pt9))

    ## STEP 3.1
    pt10 = pt7.translate(-meas.RüB, 0)
    pt16, s = segment_to_intersection(pt10, segBrustlinie.unit_normal, segSchulterlinie)
    s.name = "hintere Armlinie"
    elems.append(s)
    _, s = segment_to_intersection(pt10, -segBrustlinie.unit_normal, segSaumlinie)
    elems.append(s)

    return PatternPart(name="Blouse", elements=elems)


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    balance = make_balance()
    measurements = make_measurements(person, allowance, balance)
    model_config = make_model_config()
    part = make_blouse(measurements, model_config)

    d = render_pattern_part(part, 5000, 5000)
    d.save_svg("blouse.svg")
