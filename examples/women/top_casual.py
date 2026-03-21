#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import GarmentPart, SeamValidationResult
from sewpat.blocks import BlockConfig, TopBlock
from sewpat.fitclass import FitClass
from sewpat.grids import GridConfig, TopGrid
from sewpat.measurements import GarmentConfig, make_top_measurements
from sewpat.pages import DinA0
from sewpat.pattern import Pattern, PatternConfig
from sewpat.person import (
    BalanceAdjustments,
    BalancedPerson,
    PersonalAdjustments,
    PersonAnalyser,
    load_person,
)
from sewpat.render import export_pattern_svg_mm
from sewpat.units import CM


class Part(GarmentPart):
    """Pattern parts for the waisted top with darts."""

    GRID = "Grid"
    BLOCK_BACK = "Block Back"
    BLOCK_FRONT = "Block Front"


def create_block(
    person: BalancedPerson,
    fit_class: FitClass,
    adjustments: PersonalAdjustments,
    config: GarmentConfig,
) -> Pattern:
    """Creates block pattern for a waisted top with darts.

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
    pattern = Pattern(name="Casual Top without Darts Block", anchor=layout.anchor)

    grid = TopGrid.from_measurements(
        meas=meas,
        fit_class=fit_class,
        hip_offset=adjustments.hip_offset,
        config=config,
        layout=layout,
        grid_config=GridConfig.CASUAL,
    )
    pattern.add_part(grid.part)

    block = TopBlock.from_measurements(
        meas=meas,
        config=config,
        grid=grid,
        block_config=BlockConfig.CASUAL,  # type: ignore[attr-defined]
        fit_class=fit_class,
        adjustments=adjustments,
        layout=layout,
        back_name=Part.BLOCK_BACK,
        front_name=Part.BLOCK_FRONT,
    )
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    # Verify seam lengths. Side seams must match closely (±2 mm).
    # The shoulder seam mismatch (~12 mm) is expected — the back shoulder is
    # intentionally longer due shoulder ease (Einhalteweite).
    seam_check: SeamValidationResult = pattern.validate_seam_pairs(
        [
            (Part.BLOCK_BACK, "side", Part.BLOCK_FRONT, "side"),  # ±2 mm (default)
            (Part.BLOCK_BACK, "shoulder", Part.BLOCK_FRONT, "shoulder", 13.0),  # ±12 mm per-pair
        ]
    )
    print(seam_check)

    return pattern


if __name__ == "__main__":
    person = load_person("Sarah", date="2025-07-30")
    fit_class = FitClass(pk=4, hip_ease=6 * CM)
    adjustments = PersonalAdjustments(
        hip_offset=2 * CM,
        balance=BalanceAdjustments(front_length=-0.9 * CM),
    )
    config = GarmentConfig(length=75 * CM, shoulder_gather=1 * CM, side_seam_intake_max=1 * CM)

    person_balanced = PersonAnalyser(person, adjustments.balance).get_balanced_person()

    pattern = create_block(person_balanced, fit_class, adjustments, config)

    pattern_parts = [Part.BLOCK_BACK, Part.BLOCK_FRONT]
    grid_parts = [Part.GRID]

    # With construction grid visible (for building / drafting)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "top_casual_grid.svg"),
        parts=grid_parts + pattern_parts,
        show_bezier_control_points=True,
        show_construction=True,
        show_seam_allowance=True,
        dark_mode=False,
    )

# #marker_single  top_waisted_dart.pdf ./
