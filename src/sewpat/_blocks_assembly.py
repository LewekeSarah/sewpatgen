"""PatternPart assembly helpers for :mod:`sewpat.blocks`.

All names here are private (prefixed ``_``).  External code should only ever
import from :mod:`sewpat.blocks`.
"""

from typing import TYPE_CHECKING

from ._blocks_geometry import (
    _BackGeometry,
    _Darts,
    _FrontGeometry,
    _SideSeams,
)
from ._wide_sleeve_geometry import (
    _CuffGeometry,
    _WideSleeveGeometry,
)
from .geometry import Circle, Dart, Point, Segment, intersect, seam_length
from .grids import TopGrid, WideSleeveGrid
from .pattern import PatternPart
from .pattern._notches import RoleMap
from .sleeve import CuffBlockConfig, WideSleeveBlockConfig
from .style import (
    STYLE_BUTTON,
    STYLE_BUTTONHOLE,
    STYLE_CENTER_LINE,
    STYLE_DEBUG_RED,
    STYLE_FOLD,
    STYLE_HEM,
    STYLE_SLIT,
    STYLE_STITCH,
    STYLE_STITCH_BEVEL,
)
from .units import CM

if TYPE_CHECKING:
    from .sleeve import SleeveConfig

#: Notch rules for the **back** pattern piece of a top/blouse block.
TOP_BLOCK_BACK_ROLE_MAP: RoleMap = {
    "side": ["Hip"],
    "center_back": ["Chest", "Waist", "Hip"],
}

TOP_BLOCK_FRONT_ROLE_MAP: RoleMap = {
    "side": ["Hip"],
    "center_front": ["Chest", "Waist", "Hip"],
}


def _assemble_back_part(
    part: PatternPart,
    back: _BackGeometry,
    sides: _SideSeams,
    darts: _Darts,
    shoulder_dart_back: Dart | None,
    seam_allowance: float,
    grid: TopGrid,
) -> None:
    """Add all elements to the back PatternPart in drawing order.

    Note: ``back.armscye_back_lower`` and ``back.armscye_back_upper`` are **not**
    appended here — they were already appended in :meth:`TopBlock.from_measurements`
    before :func:`_build_darts` is called, so that :class:`~sewpat.geometry.Dart`
    can reference the live ``PatternElement`` for the in-place edge split.
    Appending them a second time would corrupt the outline polygon.
    """
    for seg in back.center_back_segments:
        part.append(seg, style=STYLE_STITCH, is_outline=True, role="center_back")
    part.append(back.neckline_back, style=STYLE_STITCH_BEVEL, is_outline=True, role="neckline")
    part.add_construction_line(back.shoulder_back_orig, name="Shoulder Back Orig")
    part.add_construction_line(back.shoulder_blade)
    part.append(
        back.shoulder_back.set_name("Shoulder Back"),
        style=STYLE_STITCH,
        is_outline=True,
        role="shoulder",
    )
    if shoulder_dart_back is not None:
        part.add_dart(shoulder_dart_back)
    part.append(sides.side_chest_waist_back, style=STYLE_STITCH, is_outline=True, role="side")
    if darts.waist_dart_back is not None:
        part.add_dart(darts.waist_dart_back)
    part.add_construction_line(sides.waist_offset)
    part.append(sides.side_waist_hip_back, is_outline=True, style=STYLE_STITCH, role="side")
    part.append(sides.side_hip_hem_back, style=STYLE_STITCH, is_outline=True, role="side")
    part.append(sides.hem_side_to_center_back, style=STYLE_HEM, is_outline=True)

    part.add_construction_line(
        Point(back.armscye_control.x, back.armscye_control.y, name="Armscye Control Back"),
    )
    if shoulder_dart_back is not None:
        part.add_construction_line(
            Point(
                back.shoulder_dart_notch.x,
                back.shoulder_dart_notch.y,
                name="Shoulder Dart Notch Back",
            ),
        )

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)
    part.add_notches(back.armscye_control, seam_edge=back.armscye_back_lower)
    part.add_grid_notches(grid.part, is_back=True, role_map=TOP_BLOCK_BACK_ROLE_MAP)

    # ── Grainline — vertical, centred between CB and side seam ────────────────
    grain_x = back.anchor.x + (back.side_back_chest.x - back.anchor.x) / 2.0
    part.add_grainline(
        Point(grain_x, back.anchor.y + 1.0 * CM),
        Point(grain_x, back.hem_center_back_outline.y - 1.0 * CM),
    )

    # ── Info box ──────────────────────────────────────────────────────────────
    notes_back: list[str] = ["Zuschnitt 2× / Cut 2×"]
    if seam_allowance > 0:
        notes_back.append(f"Nahtzugabe / S.A.: {seam_allowance / 10:.1f} cm")
    part.add_info_box(notes=notes_back)


