#!/usr/bin/env python3
"""Blouse without arms — construction grid rebuilt with ConstructionGrid helper."""

from pathlib import Path

from sewpat import GarmentPart, SeamValidationResult, WidthValidationResult
from sewpat.blocks import BlockConfig, TopBlock, WideSleeveBlock
from sewpat.fitclass import FitClass
from sewpat.grids import GridConfig, TopGrid
from sewpat.measurements import GarmentConfig, make_top_measurements
from sewpat.pages import DinA0, DinA1
from sewpat.pattern import Pattern, PatternConfig
from sewpat.person import (
    BalanceAdjustments,
    BalancedPerson,
    PersonalAdjustments,
    PersonAnalyser,
    load_person,
)
from sewpat.pleat import PleatConfig
from sewpat.render import export_pattern_svg_mm
from sewpat.sleeve import ButtonConfig, CuffConfig, SleeveArmhole, SleeveConfig
from sewpat.units import CM


class Part(GarmentPart):
    """Pattern parts for the waisted top with darts."""

    GRID = "Grid"
    BLOCK_BACK = "Block Back"
    BLOCK_FRONT = "Block Front"
    WIDE_SLEEVE_GRID = "Wide Sleeve Grid"
    WIDE_SLEEVE = "Wide Sleeve"
    CUFF = "Cuff"


def create_block(
    person: BalancedPerson,
    fit_class: FitClass,
    adjustments: PersonalAdjustments,
    config: GarmentConfig,
    sleeve_config: SleeveConfig | None = None,
) -> Pattern:
    """Creates block pattern for a waisted top with darts.

    Args:
        person:        Balanced person — obtain via PersonAnalyser.get_balanced_person().
        fit_class:     Fit class defining construction offsets.
        adjustments:   Personal adjustments (hip offset, balance).
        config:        Garment configuration (length, seam allowance).
        sleeve_config: Optional wide sleeve config.  When given, a
                       :class:`~sewpat.blocks.WideSleeveBlock` is added to the
                       pattern as ``Part.WIDE_SLEEVE`` / ``Part.WIDE_SLEEVE_GRID``.

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
            (Part.BLOCK_BACK, "shoulder", Part.BLOCK_FRONT, "shoulder", 13.0, 10.0),  # 10–13 mm
        ]
    )
    print(seam_check)

    # Verify horizontal widths at bust, waist and hip levels.
    # Width is measured by intersecting the grid construction line with the
    # center and side seam edges of each pattern piece (via role tags), so
    # the check is independent of the page layout.
    #
    # Tolerance notes for the casual block:
    #   Bust  — straight centre-back; construction target within 5 mm.
    #   Waist — no waist darts are placed, so the dart allocation computed
    #            during construction (front_dart + back_dart) remains as
    #            extra width in the flat pattern.  The expected flat-pattern
    #            width is therefore  total_waist_width − 2·side_seam_intake
    #            (the construction width after side shaping only).
    #            The angled straight CB reaches its full hip_offset only at
    #            hip level, so its outline sits ~12 mm closer to centre at
    #            the waist → 15 mm tolerance covers this structural offset.
    #   Hip   — construction target; should be within 5 mm.
    wd = block.waist_distribution
    waist_expected = wd.total_waist_width - 2 * wd.side_seam_intake
    width_check: WidthValidationResult = pattern.validate_widths(
        [
            (
                Part.BLOCK_BACK,
                "center_back",
                "side",
                Part.BLOCK_FRONT,
                "center_front",
                "side",
                "Bust",
                grid.chest,
                meas.bust_width / 2,
            ),
            (
                Part.BLOCK_BACK,
                "center_back",
                "side",
                Part.BLOCK_FRONT,
                "center_front",
                "side",
                "Waist",
                grid.waist,
                waist_expected,
                15.0,
            ),
            (
                Part.BLOCK_BACK,
                "center_back",
                "side",
                Part.BLOCK_FRONT,
                "center_front",
                "side",
                "Hip",
                grid.hip,
                meas.hip_width / 2,
            ),
        ],
        tolerance_mm=5.0,
    )
    print(width_check)

    # ── Wide sleeve ───────────────────────────────────────────────────────────
    if sleeve_config is not None:
        armhole = SleeveArmhole.from_block(block, grid)
        sleeve_layout = PatternConfig()  # own coordinate origin — exported separately
        wide_sleeve = WideSleeveBlock.from_armhole(
            armhole,
            sleeve_config,
            layout=sleeve_layout,
            part_name=Part.WIDE_SLEEVE,
            cuff_part_name=Part.CUFF,
        )
        pattern.add_part(wide_sleeve.grid.part)
        pattern.add_part(wide_sleeve.part)
        if wide_sleeve.cuff is not None:
            pattern.add_part(wide_sleeve.cuff.part)

    return pattern


if __name__ == "__main__":
    person = load_person("Sarah", date="2025-07-30")
    fit_class = FitClass(pk=4, hip_ease=6 * CM)
    adjustments = PersonalAdjustments(
        hip_offset=2 * CM,
        balance=BalanceAdjustments(front_length=-0.9 * CM),
    )
    config = GarmentConfig(length=75 * CM, shoulder_gather=1 * CM, side_seam_intake_max=1 * CM)
    sleeve_config = SleeveConfig(
        sleeve_length=62 * CM,
        cap_offset=1 * CM,
        ease=0.0 * CM,
        cuff_config=CuffConfig(
            length=20 * CM,
            width=4 * CM,
            underlap=2 * CM,
            overlap=3 * CM,
            button_config=ButtonConfig(num_buttons=2),
        ),
        slit_height=8 * CM,
        pleat_config=PleatConfig(depth=3 * CM, num_pleats=3, spacing=1.5 * CM),
    )

    person_balanced = PersonAnalyser(person, adjustments.balance).get_balanced_person()

    pattern = create_block(person_balanced, fit_class, adjustments, config, sleeve_config)

    pattern_parts = [Part.BLOCK_BACK, Part.BLOCK_FRONT]
    grid_parts = [Part.GRID]
    sleeve_parts = [Part.WIDE_SLEEVE, Part.CUFF]
    sleeve_grid_parts = [Part.WIDE_SLEEVE_GRID]

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

    # Wide sleeve block with construction grid (separate page — fits DIN A1)
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA1.width,
        height_mm=DinA1.height,
        filename=str(Path(__file__).parent / "top_casual_wide_sleeve_grid.svg"),
        parts=sleeve_grid_parts + sleeve_parts,
        show_bezier_control_points=False,
        show_construction=True,
        show_seam_allowance=False,
        dark_mode=False,
    )

# #marker_single  top_waisted_dart.pdf ./
