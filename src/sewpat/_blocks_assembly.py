"""PatternPart assembly helpers for :mod:`sewpat.blocks`.

All names here are private (prefixed ``_``).  External code should only ever
import from :mod:`sewpat.blocks`.
"""

from ._blocks_geometry import _BackGeometry, _Darts, _FrontGeometry, _SideSeams
from .geometry import Dart, Point, Segment, intersect
from .grids import TopGrid
from .pattern import PatternPart
from .pattern._notches import RoleMap
from .style import STYLE_CENTER_LINE, STYLE_HEM, STYLE_STITCH, STYLE_STITCH_BEVEL

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