def _assemble_front_part(
    part: PatternPart,
    front: _FrontGeometry,
    sides: _SideSeams,
    darts: _Darts,
    grid: TopGrid,
    seam_allowance: float,
) -> None:
    """Add all elements to the front PatternPart in drawing order."""
    hem_cf = intersect(grid.center_front, grid.hem)[0]
    part.append(
        Segment(
            front.neckline_front_start,
            hem_cf,
            name="Center Front",
        ),
        style=STYLE_CENTER_LINE,
        is_outline=True,
        role="center_front",
    )
    part.append(
        front.neckline_front.set_name("Neckline Front"),
        style=STYLE_STITCH,
        is_outline=True,
        role="neckline",
    )
    if front.neckline_front_stub is not None:
        part.add_construction_line(front.neckline_front_stub, name="Neckline Front Stub")
    if front.shoulder_front_aux_orig is not None:
        part.add_construction_line(front.shoulder_front_aux_orig, name="Shoulder Front Orig")
    if front.shoulder_front_dart_orig is not None:
        part.add_construction_line(front.shoulder_front_dart_orig, name="Shoulder Front Dart Orig")
    part.append(
        front.shoulder_armscye.set_name("Shoulder Front"),
        style=STYLE_STITCH,
        is_outline=True,
        role="shoulder",
    )
    if front.shoulder_neckline is not None:
        part.append(
            front.shoulder_neckline.set_name("Shoulder Front Dart"),
            style=STYLE_STITCH,
            is_outline=True,
            role="shoulder",
        )
        if darts.shoulder_dart_front is not None:
            part.add_dart(darts.shoulder_dart_front)
    if front.armscye_front_upper is not None:
        part.add_construction_line(front.armscye_front_upper, name="Armscye Front Upper")
    part.append(
        front.armscye_front_lower.set_name("Armscye Front"),
        style=STYLE_STITCH,
        is_outline=True,
        role="armscye",
    )
    part.append(sides.side_chest_waist_front, style=STYLE_STITCH, is_outline=True, role="side")
    if darts.waist_dart_front is not None:
        part.add_dart(darts.waist_dart_front)
    part.append(sides.side_waist_hip_front, is_outline=True, style=STYLE_STITCH, role="side")
    part.append(sides.side_hip_hem_front, style=STYLE_STITCH, is_outline=True, role="side")
    part.append(sides.hem_side_to_center_front, style=STYLE_HEM, is_outline=True, role="hem")

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)
    part.add_notches(front.armscye_control, seam_edge=front.armscye_front_lower)
    part.add_grid_notches(grid.part, role_map=TOP_BLOCK_FRONT_ROLE_MAP)

    # ── Grainline — vertical, centred between CF and side seam ────────────────
    grain_x = (
        front.neckline_front_start.x
        + (front.side_front_chest.x - front.neckline_front_start.x) / 2.0
    )
    part.add_grainline(
        Point(grain_x, front.shoulder_armscye.p1.y + 1.0 * CM),
        Point(grain_x, hem_cf.y - 1.0 * CM),
    )

    # ── Info box ──────────────────────────────────────────────────────────────
    notes_front: list[str] = ["Zuschnitt 2× / Cut 2×"]
    if seam_allowance > 0:
        notes_front.append(f"Nahtzugabe / S.A.: {seam_allowance / 10:.1f} cm")
    part.add_info_box(notes=notes_front)


# ---------------------------------------------------------------------------
# Wide-sleeve assembly
# ---------------------------------------------------------------------------


