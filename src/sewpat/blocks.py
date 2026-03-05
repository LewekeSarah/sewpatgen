"""Pre-built garment blocks for common pattern types.

Each block is a pair of frozen dataclasses — one per pattern piece — bundled
in a thin container class that mirrors the :class:`~sewpat.grids.TopGrid`
convention.  Callers never touch fragile string lookups; every key point and
edge is a typed, named attribute with full IDE autocomplete.

Example::

    from sewpat.blocks import TopBlock
    from sewpat.grids import TopGrid

    grid  = TopGrid.from_measurements(meas, model, config)
    block = TopBlock.from_measurements(meas, model, config)

    pattern.add_part(grid.part)
    pattern.add_part(block.back.part)
    pattern.add_part(block.front.part)

    # Extend the sleeve edge with a collar:
    pt_collar = block.back.pt_hÄP.translate(0, -2 * CM)
"""

from dataclasses import dataclass

from .geometry import CubicBezier, Dart, Point, Segment
from .grids import TopGrid
from .measurements import BlouseMeasurements, ModelConfig
from .pattern import PatternConfig, PatternPart
from .style import STYLE_HEM, STYLE_STITCH, StyleOptions
from .geometry import Circle, intersect, Line, Ray
from .units import CM


@dataclass(frozen=True)
class TopBlockBack:
    """The back piece of a sleeveless women's waisted-top block.

    Attributes:
        part: The :class:`~sewpat.pattern.PatternPart` ready to add to a
            :class:`~sewpat.pattern.Pattern`.  It already contains all outline
            segments, darts, and — when *seam_allowance* > 0 — the SA offset.
        sleeve_back: Armscye curve of the back piece (pt11 → shoulder_back.p2).
        shoulder_back: Shoulder seam (parallel-offset construction line).
        side_seam_back_upper: Straight side-seam segment from raised waist
            point to the armscye.
        waist_dart_back: Rhombus waist dart geometry.
        shoulder_dart_back: Triangle shoulder dart cut into the armscye.
        pt_hÄP: Armscye notch reference point on the back sleeve edge.
        pt_waist_sb_raised: Raised waist point at the back side seam
            (after SaEinzug correction).
        pt37: Hip point at the back side seam (after Fehlbetrag correction).
        pt_armscye: Armscye intersection at the back side seam (pt11).
    """

    part: PatternPart
    sleeve_back: CubicBezier
    shoulder_back: Segment
    side_seam_back_upper: Segment
    waist_dart_back: Dart
    shoulder_dart_back: Dart
    pt_hÄP: Point
    pt_waist_sb_raised: Point
    pt37: Point
    pt_armscye: Point


@dataclass(frozen=True)
class TopBlockFront:
    """The front piece of a sleeveless women's waisted-top block.

    Attributes:
        part: The :class:`~sewpat.pattern.PatternPart` ready to add to a
            :class:`~sewpat.pattern.Pattern`.  It already contains all outline
            segments, darts, and — when *seam_allowance* > 0 — the SA offset.
        sleeve_front_lower: Armscye curve of the front piece, lower section
            (shoulder endpoint → pt12).
        shoulder_front_long: Long shoulder seam (from bust-point pivot side).
        shoulder_front_short: Short shoulder seam (dart side, toward neckline).
        side_seam_front_upper: Straight side-seam segment from raised waist
            point to the armscye.
        waist_dart_front: Rhombus waist dart geometry.
        shoulder_dart_front: Triangle shoulder dart (bust-dart rotated to shoulder).
        pt_vÄP: Armscye notch reference point on the front sleeve edge.
        pt_waist_sf_raised: Raised waist point at the front side seam
            (after SaEinzug correction).
        pt37_front: Hip point at the front side seam (after Fehlbetrag correction).
        pt_BrP: Bust point.
        pt_armscye: Armscye intersection at the front side seam (pt12).
    """

    part: PatternPart
    sleeve_front_lower: CubicBezier
    shoulder_front_long: Segment
    shoulder_front_short: Segment
    side_seam_front_upper: Segment
    waist_dart_front: Dart
    shoulder_dart_front: Dart
    pt_vÄP: Point
    pt_waist_sf_raised: Point
    pt37_front: Point
    pt_BrP: Point
    pt_armscye: Point


