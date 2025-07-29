#!/usr/bin/env python3
"""Blouse without arms
"""

import math
import numpy as np

from sewpat.geometry import Point, Segment, Line, Ray, Circle
from sewpat.part import PatternPart
from sewpat.render import save_pattern_part_svg, render_pattern_part
from sewpat.measurments import Person, Allowance, ConstructionMeasurments, ModelConfig


def make_person() -> Person:
    return Person(
        KöH = 159,
        BrU = 83.5,
        TaU = 69.5,
        HüU = 93,
        AlT = 19.4,
        HüT = 24,
        BrT = 27.5,
        HlB = 6.5,
        RüB = 16,
        ArD = 8.9,
        BrB = 16.8,
        BrPA = 8.3,
        SuB = 12.1,
        RüL = 39,
        VL = 43.4,
    )


def make_allowance() -> Allowance:
    return Allowance(
        RüB = 1.0,
        ArD = 2.0,
        BrB = 1.5,
        AlT = 1.5,
        TaU = 8.0,
        HüU = 6.0,
    )


def make_measurements(
    person: Person, allowance: Allowance,
) -> ConstructionMeasurments:
    person
    measurements = {
        key: val for key, val in person.__dict__.items()
    }
    for key, val in allowance.__dict__.items():
        if key not in ["TaU", "BrU", "HüU"]:
            measurements[key] += val
    for perimeter, width in zip(["TaU", "BrU", "HüU"],["TaW", "BrW", "HüW"]):
        measurements[width] = measurements[perimeter] + allowance.__getattribute__(perimeter)
    measurements.pop("KöH")
    return ConstructionMeasurments(**measurements)


def make_model_config() -> ModelConfig:
    return ModelConfig(
        MoL=55.,
        BeckenAdjustment=1.
    )


def make_blouse(person: Person) -> PatternPart:
    elems = []

    return PatternPart(name = "Blouse", elements=elems)


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    measurements = make_measurements(person, allowance)
    model_config = make_model_config()
    part = make_blouse(measurements, model_config)