def _assemble_wide_sleeve_part(
    part: PatternPart,
    geom: _WideSleeveGeometry,
    grid: WideSleeveGrid,
    sleeve_config: SleeveConfig,
    seam_allowance: float = 0.0,
    block_config: WideSleeveBlockConfig | None = None,
) -> None:
    """Add all wide sleeve elements to *part* in drawing order.

    Args:
        part:            Empty :class:`~sewpat.pattern.PatternPart` to populate.
        geom:            Pre-computed sleeve geometry (pure data, no side effects).
        grid:            Wide sleeve construction grid (sleeve_width, cap_height, etc.).
        sleeve_config:   Garment config — used only for the info-box note text
                         (slit height, pleat count/depth).
        seam_allowance:  Nahtzugabe — seam allowance width (mm).  ``0`` → no SA layer.
        block_config:    Construction constants — grainline margins.  Defaults to
                         :attr:`~sewpat.sleeve.WideSleeveBlockConfig.WIDE`.
    """
    bc = block_config if block_config is not None else WideSleeveBlockConfig.WIDE
    # ── Auxiliary construction lines (straight triangle legs) ────────────────
    part.add_construction_line(geom.cap_left_slope)
    part.add_construction_line(geom.cap_right_slope)

    # ── Sleeve cap Bézier stitch curves ──────────────────────────────────────
    part.append(geom.cap_left_curve, style=STYLE_STITCH, is_outline=True, role="cap")
    part.append(geom.cap_right_curve, style=STYLE_STITCH, is_outline=True, role="cap")

    # ── Cap notch marks ───────────────────────────────────────────────────────
    # Front armscye notch — single notch on left (front) cap curve
    if geom.front_armscye_notch_on_cap is not None:
        part.add_notches(geom.front_armscye_notch_on_cap, seam_edge=geom.cap_left_curve)
    # Shoulder alignment notch — single notch on left cap curve
    if geom.shoulder_on_cap is not None:
        part.add_notches(geom.shoulder_on_cap, seam_edge=geom.cap_left_curve)
    # Back armscye notch — double notch on right (back) cap curve
    if geom.back_armscye_notch_on_cap is not None:
        part.add_notches(
            geom.back_armscye_notch_on_cap, seam_edge=geom.cap_right_curve, is_back=True
        )

    # ── Construction reference points ────────────────────────────────────────
    for pt in (*geom.cap_left_notch_pts, *geom.cap_right_notch_pts, *geom.hem_ref_pts):
        part.append(pt, style=STYLE_DEBUG_RED, is_construction=True)

    # ── Rectangle body ────────────────────────────────────────────────────────
    part.append(geom.left_side, style=STYLE_STITCH, is_outline=True, role="side")
    part.add_construction_line(geom.hem)
    part.append(geom.hem_left_curve, style=STYLE_STITCH, is_outline=True, role="hem")
    part.append(geom.hem_right_curve, style=STYLE_STITCH, is_outline=True, role="hem")
    if geom.slit is not None:
        part.append(geom.slit, style=STYLE_SLIT)
    for pleat in geom.pleats:
        pleat.apply_to(part)
    part.append(geom.right_side, style=STYLE_STITCH, is_outline=True, role="side")
    part.add_construction_line(geom.cut_seg)

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)

    # ── Grainline — vertical along the centre fold ────────────────────────────
    part.add_grainline(
        Point(grid.center_sleeve.p1.x, geom.cap_left.y + bc.grainline_cap_margin),
        Point(grid.center_sleeve.p1.x, geom.hem_left.y - bc.grainline_hem_margin),
    )

    # ── Info box ──────────────────────────────────────────────────────────────
    sleeve_hem_width = grid.construction_measures.sleeve_hem_width
    cap_stitch_length = seam_length([geom.cap_left_curve, geom.cap_right_curve])
    armscye_circumference = grid.construction_measures.armscye_circumference
    sleeve_ease = cap_stitch_length - armscye_circumference
    notes = [
        f"Ärmelbreite / sleeve width: {grid.sleeve_width / 10:.1f} cm",
        f"Armkugelhöhe / cap height: {grid.cap_height / 10:.1f} cm",
        f"Armkugellänge / cap seam: {cap_stitch_length / 10:.1f} cm",
        f"Armlochumfang / armscye seam: {armscye_circumference / 10:.1f} cm",
        f"Einhalteweite / sleeve ease: {sleeve_ease / 10:+.1f} cm",
    ]
    if sleeve_hem_width is not None:
        notes.append(f"Bündchenweite / cuff width: {sleeve_hem_width / 10:.1f} cm")
    if geom.slit is not None and sleeve_config.slit_height is not None:
        notes.append(f"Schlitzhöhe / slit height: {sleeve_config.slit_height / 10:.1f} cm")
    if geom.pleats and sleeve_config.pleat_config is not None:
        _pc = sleeve_config.pleat_config
        notes.append(f"Falten / pleats: {_pc.num_pleats} × {_pc.depth / 10:.1f} cm")
    if seam_allowance > 0:
        notes.append(f"Nahtzugabe / S.A.: {seam_allowance / 10:.1f} cm")
    # Shift the info box left of the centre grainline to avoid overlap.
    part.add_info_box(notes=notes, offset=(-grid.sleeve_width / 2.0, 3.0 * CM))