@dataclass(frozen=True)
class TopBlock:
    """Both pieces of the sleeveless women's waisted-top block.

    Build via :meth:`TopBlock.from_measurements`; then add ``.back.part``
    and ``.front.part`` to your pattern.  All key points and edges on each
    piece are available as typed attributes with full IDE autocomplete.

    Example::

        block = TopBlock.from_measurements(meas, model, config)
        pattern.add_part(block.back.part)
        pattern.add_part(block.front.part)

        # Draw a new sleeve:
        sleeve = CubicBezier(block.back.pt_armscye, ..., block.back.pt_hÄP)

    Attributes:
        back:  :class:`TopBlockBack` — the complete back piece with typed geometry.
        front: :class:`TopBlockFront` — the complete front piece with typed geometry.
    """

    back: TopBlockBack
    front: TopBlockFront

    @classmethod
    def from_measurements(
        cls,
        meas: BlouseMeasurements,
        model: ModelConfig,
        config: PatternConfig | None = None,
        back_name: str = "Block Back",
        front_name: str = "Block Front",
    ) -> "TopBlock":
        """Build and return a :class:`TopBlock` from measurements.

        The two ``PatternPart`` objects inside the returned block already
        contain every outline element, both darts with notches and precision
        marks, and (when ``model.seam_allowance > 0``) the SA offset.
        Add them directly to your pattern::

            pattern.add_part(block.back.part)
            pattern.add_part(block.front.part)

        Args:
            meas: Blouse measurements (ease already included).
            model: Model-level design choices (garment length, hip adjustment,
                seam allowance, …).
            config: Pattern configuration (anchor, inter-piece margin).
                Defaults to a standard :class:`~sewpat.pattern.PatternConfig`.
            back_name: Name for the back :class:`~sewpat.pattern.PatternPart`.
            front_name: Name for the front :class:`~sewpat.pattern.PatternPart`.

        Returns:
            A :class:`TopBlock` with fully constructed ``.back`` and
            ``.front`` pieces.
        """
        from .geometry import Dart, DartType
        from .measurements import WaistDistribution, calculate_waist_distribution, calculate_hip_distribution

        if config is None:
            config = PatternConfig()

        grid = TopGrid.from_measurements(meas=meas, model=model, config=config)

        block_back  = PatternPart(name=back_name)
        block_front = PatternPart(name=front_name)

        # ── Grid intersections ───────────────────────────────────────────────
        pt1  = config.anchor
        pt2  = pt1.translate(0, model.MoL)
        pt4  = pt1.translate(0, meas.RüL)
        pt5  = intersect(grid.center_back, grid.hip)[0]
        pt6  = pt4.translate(model.BeckenAdjustment, 0)
        pt8  = pt5.translate(model.BeckenAdjustment, 0)
        pt9  = pt2.translate(model.BeckenAdjustment, 0)
        pt10 = intersect(grid.sleeve_back,  grid.chest)[0]
        pt11 = intersect(grid.side_back,    grid.chest)[0]
        pt12 = intersect(grid.side_front,   grid.chest)[0]
        pt13 = intersect(grid.sleeve_front, grid.chest)[0]
        pt14 = intersect(grid.center_front, grid.chest)[0]
        pt16 = intersect(grid.sleeve_back,  grid.shoulder_back)[0]
        pt17 = intersect(grid.shoulder_back, grid.neck)[0]
        pt18 = pt16.translate(0, 1.5 * CM)  # TODO don't hard-code

        # ── Shoulder back ────────────────────────────────────────────────────
        pt_sHlP   = pt17.translate(0, -2 * CM)  # TODO don't hard-code
        pt_HP     = Segment(pt18, pt10).point_at_t(0.5).translate(1 * CM, 0)
        shoulder_blade = Line(pt_HP, (1, 0), name="Shoulder Blade")
        pt_hÄP    = Segment(pt18, pt10).point_at_t(0.75).translate(1.5 * CM, 0)
        shoulder_back_orig = Segment.from_direction(pt_sHlP, pt18, length=meas.SuB + 1 * CM)
        shoulder_back      = shoulder_back_orig.offset(-1 * CM)
        pt29 = intersect(grid.dart_back, shoulder_blade)[0]

        # ── Neckline front ───────────────────────────────────────────────────
        pt19 = intersect(grid.bust_point, grid.waist)[0]
        pt20 = intersect(grid.shoulder_front, grid.bust_point)[0]
        pt_BrP = pt20.translate(0, meas.BrT)
        pt21   = intersect(grid.center_front, grid.shoulder_front)[0]
        pt22   = pt21.translate(0, meas.HlB + 1.5 * CM)  # TODO don't hard-code
        pt_sHlP_front = pt21.translate(-meas.HlB, 0)

        # ── Shoulder front with dart ─────────────────────────────────────────
        pt_vÄP = pt13.translate(0, -0.25 * meas.ArD)
        aux_l  = Segment(pt18, pt10).length - 2 * CM
        pt23   = pt13.translate(0, -aux_l)
        pt_SuP = Circle(pt13, aux_l).point_along_from(pt23, -meas.BrU / 20 + 0 * CM)
        pt24   = intersect(Circle(pt_BrP, meas.BrT), Circle(pt_SuP, meas.SuB))[0]
        shoulder_front_aux = Segment(pt24, pt_SuP)
        pt25   = shoulder_front_aux.point_along_from(pt24, Segment(pt_sHlP_front, pt20).length)
        pt26   = pt_BrP.translate(0, -Segment(pt_BrP, pt25).length)
        shoulder_front_long      = Segment(pt_SuP, pt25).offset(1 * CM)
        _shoulder_front_short_raw = Segment(pt26, pt_sHlP_front).offset(1 * CM)

        # Neckline front Bézier — split at shoulder_front_short ray
        neckline_front_full = CubicBezier(
            pt22, pt22,
            pt21.translate(-meas.HlB, meas.HlB),
            pt_sHlP_front,
        )
        _short_ray = Ray(_shoulder_front_short_raw.p1, _shoulder_front_short_raw.unit_direction)
        _neckline_intersections = intersect(neckline_front_full, _short_ray)
        if _neckline_intersections:
            _ix = _neckline_intersections[0]
            shoulder_front_short = Segment(_shoulder_front_short_raw.p1, _ix)
            _neckline_split = neckline_front_full.split_at_points([_ix])
            _nf = _neckline_split[0]
            neckline_front = CubicBezier(_nf.p0, _nf.p1, _nf.p2, _ix)
            neckline_front_stub = _neckline_split[1] if len(_neckline_split) > 1 else None
        else:
            shoulder_front_short = _shoulder_front_short_raw
            neckline_front = neckline_front_full
            neckline_front_stub = None

        # ── Sleeve curves ────────────────────────────────────────────────────
        sleeve_front = CubicBezier(pt_SuP, pt_BrP.translate(-4 * CM, -3 * CM), pt12, pt12)
        _sleeve_split = sleeve_front.split_at_points([shoulder_front_long.p1])
        if len(_sleeve_split) > 1:
            sleeve_front_upper = _sleeve_split[0]
            sleeve_front_lower = _sleeve_split[1]
        else:
            sleeve_front_upper = None
            sleeve_front_lower = sleeve_front

        sleeve_back = CubicBezier(
            pt11,
            pt_hÄP.translate(-0.5 * CM, 3 * CM),
            pt_hÄP.translate(-1.5 * CM, 3 * CM),
            shoulder_back.p2,
        )

        # ── Waist dart distribution ──────────────────────────────────────────
        waist_offset  = grid.waist.offset(-1 * CM).set_name("Waist Offset")
        pt_waist_cf   = intersect(grid.center_front, grid.waist)[0]
        pt_waist_sf   = intersect(grid.side_front,   grid.waist)[0]
        pt_waist_sb   = intersect(grid.side_back,    grid.waist)[0]
        wd: WaistDistribution = calculate_waist_distribution(
            meas,
            pt_waist_cf=pt_waist_cf,
            pt_waist_sf=pt_waist_sf,
            pt_waist_sb=pt_waist_sb,
            pt_waist_cb=pt6,
        )

        # ── Hip distribution ─────────────────────────────────────────────────
        pt_hip_cf = intersect(grid.center_front, grid.hip)[0]
        pt_hip_sf = intersect(grid.side_front,   grid.hip)[0]
        pt_hip_sb = intersect(grid.side_back,    grid.hip)[0]
        pt_hip_cb = pt8
        hd = calculate_hip_distribution(
            meas,
            pt_hip_cf=pt_hip_cf,
            pt_hip_sf=pt_hip_sf,
            pt_hip_sb=pt_hip_sb,
            pt_hip_cb=pt_hip_cb,
        )

        # ── Raised waist + hip side points ───────────────────────────────────
        pt_waist_sb_raised = intersect(grid.side_back,  waist_offset)[0].translate(-wd.SaEinzug, 0)
        pt_waist_sf_raised = intersect(grid.side_front, waist_offset)[0].translate( wd.SaEinzug, 0)

        side_seam_back_upper  = Segment(pt_waist_sb_raised, pt11, name="Side Seam Back Upper")
        side_seam_front_upper = Segment(pt_waist_sf_raised, pt12, name="Side Seam Front Upper")

        side_back_offset  = grid.side_back.offset(  hd.Fehlbetrag)
        side_front_offset = grid.side_front.offset(-hd.Fehlbetrag)
        pt37       = intersect(grid.hip, side_back_offset )[0]
        pt37_front = intersect(grid.hip, side_front_offset)[0]

        side_back_curved = CubicBezier(
            pt_waist_sb_raised,
            intersect(grid.side_back, waist_offset)[0].translate(-hd.Fehlbetrag, 15 * CM),
            pt37, pt37,
            name="Side Hip Curve Back",
        )
        side_front_curved = CubicBezier(
            pt_waist_sf_raised,
            intersect(grid.side_front, waist_offset)[0].translate(hd.Fehlbetrag, 15 * CM),
            pt37_front, pt37_front,
            name="Side Hip Curve Front",
        )

        # ── Darts ────────────────────────────────────────────────────────────
        pt28 = intersect(grid.waist, grid.dart_back)[0]

        waist_dart_back = Dart.from_tip_center_width(
            tip=intersect(grid.dart_back, grid.chest)[0],
            center=pt28,
            width=wd.hAbI,
            dart_type=DartType.RHOMBUS,
            second_tip=pt28.translate(0, 16 * CM),
        ).set_name("Waist Dart Back")

        pt19_waist = intersect(grid.bust_point, grid.waist)[0]
        waist_dart_front = Dart.from_tip_center_width(
            tip=pt_BrP,
            center=pt19_waist,
            width=wd.vAbI,
            dart_type=DartType.RHOMBUS,
            second_tip=pt19_waist.translate(0, 12 * CM),
        ).set_name("Waist Dart Front")

        shoulder_dart_front = Dart.from_tip_and_legs(
            pt_BrP,
            shoulder_front_short.p1,
            shoulder_front_long.p2,
        ).set_name("Shoulder Dart Front")

        # ── Assemble back piece ──────────────────────────────────────────────
        sleeve_back_elem = block_back.append(
            sleeve_back.set_name("Sleeve Back"), style=STYLE_STITCH, is_outline=True,
        )
        shoulder_dart_back = Dart.from_edge_at_legs(
            sleeve_back_elem,
            leg_a=pt_HP,
            leg_b=sleeve_back.point_along_from(pt_HP, 1.5 * CM),
            tip=pt29,
            name="Shoulder Dart Back",
        )
        block_back.append(Segment(pt1, pt6, name="Center Back"),     style=STYLE_STITCH,   is_outline=True)
        block_back.append(Segment(pt6, pt9, name="Center Back Hem"), style=STYLE_STITCH,   is_outline=True)
        block_back.append(
            CubicBezier(pt1, pt1, pt17, shoulder_back.p1, name="Neckline Back"),
            style=StyleOptions(dash_array=[5.0, 2.0], corner_join="bevel"),
            is_outline=True,
        )
        block_back.append(shoulder_back_orig.set_name("Shoulder Back Orig"), is_construction=True)
        block_back.append(shoulder_blade, is_construction=True)
        block_back.append(shoulder_back.set_name("Shoulder Back"), style=STYLE_STITCH, is_outline=True)
        block_back.add_dart(shoulder_dart_back)
        block_back.append(side_seam_back_upper, style=STYLE_STITCH, is_outline=True)
        block_back.add_dart(waist_dart_back)
        block_back.append(waist_offset, is_construction=True)
        block_back.append(side_back_curved, is_outline=True, style=STYLE_STITCH)
        block_back.append(
            Segment(pt37, pt37.translate(0, Segment(pt8, pt9).length)),
            style=STYLE_STITCH, is_outline=True,
        )
        block_back.append(
            Segment(intersect(grid.hem, side_back_offset)[0], pt9),
            style=STYLE_HEM, is_outline=True,
        )
        if model.seam_allowance > 0:
            block_back.add_seam_allowance(model.seam_allowance)
        block_back.add_notches(pt_hÄP, seam_edge=sleeve_back)

        # ── Assemble front piece ─────────────────────────────────────────────
        block_front.append(
            Segment(pt22, intersect(grid.center_front, grid.hem)[0], name="Center Front"),
            style=StyleOptions(dash_array=[5.0, 2.0], corner_join="bevel"),
            is_outline=True,
        )
        block_front.append(neckline_front.set_name("Neckline Front"), style=STYLE_STITCH, is_outline=True)
        if neckline_front_stub is not None:
            block_front.append(neckline_front_stub.set_name("Neckline Front Stub"), is_construction=True)
        block_front.append(Segment(pt_SuP, pt25, name="Shoulder Front Orig"), is_construction=True)
        block_front.append(Segment(pt_sHlP_front, pt26, name="Shoulder Front Dart Orig"), is_construction=True)
        block_front.append(shoulder_front_long.set_name("Shoulder Front"),      style=STYLE_STITCH, is_outline=True)
        block_front.append(shoulder_front_short.set_name("Shoulder Front Dart"), style=STYLE_STITCH, is_outline=True)
        block_front.add_dart(shoulder_dart_front)
        block_front.append(side_seam_front_upper, style=STYLE_STITCH, is_outline=True)
        if sleeve_front_upper is not None:
            block_front.append(sleeve_front_upper.set_name("Sleeve Front Upper"), is_construction=True)
        block_front.append(sleeve_front_lower.set_name("Sleeve Front"), style=STYLE_STITCH, is_outline=True)
        block_front.add_dart(waist_dart_front)
        block_front.append(side_front_curved, is_outline=True, style=STYLE_STITCH)
        block_front.append(
            Segment(pt37_front, pt37_front.translate(0, Segment(pt8, pt9).length)),
            style=STYLE_STITCH, is_outline=True,
        )
        block_front.append(
            Segment(
                intersect(grid.hem, side_front_offset)[0],
                intersect(grid.hem, grid.center_front)[0],
            ),
            style=STYLE_HEM, is_outline=True,
        )
        if model.seam_allowance > 0:
            block_front.add_seam_allowance(model.seam_allowance)
        block_front.add_notches(pt_vÄP, seam_edge=sleeve_front_lower)

        # ── Pack and return ──────────────────────────────────────────────────
        back = TopBlockBack(
            part=block_back,
            sleeve_back=sleeve_back,
            shoulder_back=shoulder_back,
            side_seam_back_upper=side_seam_back_upper,
            waist_dart_back=waist_dart_back,
            shoulder_dart_back=shoulder_dart_back,
            pt_hÄP=pt_hÄP,
            pt_waist_sb_raised=pt_waist_sb_raised,
            pt37=pt37,
            pt_armscye=pt11,
        )
        front = TopBlockFront(
            part=block_front,
            sleeve_front_lower=sleeve_front_lower,
            shoulder_front_long=shoulder_front_long,
            shoulder_front_short=shoulder_front_short,
            side_seam_front_upper=side_seam_front_upper,
            waist_dart_front=waist_dart_front,
            shoulder_dart_front=shoulder_dart_front,
            pt_vÄP=pt_vÄP,
            pt_waist_sf_raised=pt_waist_sf_raised,
            pt37_front=pt37_front,
            pt_BrP=pt_BrP,
            pt_armscye=pt12,
        )
        return cls(back=back, front=front)

