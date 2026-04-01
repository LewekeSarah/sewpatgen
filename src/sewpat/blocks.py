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
from typing import TYPE_CHECKING, ClassVar

from ._blocks_assembly import _assemble_back_part, _assemble_front_part
from ._blocks_geometry import (
    _build_back_geometry,
    _build_darts,
    _build_front_geometry,
    _build_side_seams,
)
from .geometry import CubicBezier, Dart, Point, Segment, fit_cubic_bezier, intersect
from .grids import TopGrid, WideSleeveGrid
from .measurements import (
    BlouseMeasurements,
    GarmentConfig,
    WaistDistribution,
    calculate_hip_distribution,
    calculate_waist_distribution,
)
from .pattern import PatternConfig, PatternPart
from .person import PersonalAdjustments
from .style import STYLE_HEM, STYLE_STITCH
from .units import CM

if TYPE_CHECKING:
    from .fitclass import FitClass
    from .sleeve import SleeveArmhole, SleeveConfig


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

    # ── Presets (class-level, not dataclass fields) ───────────────────────────
    WAISTED_DART: ClassVar[BlockConfig]
    CASUAL: ClassVar[BlockConfig]

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
        """Return the waisted-dart preset with kinked CB and shoulder/waist darts."""
        return cls(
            straight_center_back=False,
            has_shoulder_dart=True,
            neckline_ease_y=1.5 * CM,
            neckline_ease_x=0.0,
            armscye_front_offset=2.0 * CM,
        )

    @classmethod
    def _make_casual(cls) -> BlockConfig:
        """Return the casual preset with straight CB and no darts."""
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
BlockConfig.WAISTED_DART = BlockConfig._make_waisted_dart()
BlockConfig.CASUAL = BlockConfig._make_casual()


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

    Attributes:
        back:               The back pattern piece with all dart/seam geometry.
        front:              The front pattern piece with all dart/seam geometry.
        waist_distribution: Result of the waist excess calculation — exposes
            ``side_seam_intake``, ``front_dart_width``, ``back_dart_width``,
            ``total_waist_width`` etc. for use in downstream width checks.
    """

    back: TopBlockBack
    front: TopBlockFront
    waist_distribution: WaistDistribution

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
        return cls(back=back, front=front, waist_distribution=wd)


# ---------------------------------------------------------------------------
# WideSleeveBlock helpers
# ---------------------------------------------------------------------------


def _cap_ref_points(
    corner: Point,
    crown: Point,
) -> tuple[Point, Point, Point]:
    """Return three reference points along the straight cap slope.

    The points are placed at parameter values ``t = 0.25``, ``0.50``, ``0.75``
    on the :class:`Segment` from *corner* (cap-line end) to *crown* (apex).
    They serve as the *ref* argument to :func:`fit_cubic_bezier` so that the
    fitted Bézier stays close to the straight construction line.

    Args:
        corner: Start of the cap slope (cap-line end point).
        crown:  End of the cap slope (apex / crown point).

    Returns:
        A 3-tuple of :class:`Point` at 25 %, 50 %, 75 % along the slope.
    """
    slope = Segment(corner, crown)
    return (slope.point_at_t(0.25), slope.point_at_t(0.50), slope.point_at_t(0.75))


def _fit_cap_bezier(
    corner: Point,
    crown: Point,
    ref: tuple[Point, Point, Point],
) -> CubicBezier:
    """Fit a sleeve-cap Bézier from *corner* to *crown* through *ref*.

    Thin wrapper around :func:`fit_cubic_bezier` using the default
    ``t_params = (0.25, 0.50, 0.75)``.  The curve arrives at *crown* with a
    horizontal tangent (``p2.y = crown.y``), matching the flat-tangent
    constraint at the sleeve cap apex.

    Args:
        corner: Start point (cap-line corner, ``p0``).
        crown:  End point (cap apex, ``p3``).
        ref:    Three reference points the curve passes near.

    Returns:
        A :class:`CubicBezier` from *corner* to *crown*.
    """
    return fit_cubic_bezier(corner, crown, ref)


# ---------------------------------------------------------------------------
# WideSleeveBlock
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WideSleeveBlock:
    """Wide sleeve block — construction grid plus the drafted outline.

    The outline is a closed pentagon:

    * Two **cap slopes** (left and right): straight lines from the sleeve cap
      crown (the topmost point, above the cap line) down to the left / right
      ends of the cap line.  Together they form the triangular cap above the
      rectangle body.
    * Two **side seams** (left and right): vertical lines from the cap-line
      corners down to the hem fold line.
    * One **hem** edge: horizontal line at the hem fold / allowance start
      (= ``grid.hem_line``).

    A separate **sleeve length line** (``STYLE_HEM``) marks the actual cutting
    edge 1 cm below the hem fold line.  A **grainline** runs vertically along
    the centre fold.

    Build via :meth:`from_armhole`.

    Attributes:
        part: The :class:`~sewpat.pattern.PatternPart` with the outlined sleeve shape.
        grid: The :class:`~sewpat.grids.WideSleeveGrid` construction grid.
        cap_crown: Apex of the sleeve cap (top-centre point above the cap line).
        cap_left: Left end of the cap line (intersection of left sleeve / cap line).
        cap_right: Right end of the cap line.
        hem_left: Bottom-left corner of the rectangle body (left sleeve / hem line).
        hem_right: Bottom-right corner.
        cap_left_slope: Segment from ``cap_crown`` down to ``cap_left``.
        left_side: Segment from ``cap_left`` down to ``hem_left``.
        hem: Segment from ``hem_left`` across to ``hem_right`` (fold line).
        right_side: Segment from ``hem_right`` up to ``cap_right``.
        cap_right_slope: Segment from ``cap_right`` up to ``cap_crown``.
    """

    part: PatternPart
    grid: WideSleeveGrid

    # ── Key points ────────────────────────────────────────────────────────────
    cap_crown: Point  # apex of the sleeve cap
    cap_left: Point  # left_sleeve ∩ cap_line
    cap_right: Point  # right_sleeve ∩ cap_line
    hem_left: Point  # left_sleeve ∩ hem_line
    hem_right: Point  # right_sleeve ∩ hem_line

    # ── Auxiliary construction lines (straight triangle legs) ─────────────────
    cap_left_slope: Segment  # crown → cap_left  (construction reference)
    cap_right_slope: Segment  # cap_right → crown  (construction reference)

    # ── Stitch-line Bézier curves for the sleeve cap ──────────────────────────
    cap_left_curve: CubicBezier  # cap_left → cap_crown  (S-curve, stitching)
    cap_right_curve: CubicBezier  # cap_right → cap_crown  (S-curve, stitching)

    # ── Rectangle body outline ────────────────────────────────────────────────
    left_side: Segment  # cap_left → hem_left  (left side seam)
    hem: Segment  # hem_left → hem_right  (hem fold edge)
    right_side: Segment  # hem_right → cap_right  (right side seam)

    @classmethod
    def from_armhole(
        cls,
        armhole: SleeveArmhole,
        sleeve_config: SleeveConfig,
        layout: PatternConfig | None = None,
        part_name: str = "Wide Sleeve",
    ) -> WideSleeveBlock:
        """Build the wide sleeve block from armhole geometry.

        Internally calls :meth:`~sewpat.grids.WideSleeveGrid.from_armhole`
        and then derives all key points and outline segments.

        Args:
            armhole:      Armhole geometry from a finished bodice block.
            sleeve_config: Garment config — ``sleeve_length``, ``cap_offset``,
                           ``ease`` (see :class:`~sewpat.sleeve.SleeveConfig`).
            layout:       Pattern layout configuration (anchor position).
            part_name:    Name of the produced :class:`~sewpat.pattern.PatternPart`.

        Returns:
            :class:`WideSleeveBlock` with all geometry and the pattern part assembled.
        """
        grid = WideSleeveGrid.from_armhole(armhole, sleeve_config, layout=layout)

        # ── Key intersection points ───────────────────────────────────────────
        cap_left = intersect(grid.left_sleeve, grid.cap_line)[0]
        cap_right = intersect(grid.right_sleeve, grid.cap_line)[0]
        hem_left = intersect(grid.left_sleeve, grid.hem_line)[0]
        hem_right = intersect(grid.right_sleeve, grid.hem_line)[0]

        # Crown (tip): centre x, anchored above the cap line by cap_height
        crown_y = grid.cap_line.p1.y - grid.cap_height
        cap_crown = Point(grid.center_sleeve.p1.x, crown_y, "Cap Crown")

        # ── Auxiliary construction lines (straight triangle legs) ─────────────
        seg_cap_left = Segment(cap_crown, cap_left, "Cap Left Slope")
        seg_cap_right = Segment(cap_right, cap_crown, "Cap Right Slope")

        # ── Precision points on the cap-left slope ───────────────────────────
        # Indexed along seg_cap_left (cap_crown → cap_left, t = 0..1).
        # The reversed t-values (0.75, 0.50, 0.25) align with the Bézier's
        # t_params (0.25, 0.50, 0.75), because the Bézier travels in the
        # opposite direction (cap_left → cap_crown).
        _CAP_LEFT_NOTCH_PARAMS: list[tuple[float, float]] = [
            (0.75, -0.8 * CM),
            (0.50, 0.5 * CM),
            (0.25, 1.5 * CM),
        ]
        cap_left_notch_pts = [
            seg_cap_left.point_perpendicular(offset, t=t) for t, offset in _CAP_LEFT_NOTCH_PARAMS
        ]

        # ── Sleeve cap stitch-line Béziers ────────────────────────────────────
        # Each curve runs from the cap-line corner to the crown with a
        # horizontal tangent at the crown (p2.y = crown_y).
        # The left cap Bézier is fitted directly to the precision points so the
        # curve passes through them; cap_left_notch_pts is already ordered for
        # t_params = (0.25, 0.50, 0.75) of the cap_left → cap_crown direction.
        ref_left: tuple[Point, Point, Point] = (
            cap_left_notch_pts[0],
            cap_left_notch_pts[1],
            cap_left_notch_pts[2],
        )
        cap_left_curve = _fit_cap_bezier(cap_left, cap_crown, ref_left).set_name("Cap Left Curve")
        ref_right = _cap_ref_points(cap_right, cap_crown)
        cap_right_curve = _fit_cap_bezier(cap_right, cap_crown, ref_right).set_name(
            "Cap Right Curve"
        )

        # ── Rectangle body segments ───────────────────────────────────────────
        seg_left_side = Segment(cap_left, hem_left, "Left Side")
        seg_hem = Segment(hem_left, hem_right, "Hem")
        seg_right_side = Segment(hem_right, cap_right, "Right Side")

        # ── Cut line: sleeve length line 1 cm below hem (STYLE_HEM) ──────────
        cut_left = intersect(grid.left_sleeve, grid.sleeve_length_line)[0]
        cut_right = intersect(grid.right_sleeve, grid.sleeve_length_line)[0]
        cut_seg = Segment(cut_left, cut_right, "Sleeve Length")

        # ── Assemble part ─────────────────────────────────────────────────────
        part = PatternPart(name=part_name)

        # Straight triangle legs — construction reference, not the stitch line
        part.add_construction_line(seg_cap_left)
        part.add_construction_line(seg_cap_right)

        # Sleeve cap Bézier stitch curves
        part.append(cap_left_curve, style=STYLE_STITCH, is_outline=True, role="cap")
        part.append(cap_right_curve, style=STYLE_STITCH, is_outline=True, role="cap")

        # Notches on the cap-left slope (points computed above with the Bézier ref)
        part.add_precision_points(*cap_left_notch_pts)

        # Rectangle body
        part.append(seg_left_side, style=STYLE_STITCH, is_outline=True, role="side")
        part.append(seg_hem, style=STYLE_STITCH, is_outline=True, role="hem")
        part.append(seg_right_side, style=STYLE_STITCH, is_outline=True, role="side")
        part.append(cut_seg, style=STYLE_HEM)

        # Grainline and info box
        part.add_grainline(
            Point(grid.center_sleeve.p1.x, cap_left.y + 2.0 * CM),
            Point(grid.center_sleeve.p1.x, hem_left.y - 2.0 * CM),
        )
        part.add_info_box(
            notes=[
                f"Ärmelbreite / sleeve width: {grid.sleeve_width / 10:.1f} cm",
                f"Ärmelkopfhöhe / cap height: {grid.cap_height / 10:.1f} cm",
            ]
        )

        return cls(
            part=part,
            grid=grid,
            cap_crown=cap_crown,
            cap_left=cap_left,
            cap_right=cap_right,
            hem_left=hem_left,
            hem_right=hem_right,
            cap_left_slope=seg_cap_left,
            cap_right_slope=seg_cap_right,
            cap_left_curve=cap_left_curve,
            cap_right_curve=cap_right_curve,
            left_side=seg_left_side,
            hem=seg_hem,
            right_side=seg_right_side,
        )
