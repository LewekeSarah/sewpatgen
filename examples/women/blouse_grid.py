#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat.geometry import (
    Point,
    Segment,
    intersect,
    segment_to_intersection,
)
from sewpat.units import CM
from sewpat.measurments import make_blouse_measurements
from sewpat.pages import DinA0
from sewpat.part import PatternPart, Pattern, ConstructionGrid
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

    ## STEP 2.1  — Anchor: top left
    pt1 = Point(5 * CM, 5 * CM, "p1")

    pattern = Pattern(name="Blouse", anchor=pt1)

    # -----------------------------------------------------------------------
    # KONSTRUKTIONSGITTER  (horizontal = Querlinien, vertikal = Längslinien)
    # -----------------------------------------------------------------------
    # Horizontal lines are placed at y-offsets from pt1 (increasing downward).
    # Vertical lines are placed at x-offsets from pt1 (increasing rightward).
    #
    # NOTE: The manual construction (STEP 2.6) derives pt7 via the intersection
    # of the line pt1→pt6 (where pt6 = pt4 + BeckenAdjustment) with the
    # Brustlinie.  This shifts all breast-width verticals by
    #   pt7_shift = BeckenAdjustment × AlT / RüL
    # relative to the raw anchor pt1.  All vertical offsets below must
    # therefore start from (hintere Mitte + pt7_shift) — not from pt1.
    #
    # Additionally, the 10 cm between Seitenlinie RT and Seitenlinie VT
    # (Einsatzbreite) is NOT part of BrW, so "vordere Mitte" must be
    # BrW/2 + 10 cm — not BrW/2 — when measured from the same anchor.
    pt7_shift = model.BeckenAdjustment * meas.AlT / meas.RüL
    grid = ConstructionGrid(
        anchor=pt1,
        horizontals=[
            ("Schulterlinie",  0),
            ("Brustlinie",     meas.AlT),
            ("Taillenlinie",   meas.RüL),
            ("Hüftlinie",      meas.RüL + meas.HüT),
            ("Saumlinie",      model.MoL),
        ],
        verticals=[
            ("hintere Mitte",  0),
            ("hintere Armlinie",   pt7_shift + meas.RüB),
            ("Seitenlinie RT", pt7_shift + meas.RüB + meas.ArD * 2 / 3),
            ("Seitenlinie VT", pt7_shift + meas.RüB + meas.ArD * 2 / 3 + 10 * CM),
            ("vordere Armlinie",   pt7_shift + meas.RüB + meas.ArD * 2 / 3 + 10 * CM + meas.ArD / 3),
            ("vordere Mitte",  pt7_shift + meas.BrW / 2 + 10 * CM),
        ],
        part_name="Konstruktionsgitter Grundgerüst",
    )
    grid_part = grid.build()
    pattern.add_part(grid_part)

    # Retrieve grid lines directly from the built part by name.
    seg_schulterlinie  = grid_part.get_element("Schulterlinie").geometry
    seg_brustlinie     = grid_part.get_element("Brustlinie").geometry
    seg_taillenlinie   = grid_part.get_element("Taillenlinie").geometry
    seg_hueftlinie     = grid_part.get_element("Hüftlinie").geometry
    seg_saumlinie      = grid_part.get_element("Saumlinie").geometry

    seg_hint_armlinie  = grid_part.get_element("hintere Armlinie").geometry
    seg_seite_rt       = grid_part.get_element("Seitenlinie RT").geometry
    seg_seite_vt       = grid_part.get_element("Seitenlinie VT").geometry
    seg_vord_armlinie  = grid_part.get_element("vordere Armlinie").geometry
    seg_vordere_mitte  = grid_part.get_element("vordere Mitte").geometry

    # -----------------------------------------------------------------------
    # GRUNDGERÜST — construction detail lines built on top of the grid
    # -----------------------------------------------------------------------
    part = PatternPart(name="Grundgerüst")
    pattern.add_part(part)

    # STEP 2.2 — Modelllänge (vertical spine along hintere Mitte)
    pt2 = pt1.translate(0, model.MoL)

    ## STEP 2.6 — pt7: intersection of the BeckenAdjustment diagonal with the Brustlinie
    # pt4 lies on the Taillenlinie directly below pt1; pt6 shifts it by BeckenAdjustment.
    # The resulting diagonal pt1→pt6 crosses the Brustlinie at pt7, which is the
    # start-point for all breast-width measurements.
    pt4 = pt1.translate(0, meas.RüL)
    pt6 = pt4.translate(model.BeckenAdjustment, 0)
    pt9 = pt2.translate(model.BeckenAdjustment, 0)
    pt7 = intersect(Segment(pt1, pt6), seg_brustlinie)[0]

    ## STEP 3.1 — hintere Armlinie (pt10)
    # Read pt10 directly from the grid: intersection of "hintere Armlinie" with Brustlinie.
    pt10 = intersect(seg_hint_armlinie, seg_brustlinie)[0]

    ## STEP 3.2 — Seitenlinie RT (pt11)
    pt11 = intersect(seg_seite_rt, seg_brustlinie)[0]

    ## STEP 3.3 — Seitenlinie VT (pt12)
    pt12 = intersect(seg_seite_vt, seg_brustlinie)[0]

    ## STEP 3.4 — vordere Armlinie (pt13)
    pt13 = intersect(seg_vord_armlinie, seg_brustlinie)[0]

    ## STEP 3.5 — vordere Mitte (pt14)
    pt14 = intersect(seg_vordere_mitte, seg_brustlinie)[0]

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

    pattern_parts = ["Grundgerüst"]
    grid_parts = ["Konstruktionsgitter Grundgerüst"]

    # With construction grid visible (for building / drafting)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "blouse_grid.svg"),
        parts=grid_parts + pattern_parts,
    )

    # Clean version — construction grid not included
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "blouse_grid_clean.svg"),
        parts=pattern_parts,
    )
#marker_single  top_waisted_dart.pdf ./