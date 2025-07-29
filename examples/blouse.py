#!/usr/bin/env python3
"""Blouse without arms
"""

import math
import numpy as np

from sewpat.geometry import Point, Segment, Line, Ray, Circle
from sewpat.part import PatternPart
from sewpat.render import save_pattern_part_svg, render_pattern_part
from sewpat.person import Person


def make_person() -> Person:
    return Person(
        Körperhöhe = 0.0,
        BrU = 0.0,
        TaU = 0.0,
        HüU = 0.0,
        AlT = 0.0,
        HüT = 0.0,
        BrT = 0.0,
        HlB = 0.0,
        RüB = 0.0,
        ArD = 0.0,
        BrB = 0.0,
        BrPA = 0.0,
        SuB = 0.0,
        RüL = 0.0,
        VL = 0.0,
    )


def make_blouse(person: Person) -> PatternPart:
    elems = []

    return PatternPart(name = "Blouse", elements=elems)

if __name__ == "__main__":
    person = make_person()
    part = make_blouse(person)
