"""PatternPart assembly helpers for :mod:`sewpat.blocks`.

All names here are private (prefixed ``_``).  External code should only ever
import from :mod:`sewpat.blocks`.
"""

from typing import TYPE_CHECKING

from ._blocks_geometry import _BackGeometry, _Darts, _FrontGeometry, _SideSeams, _WideSleeveGeometry
from .geometry import Dart, Point, Segment, intersect
from .grids import TopGrid, WideSleeveGrid
from .pattern import PatternPart
from .pattern._notches import RoleMap
from .style import (
    STYLE_CENTER_LINE,
    STYLE_DEBUG_RED,
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


def _assemble_front_part(
    part: PatternPart,
    front: _FrontGeometry,
    sides: _SideSeams,
    darts: _Darts,
    grid: TopGrid,
    seam_allowance: float,
) -> None:
    """Add all elements to the front PatternPart in drawing order."""
    part.append(
        Segment(
            front.neckline_front_start,
            intersect(grid.center_front, grid.hem)[0],
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


# ---------------------------------------------------------------------------
# Wide-sleeve assembly
# ---------------------------------------------------------------------------


def _assemble_wide_sleeve_part(
    part: PatternPart,
    geom: _WideSleeveGeometry,
    grid: WideSleeveGrid,
    sleeve_config: SleeveConfig,
) -> None:
    """Add all wide sleeve elements to *part* in drawing order.

    Args:
        part:          Empty :class:`~sewpat.pattern.PatternPart` to populate.
        geom:          Pre-computed sleeve geometry (pure data, no side effects).
        grid:          Wide sleeve construction grid (sleeve_width, cap_height, etc.).
        sleeve_config: Garment config — used only for the info-box note text
                       (slit height, pleat count/depth).
    """
    # ── Auxiliary construction lines (straight triangle legs) ────────────────
    part.add_construction_line(geom.cap_left_slope)
    part.add_construction_line(geom.cap_right_slope)

    # ── Sleeve cap Bézier stitch curves ──────────────────────────────────────
    part.append(geom.cap_left_curve, style=STYLE_STITCH, is_outline=True, role="cap")
    part.append(geom.cap_right_curve, style=STYLE_STITCH, is_outline=True, role="cap")

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

    # ── Grainline — vertical along the centre fold ────────────────────────────
    part.add_grainline(
        Point(grid.center_sleeve.p1.x, geom.cap_left.y + 2.0 * CM),
        Point(grid.center_sleeve.p1.x, geom.hem_left.y - 2.0 * CM),
    )

    # ── Info box ──────────────────────────────────────────────────────────────
    sleeve_hem_width = grid.construction_measures.sleeve_hem_width
    notes = [
        f"Ärmelbreite / sleeve width: {grid.sleeve_width / 10:.1f} cm",
        f"Ärmelkopfhöhe / cap height: {grid.cap_height / 10:.1f} cm",
    ]
    if sleeve_hem_width is not None:
        notes.append(f"Bündchenweite / cuff width: {sleeve_hem_width / 10:.1f} cm")
    if geom.slit is not None and sleeve_config.slit_height is not None:
        notes.append(f"Schlitzhöhe / slit height: {sleeve_config.slit_height / 10:.1f} cm")
    if geom.pleats and sleeve_config.pleat_config is not None:
        _pc = sleeve_config.pleat_config
        notes.append(f"Falten / pleats: {_pc.num_pleats} × {_pc.depth / 10:.1f} cm")
    part.add_info_box(notes=notes)
