"""Pre-built garment blocks for common pattern types.

Each block is a pair of frozen dataclasses — one per pattern piece — bundled
in a thin container class that mirrors the :class:`~sewpat.grids.TopGrid`
convention.  Callers never touch fragile string lookups; every key point and
edge is a typed, named attribute with full IDE autocomplete.

Example::

    from sewpat.blocks import BlockConfig, TopBlock
    from sewpat.fitclass import FitClass
    from sewpat.grids import GridConfig, TopGrid
    from sewpat.measurements import GarmentConfig

    fc    = FitClass(pk=4)
    cfg   = GarmentConfig(length=75 * CM)
    grid  = TopGrid.from_measurements(meas, fc, cfg, GridConfig.WAISTED_DART,
                                      hip_offset=1*CM)
    block = TopBlock.from_measurements(meas, cfg, grid, BlockConfig.WAISTED_DART)
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    # Extend the armscye edge with a collar:
    pt_collar = block.back.armscye_control.translate(0, -2 * CM)
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._blocks_assembly import _assemble_back_part, _assemble_front_part
from ._blocks_geometry import (
    _build_back_geometry,
    _build_darts,
    _build_front_geometry,
    _build_side_seams,
)
from .geometry import CubicBezier, Dart, Point, Segment, intersect
from .grids import TopGrid
from .measurements import (
    BlouseMeasurements,
    GarmentConfig,
    calculate_hip_distribution,
    calculate_waist_distribution,
)
from .pattern import PatternConfig, PatternPart
from .person import PersonalAdjustments
from .style import STYLE_STITCH
from .units import CM

if TYPE_CHECKING:
    from .fitclass import FitClass


@dataclass(frozen=True)
class BlockConfig:
    """Block-level construction choices for :class:`TopBlock`.

    These constants govern how the *pattern piece* is drawn, independent of
    the underlying construction grid.  They are deliberately separate from
    :class:`~sewpat.grids.GridConfig` because the grid describes measurement
    geometry whereas ``BlockConfig`` describes drafting decisions.

    Use the pre-built class-level presets:

    * ``BlockConfig.WAISTED_DART`` — waisted top with bust dart; kinked
      center-back (two segments, bend at waist).
    * ``BlockConfig.CASUAL``       — casual top; straight center-back (single
      line from shoulder through the hip-offset point to the hem).

    Attributes:
        straight_center_back: When ``False`` the center-back outline is drafted
            as two segments that meet at a kink at the waist adjustment point.
            When ``True`` a single straight line is drawn from the
            shoulder/centre intersection through the hip-offset point to the hem.
        has_shoulder_dart: When ``True`` the front shoulder seam is derived via
            bust-point pivot, producing a split seam with a shoulder dart.
            When ``False`` a single unbroken shoulder seam is constructed
            directly (no dart).
        has_waist_dart: When ``True`` front and back waist darts are constructed.
            When ``False`` (casual block) waist shaping comes from the side seam
            only; no waist dart elements are created.
        neckline_ease_y: Vertical ease added to the front neckline depth.
        neckline_ease_x: Horizontal ease added to shoulder_front_neckline_pt.
        armscye_front_offset: Length subtracted from the front armscye seam
            relative to the back, controlling cap ease.
        shoulder_ease: Parallel offset applied to both shoulder seams.
        shoulder_raise: Vertical raise at the back neckline shoulder point.
        shoulder_dart_width: Width of the back shoulder dart cut into the armscye.
        armscye_front_cp_x: X offset of the front armscye Bézier control point.
        armscye_front_cp_y: Y offset of the front armscye Bézier control point.
        side_hip_tangent: Length of the control-point tangent for side-hip curves.
        waist_offset: Distance the waist construction line is raised above the
            waist grid line.
        armscye_back_aux_offset: X offset placing the shoulder-blade checkpoint.
        armscye_back_offset: X offset for the armscye notch control point.
        armscye_back_cp_x: X offset of the back armscye lower Bézier CP.
        armscye_back_cp_y: Y offset of the back armscye lower Bézier CP.
    """

    # ── Style ────────────────────────────────────────────────────────────────
    straight_center_back: bool = False
    has_shoulder_dart: bool = True
    has_waist_dart: bool = True

    # ── Neckline ─────────────────────────────────────────────────────────────
    neckline_ease_y: float = 1.5 * CM
    neckline_ease_x: float = 0.0

    # ── Armscye front ────────────────────────────────────────────────────────
    armscye_front_offset: float = 2.0 * CM
    armscye_front_cp_x: float = -5.0 * CM
    armscye_front_cp_y: float = -3.0 * CM

    # ── Shoulder ─────────────────────────────────────────────────────────────
    shoulder_ease: float = 1.0 * CM
    shoulder_raise: float = 2.0 * CM
    shoulder_dart_width: float = 1.5 * CM

    # ── Armscye back ─────────────────────────────────────────────────────────
    armscye_back_aux_offset: float = 1.5 * CM
    armscye_back_offset: float = 1.0 * CM
    armscye_back_cp_x: float = 1.0 * CM
    armscye_back_cp_y: float = 1.0 * CM

    # ── Side seam ────────────────────────────────────────────────────────────
    side_hip_tangent: float = 15.0 * CM
    waist_offset: float = 1.0 * CM

    @classmethod
    def _make_waisted_dart(cls) -> BlockConfig:
        return cls(
            straight_center_back=False,
            has_shoulder_dart=True,
            neckline_ease_y=1.5 * CM,
            neckline_ease_x=0.0,
            armscye_front_offset=2.0 * CM,
        )

    @classmethod
    def _make_casual(cls) -> BlockConfig:
        return cls(
            straight_center_back=True,
            has_shoulder_dart=False,
            has_waist_dart=False,
            neckline_ease_y=2.0 * CM,
            neckline_ease_x=0.5 * CM,
            armscye_front_offset=0.0,
            armscye_front_cp_x=-6.0 * CM,
            armscye_front_cp_y=-3.0 * CM,
        )


# Presets — frozen dataclass instances assigned after class body.
BlockConfig.WAISTED_DART: BlockConfig  # type: ignore[attr-defined,misc]  # noqa: B032
BlockConfig.CASUAL: BlockConfig  # type: ignore[attr-defined,misc]  # noqa: B032
BlockConfig.WAISTED_DART = BlockConfig._make_waisted_dart()  # type: ignore[attr-defined]
BlockConfig.CASUAL = BlockConfig._make_casual()  # type: ignore[attr-defined]


@dataclass(frozen=True)
class TopBlockBack:
    """The back piece of a sleeveless women's waisted-top block."""

    part: PatternPart
    armscye_lower: CubicBezier
    armscye_upper: CubicBezier
    neckline: CubicBezier
    shoulder: Segment
    side_chest_waist: Segment
    side_waist_hip: CubicBezier
    side_hip_hem: Segment
    waist_dart: Dart | None
    shoulder_dart: Dart | None
    armscye_control: Point
    waist_indent: Point
    hip_outset: Point


