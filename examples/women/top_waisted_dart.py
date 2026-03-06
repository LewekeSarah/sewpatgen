#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import GarmentPart
from sewpat.blocks import TopBlock
from sewpat.fitclass import FitClass
from sewpat.grids import TopGrid
from sewpat.measurements import GarmentConfig, make_top_measurements
from sewpat.pages import DinA0
from sewpat.pattern import Pattern, PatternConfig
from sewpat.person import BalanceAdjustments, BalancedPerson, Person, PersonalAdjustments, PersonAnalyser, load_person
from sewpat.render import export_pattern_svg_mm
from sewpat.units import CM


class Part(GarmentPart):
    """Pattern parts for the waisted top with darts."""
    GRID        = "Grid"
    BLOCK_BACK  = "Block Back"
    BLOCK_FRONT = "Block Front"


def create_block(person: BalancedPerson, fit_class: FitClass, adjustments: PersonalAdjustments, config: GarmentConfig) -> Pattern:
    """ Creates block pattern for a waisted top with darts.

    Args:
        person:     Balanced person — obtain via PersonAnalyser.get_balanced_person().
        fit_class:  Fit class defining construction offsets.
        adjustments: Personal adjustments (hip offset, balance).
        config:     Garment configuration (length, seam allowance).

    Returns:
        A Pattern object representing the waisted top with darts block.
    """
    meas = make_top_measurements(person, fit_class)

    layout = PatternConfig()
    pattern = Pattern(name="Waisted Top with Darts Block", anchor=layout.anchor)

    grid = TopGrid.from_measurements(meas=meas, fit_class=fit_class, hip_offset=adjustments.hip_offset, config=config, layout=layout)
    pattern.add_part(grid.part)

    block = TopBlock.from_measurements(
        meas=meas,
        fit_class=fit_class,
        hip_offset=adjustments.hip_offset,
        config=config,
        layout=layout,
        back_name=Part.BLOCK_BACK,
        front_name=Part.BLOCK_FRONT,
    )
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    return pattern


if __name__ == "__main__":
    person      = load_person("Sarah", date="2025-07-30")
    fit_class   = FitClass(pk=4)
    adjustments = PersonalAdjustments(
        hip_offset=1 * CM,
        balance=BalanceAdjustments(front_length=-0.9 * CM),
    )
    config      = GarmentConfig(length=75 * CM)

    person_balanced = PersonAnalyser(person, adjustments.balance).get_balanced_person()

    pattern     = create_block(person_balanced, fit_class, adjustments, config)

    pattern_parts = [Part.BLOCK_BACK, Part.BLOCK_FRONT]
    grid_parts    = [Part.GRID]

    # With construction grid visible (for building / drafting)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "top_waisted_dart_grid.svg"),
        parts=grid_parts + pattern_parts,
        show_bezier_control_points=False,
        show_construction=False,
        show_seam_allowance=True
    )

# #marker_single  top_waisted_dart.pdf ./
