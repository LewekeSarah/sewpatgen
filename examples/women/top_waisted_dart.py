#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import GarmentPart
from sewpat.blocks import TopBlock
from sewpat.fitclass import FitClass
from sewpat.grids import TopGrid
from sewpat.measurements import GarmentConfig, make_blouse_measurements
from sewpat.pages import DinA0
from sewpat.pattern import Pattern, PatternConfig
from sewpat.person import BalanceAdjustments, Person, PersonalAdjustments
from sewpat.render import export_pattern_svg_mm
from sewpat.units import CM


def make_person() -> Person:
    return Person(
        height=159 * CM,
        bust=83.5 * CM,
        waist=69.5 * CM,
        hip=93 * CM,
        hip_depth=24 * CM,
        bust_depth=27.5 * CM,
        neck_size=6.5 * CM,
        bust_span=8.3 * CM,
        shoulder_width=12.1 * CM,
        back_length=39 * CM,
        front_length=43.4 * CM,
    )


def make_fit_class() -> FitClass:
    return FitClass(pk=4, bust_point_ease=0.5 * CM)


def make_adjustments() -> PersonalAdjustments:
    return PersonalAdjustments(
        hip_offset=1 * CM,
        balance=BalanceAdjustments(front_length=-0.9 * CM),
    )


def make_config() -> GarmentConfig:
    return GarmentConfig(length=75 * CM)


class Part(GarmentPart):
    """Pattern parts for the waisted top with darts."""
    GRID        = "Grid"
    BLOCK_BACK  = "Block Back"
    BLOCK_FRONT = "Block Front"


def make_blouse(person: Person, fit_class: FitClass, adjustments: PersonalAdjustments, config: GarmentConfig) -> Pattern:
    from sewpat.measurements import make_blouse_measurements
    meas = make_blouse_measurements(person, fit_class, adjustments)

    layout = PatternConfig()
    pattern = Pattern(name="Waisted Top with Darts Block", anchor=layout.anchor)

    grid = TopGrid.from_measurements(meas=meas, fit_class_or_model=fit_class, adjustments=adjustments, config=config, layout=layout)
    pattern.add_part(grid.part)

    block = TopBlock.from_measurements(
        meas=meas,
        fit_class_or_model=fit_class,
        adjustments=adjustments,
        config=config,
        layout=layout,
        back_name=Part.BLOCK_BACK,
        front_name=Part.BLOCK_FRONT,
    )
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    return pattern


if __name__ == "__main__":
    person      = make_person()
    fit_class   = make_fit_class()
    adjustments = make_adjustments()
    config      = make_config()
    pattern     = make_blouse(person, fit_class, adjustments, config)

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