@dataclass(frozen=True)
class TopBlockFront:
    """The front piece of a sleeveless women's waisted-top block."""

    part: PatternPart
    armscye: CubicBezier
    neckline: CubicBezier
    shoulder_armscye: Segment
    shoulder_neckline: Segment | None
    side_chest_waist: Segment
    side_waist_hip: CubicBezier
    side_hip_hem: Segment
    waist_dart: Dart | None
    shoulder_dart: Dart | None
    armscye_control: Point
    waist_indent: Point
    hip_outset: Point
    bust_point: Point


@dataclass(frozen=True)
class TopBlock:
    """Both pieces of the sleeveless women's waisted-top block.

    Build via :meth:`TopBlock.from_measurements`; then add ``.back``
    and ``.front`` to your pattern.
    """

    back: TopBlockBack
    front: TopBlockFront

    @classmethod
    def from_measurements(
        cls,
        meas: BlouseMeasurements,
        config: GarmentConfig,
        grid: TopGrid,
        block_config: BlockConfig,
        fit_class: FitClass | None = None,
        adjustments: PersonalAdjustments | None = None,
        layout: PatternConfig | None = None,
        back_name: str = "Block Back",
        front_name: str = "Block Front",
    ) -> TopBlock:
        """Build and return a :class:`TopBlock` from measurements."""
        adj = adjustments or PersonalAdjustments()
        layout = layout if layout is not None else PatternConfig()
        seam_allowance = config.seam_allowance

        if fit_class is None:
            from .fitclass import FitClass as _FitClass

            fit_class = _FitClass(pk=4)

        # ── 1. Build geometry for each piece independently ───────────────────
        back_geom = _build_back_geometry(
            grid,
            meas,
            layout.anchor,
            adj.hip_offset,
            adj.shoulder_drop,
            config.shoulder_gather,
            block_config,
        )
        front_geom = _build_front_geometry(grid, meas, back_geom, config.armscye_fit, block_config)

        # ── 2. Compute waist / hip distribution ──────────────────────────────
        wd = calculate_waist_distribution(
            meas,
            pt_waist_cf=intersect(grid.center_front, grid.waist)[0],
            pt_waist_sf=intersect(grid.side_front, grid.waist)[0],
            pt_waist_sb=intersect(grid.side_back, grid.waist)[0],
            pt_waist_cb=back_geom.waist_center_back_adj,
            side_seam_intake_max=config.side_seam_intake_max,
        )
        hd = calculate_hip_distribution(
            meas,
            pt_hip_cf=intersect(grid.center_front, grid.hip)[0],
            pt_hip_sf=intersect(grid.side_front, grid.hip)[0],
            pt_hip_sb=intersect(grid.side_back, grid.hip)[0],
            pt_hip_cb=back_geom.hip_center_back_adj,
        )

        # ── 3. Build shared side-seam geometry ───────────────────────────────
        sides = _build_side_seams(grid, meas, config, back_geom, front_geom, wd, hd, block_config)

        # ── 4. Assemble pieces and extract darts ─────────────────────────────
        block_back = PatternPart(name=back_name)
        block_front = PatternPart(name=front_name)

        block_back.append(
            back_geom.armscye_back_lower.set_name("Armscye Back Lower"),
            style=STYLE_STITCH,
            is_outline=True,
            role="armscye",
        )
        armscye_back_elem = block_back.append(
            back_geom.armscye_back_upper.set_name("Armscye Back Upper"),
            style=STYLE_STITCH,
            is_outline=True,
            role="armscye",
        )
        darts, shoulder_dart_back = _build_darts(
            grid, meas, back_geom, front_geom, armscye_back_elem, wd, config, block_config
        )

        _assemble_back_part(
            block_back, back_geom, sides, darts, shoulder_dart_back, seam_allowance, grid
        )
        _assemble_front_part(block_front, front_geom, sides, darts, grid, seam_allowance)

        # ── 5. Pack into public dataclasses and return ────────────────────────
        back = TopBlockBack(
            part=block_back,
            armscye_lower=back_geom.armscye_back_lower,
            armscye_upper=back_geom.armscye_back_upper,
            neckline=back_geom.neckline_back,
            shoulder=back_geom.shoulder_back,
            side_chest_waist=sides.side_chest_waist_back,
            side_waist_hip=sides.side_waist_hip_back,
            side_hip_hem=sides.side_hip_hem_back,
            waist_dart=darts.waist_dart_back,
            shoulder_dart=shoulder_dart_back,
            armscye_control=back_geom.armscye_control,
            waist_indent=sides.waist_indent_back,
            hip_outset=sides.hip_side_back,
        )
        front = TopBlockFront(
            part=block_front,
            armscye=front_geom.armscye_front_lower,
            neckline=front_geom.neckline_front,
            shoulder_armscye=front_geom.shoulder_armscye,
            shoulder_neckline=front_geom.shoulder_neckline,
            side_chest_waist=sides.side_chest_waist_front,
            side_waist_hip=sides.side_waist_hip_front,
            side_hip_hem=sides.side_hip_hem_front,
            waist_dart=darts.waist_dart_front,
            shoulder_dart=darts.shoulder_dart_front,
            armscye_control=front_geom.armscye_control,
            waist_indent=sides.waist_indent_front,
            hip_outset=sides.hip_side_front,
            bust_point=front_geom.bust_point,
        )
        return cls(back=back, front=front)