# ---------------------------------------------------------------------------
# Cuff assembly
# ---------------------------------------------------------------------------


def _assemble_cuff_part(
    part: PatternPart,
    geom: _CuffGeometry,
    seam_allowance: float = 0.0,
    cuff_block_config: CuffBlockConfig | None = None,
) -> None:
    """Add all cuff elements to *part* in drawing order.

    Args:
        part:              Empty :class:`~sewpat.pattern.PatternPart` to populate.
        geom:              Pre-computed cuff geometry (pure data, no side effects).
        seam_allowance:    Nahtzugabe — seam allowance width (mm).  ``0`` → no SA layer.
        cuff_block_config: Construction constants — grainline placement.  Defaults to
                           :attr:`~sewpat.sleeve.CuffBlockConfig.STANDARD`.
    """
    cbc = cuff_block_config if cuff_block_config is not None else CuffBlockConfig.STANDARD
    ay = geom.top_left.y
    total_height = 2.0 * geom.cuff_height

    # ── Outer rectangle — all four edges are cutting lines ────────────────────
    part.append(
        Segment(geom.top_left, geom.top_right, "Cuff Opening"),
        style=STYLE_STITCH,
        is_outline=True,
    )
    part.append(
        Segment(geom.top_right, geom.bottom_right, "Cuff Right"),
        style=STYLE_STITCH,
        is_outline=True,
    )
    part.append(
        Segment(geom.bottom_right, geom.bottom_left, "Cuff Fold Edge"),
        style=STYLE_STITCH,
        is_outline=True,
    )
    part.append(
        Segment(geom.bottom_left, geom.top_left, "Cuff Left"),
        style=STYLE_STITCH,
        is_outline=True,
    )

    # ── Fold line — not a sewing line, no SA ──────────────────────────────────
    part.append(Segment(geom.fold_left, geom.fold_right, "Fold Line"), style=STYLE_FOLD)

    # ── Division lines between sections ───────────────────────────────────────
    if geom.underlap > 0.0:
        part.append(
            Segment(
                Point(geom.main_left_x, ay),
                Point(geom.main_left_x, ay + total_height),
                "Underlap Boundary",
            ),
            style=STYLE_CENTER_LINE,
        )
    if geom.overlap > 0.0:
        part.append(
            Segment(
                Point(geom.main_right_x, ay),
                Point(geom.main_right_x, ay + total_height),
                "Overlap Boundary",
            ),
            style=STYLE_CENTER_LINE,
        )

    # ── Grainline — placed at fraction of main body width to clear fold-line label ──
    grain_x = geom.main_left_x + geom.cuff_length * cbc.grainline_fraction
    part.add_grainline(
        Point(grain_x, ay + cbc.grainline_margin),
        Point(grain_x, ay + total_height - cbc.grainline_margin),
        name="Cuff Grain",
    )

    if seam_allowance > 0:
        part.add_seam_allowance(seam_allowance)

    # ── Buttons and buttonholes ────────────────────────────────────────────────
    for row in geom.button_rows:
        part.append(
            Circle(row.button, row.button_radius, "Button"),
            style=STYLE_BUTTON,
        )
        if row.button2 is not None:
            part.append(
                Circle(row.button2, row.button_radius, "Button"),
                style=STYLE_BUTTON,
            )
        part.append(
            Segment(row.hole_start, row.hole_end, "Buttonhole"),
            style=STYLE_BUTTONHOLE,
        )

    # ── Info box ──────────────────────────────────────────────────────────────
    notes = [
        f"Bündchenlänge / cuff length: {geom.cuff_length / 10:.1f} cm",
        f"Bündchenbreite / cuff height: {geom.cuff_height / 10:.1f} cm",
    ]
    if geom.underlap > 0.0:
        notes.append(f"Unterschlag / underlap: {geom.underlap / 10:.1f} cm")
    if geom.overlap > 0.0:
        notes.append(f"Überschlag / overlap: {geom.overlap / 10:.1f} cm")
    if seam_allowance > 0:
        notes.append(f"Nahtzugabe / S.A.: {seam_allowance / 10:.1f} cm")
    # Centre the info block inside the lower cuff half (fold → bottom edge).
    part.add_info_box(notes=notes, offset=(0.0, geom.cuff_height / 2.0))
