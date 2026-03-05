#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import (
    GarmentPart,
)
from sewpat.blocks import TopBlock
from sewpat.grids import TopGrid
from sewpat.measurements import (
    Allowance,
    BlouseMeasurements,
    ModelConfig,
    make_blouse_measurements,
)
from sewpat.pages import DinA0
from sewpat.pattern import Pattern, PatternConfig
from sewpat.person import BalanceAdjustments, Person
from sewpat.render import export_pattern_svg_mm
from sewpat.units import CM


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
    # TODO the ZuBrA depends on the Passformklasse PK <4: 0-0.5cm, 5 <= PK < 8: 1cm, PK >=0: 1.5cm
    return ModelConfig(MoL=75 * CM, BeckenAdjustment=1 * CM, ZuBrA=0.5 * CM)


def make_balance() -> BalanceAdjustments:
    return BalanceAdjustments(VL=-0.9 * CM)


class Part(GarmentPart):
    """Pattern parts for the waisted top with darts."""
    GRID        = "Grid"
    BLOCK_BACK  = "Block Back"
    BLOCK_FRONT = "Block Front"


# -----------------------------------------------------------------------
def make_blouse(meas: BlouseMeasurements, model: ModelConfig) -> Pattern:

    config = PatternConfig()
    pattern = Pattern(name="Waisted Top with Darts Block", anchor=config.anchor)

    # -----------------------------------------------------------------------
    # Grid — construction detail lines
    # -----------------------------------------------------------------------
    grid = TopGrid.from_measurements(meas=meas, model=model, config=config)
    pattern.add_part(grid.part)

    # -----------------------------------------------------------------------
    # Block — both pieces built and returned as a typed TopBlock
    # -----------------------------------------------------------------------
    block = TopBlock.from_measurements(
        meas=meas,
        model=model,
        config=config,
        back_name=Part.BLOCK_BACK,
        front_name=Part.BLOCK_FRONT,
    )
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    return pattern


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    balance = make_balance()
    measurements = make_blouse_measurements(person, allowance, balance)
    model_config = make_model_config()
    pattern = make_blouse(measurements, model_config)

    pattern_parts = [Part.BLOCK_BACK, Part.BLOCK_FRONT]
    grid_parts = [] # [Part.GRID]

    # With construction grid visible (for building / drafting)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(Path(__file__).parent / "top_waisted_dart_grid.svg"),
        parts=grid_parts + pattern_parts,
        show_bezier_control_points=False,
        show_construction=True,
        show_seam_allowance=True
    )

# #marker_single  top_waisted_dart.pdf ./
