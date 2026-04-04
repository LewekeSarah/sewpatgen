"""Internal geometry builders for the wide sleeve and cuff pattern pieces.

All names here are private (prefixed ``_``).  External code should only ever
import from :mod:`sewpat.blocks`.

This module owns the geometry layer for the wide-sleeve feature set:

* :class:`_WideSleeveGeometry` — frozen dataclass holding all key points,
  curves, and feature markings for the sleeve block.
* :class:`_CuffButtonRow` / :class:`_CuffGeometry` — frozen dataclasses for
  the cuff pattern piece.
* :func:`_build_wide_sleeve_geometry` — main builder: intersections, Bézier
  fitting, slit/pleat resolution.
* :func:`_build_cuff_geometry` — cuff builder: rectangle layout, button rows.
* :func:`_build_button_rows` — button/buttonhole placement for all lap variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .geometry import (
    CubicBezier,
    Point,
    Segment,
    fit_cubic_bezier,
    fit_cubic_bezier_free,
    intersect,
    seam_length,
    split_bezier_seam_fn,
)
from .grids import WideSleeveGrid
from .pleat import Pleat
from .units import CM

if TYPE_CHECKING:
    from .sleeve import SleeveArmhole, SleeveConfig


# ---------------------------------------------------------------------------
# Cap and hem reference-point offsets
# ---------------------------------------------------------------------------

# Notch offsets for the sleeve cap slopes (t along slope, perpendicular offset in mm).
# cap-LEFT slope travels crown→cap_left; Bézier t-params are 0.25/0.50/0.75 in the
# opposite direction, so slope-t 0.75/0.50/0.25 maps to Bézier t 0.25/0.50/0.75.
_CAP_LEFT_NOTCH_PARAMS: tuple[tuple[float, float], ...] = (
    (0.75, -0.8 * CM),
    (0.50, 0.5 * CM),
    (0.25, 1.5 * CM),
)
# cap-RIGHT slope travels cap_right→crown (same direction as the Bézier).
_CAP_RIGHT_NOTCH_PARAMS: tuple[tuple[float, float], ...] = (
    (0.25, 0.0 * CM),
    (0.50, 1.5 * CM),
    (0.75, 2.0 * CM),
)
# Hem reference points: (t along straight hem, perpendicular offset in mm).
# ref 3 (t=0.5) is the split / junction midpoint shared by both Bézier halves.
_HEM_NOTCH_PARAMS: tuple[tuple[float, float], ...] = (
    (1 / 6, -0.5 * CM),
    (2 / 6, 0.0 * CM),
    (3 / 6, 1.0 * CM),  # split point
    (4 / 6, 1.5 * CM),
    (5 / 6, 0.8 * CM),
)


# ---------------------------------------------------------------------------
# _WideSleeveGeometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _WideSleeveGeometry:
    """All computed geometry for the wide sleeve block, prior to part assembly."""

    # ── Key points ────────────────────────────────────────────────────────────
    cap_crown: Point
    cap_left: Point
    cap_right: Point
    hem_left: Point
    hem_right: Point

    # ── Auxiliary construction lines (straight triangle legs) ─────────────────
    cap_left_slope: Segment  # crown → cap_left
    cap_right_slope: Segment  # cap_right → crown

    # ── Sleeve cap Bézier stitch curves ───────────────────────────────────────
    cap_left_curve: CubicBezier
    cap_right_curve: CubicBezier

    # ── Rectangle body outline ────────────────────────────────────────────────
    left_side: CubicBezier
    hem: Segment
    hem_left_curve: CubicBezier
    hem_right_curve: CubicBezier
    right_side: CubicBezier

    # ── Cut line (construction reference only) ────────────────────────────────
    cut_seg: Segment

    # ── Optional feature markings ─────────────────────────────────────────────
    slit: Segment | None
    pleats: tuple[Pleat, ...]

    # ── Construction reference points ─────────────────────────────────────────
    cap_left_notch_pts: tuple[Point, ...]
    cap_right_notch_pts: tuple[Point, ...]
    hem_ref_pts: tuple[Point, ...]

    # ── Cap notch points (set when armhole is supplied) ───────────────────────
    front_armscye_notch_on_cap: Point | None  # front armscye notch on left cap curve
    shoulder_on_cap: Point | None  # shoulder alignment notch on left cap curve
    back_armscye_notch_on_cap: Point | None  # back armscye notch on right cap curve


# ---------------------------------------------------------------------------
# Cuff geometry
# ---------------------------------------------------------------------------

_BUTTON_MIN_MARGIN: float = 10.0  # mm — min distance from top edge / fold line (1 cm)
_BUTTON_MIN_SIDE: float = 5.0  # mm — min distance from section boundaries (0.5 cm)


@dataclass(frozen=True)
class _CuffButtonRow:
    """Geometry for one button/buttonhole pair on the outer cuff face.

    For the two-button case (``num_buttons=2`` with underlap) *button2* holds the
    second button circle.  Both buttons share a single buttonhole mark and are
    placed at the same Y height.
    """

    button: Point  # centre of the first (or only) button circle
    button_radius: float  # circle radius in mm
    hole_start: Point  # left end of the buttonhole mark
    hole_end: Point  # right end of the buttonhole mark
    button2: Point | None = None  # second button (side-by-side); None for single-button rows


@dataclass(frozen=True)
class _CuffGeometry:
    """All computed geometry for the cuff pattern piece, prior to assembly."""

    # ── Dimensions ────────────────────────────────────────────────────────────
    cuff_length: float  # Bündchenlänge — flat circumference (mm)
    cuff_height: float  # single (folded) height — full cut height is 2× (mm)
    underlap: float  # width of left extension, 0 when absent (mm)
    overlap: float  # width of right extension, 0 when absent (mm)

    # ── Key outline points ────────────────────────────────────────────────────
    top_left: Point
    top_right: Point
    bottom_right: Point
    bottom_left: Point

    # ── Fold line ─────────────────────────────────────────────────────────────
    fold_left: Point
    fold_right: Point

    # ── Division line x-coordinates ──────────────────────────────────────────
    # main_left_x: x of the underlap|main boundary (= anchor.x + underlap)
    # main_right_x: x of the main|overlap boundary (= anchor.x + underlap + cuff_length)
    main_left_x: float
    main_right_x: float

    # ── Button / buttonhole rows (empty tuple when none configured) ───────────
    button_rows: tuple[_CuffButtonRow, ...]


# ---------------------------------------------------------------------------
# _build_button_rows
# ---------------------------------------------------------------------------


def _build_button_rows(
    num_buttons: int,
    button_diameter: float,
    buttonhole_ease: float,
    margin: float,
    ax: float,
    ay: float,
    cuff_height: float,
    cuff_length: float,
    underlap: float,
    overlap: float,
) -> tuple[_CuffButtonRow, ...]:
    """Compute button and buttonhole positions for the outer cuff face.

    Always returns at most one _CuffButtonRow. Both button(s) and the single
    buttonhole are placed at the vertical midpoint of the cuff.

    For num_buttons=2 with an underlap wide enough for button_diameter, a second
    button is placed side-by-side (different X, same Y) via button2. Both
    buttons share a single buttonhole. Falls back to single-button layout when
    no adequate underlap is present.

    Placement rules:
      Only overlap:    button at main_right_x - overlap/2; buttonhole centred in overlap.
      Only underlap:   button AT main_left_x; buttonhole in cuff starting at main_left_x.
      Both laps:       button AT main_left_x; buttonhole AT main_right_x.
      No extensions:   both centred in main cuff body.
      num_buttons=2 + underlap: first button at centre of underlap, second at same
                                distance into cuff; single buttonhole per overlap rule.

    Returns:
        Tuple with a single _CuffButtonRow, or empty when height band is too small.
    """
    if num_buttons == 0:  # pragma: no cover
        return ()

    # ── Y-position: always the single vertical midpoint ───────────────────────
    valid_min = ay + margin
    valid_max = ay + cuff_height - margin
    if valid_min >= valid_max:
        return ()

    y_mid = (valid_min + valid_max) / 2.0

    # ── Derived boundaries ────────────────────────────────────────────────────
    main_left_x = ax + underlap
    main_right_x = main_left_x + cuff_length
    buttonhole_length = button_diameter + buttonhole_ease
    half_hole = buttonhole_length / 2.0
    half_btn = button_diameter / 2.0
    has_underlap = underlap > 0
    has_overlap = overlap > 0

    # A cuff without any lap extension closes with elastic — no button closure
    # marks are needed or meaningful.
    if not has_underlap and not has_overlap:
        return ()

    # ── Button X position(s) ──────────────────────────────────────────────────
    button2: Point | None = None
    if num_buttons == 2 and underlap >= button_diameter:
        d = underlap / 2.0
        btn_x = ax + d  # centre of underlap
        button2 = Point(main_left_x + d, y_mid, "Button")  # same distance into cuff
    elif has_underlap:
        btn_x = main_left_x  # at the closure line
    else:  # has_overlap only
        # Button near LEFT edge so it aligns with the buttonhole when the
        # overlap folds closed (symmetric: both overlap/2 from their edge).
        btn_x = ax + overlap / 2.0

    # ── Buttonhole X position (always exactly one) ────────────────────────────
    if has_overlap and has_underlap:
        hole_center_x = main_right_x  # at the main|overlap closure line
    elif has_overlap:
        hole_center_x = main_right_x + overlap / 2.0  # centred in overlap
    else:  # has_underlap only
        # Buttonhole near RIGHT edge, one full underlap-width inward.
        hole_center_x = main_right_x - underlap

    return (
        _CuffButtonRow(
            button=Point(btn_x, y_mid, "Button"),
            button_radius=half_btn,
            hole_start=Point(hole_center_x - half_hole, y_mid, "Buttonhole Start"),
            hole_end=Point(hole_center_x + half_hole, y_mid, "Buttonhole End"),
            button2=button2,
        ),
    )


# ---------------------------------------------------------------------------
# _build_cuff_geometry
# ---------------------------------------------------------------------------


def _build_cuff_geometry(
    sleeve_config: SleeveConfig,
    anchor: Point,
) -> _CuffGeometry | None:
    """Compute the key points for the cuff pattern piece.

    Returns ``None`` when *sleeve_config* has no :attr:`~SleeveConfig.cuff_config`.

    Args:
        sleeve_config: Reads :attr:`~SleeveConfig.cuff_config`.
        anchor:        Top-left origin of the whole piece.

    Returns:
        Fully populated :class:`_CuffGeometry`, or ``None``.
    """
    cc = sleeve_config.cuff_config
    if cc is None:
        return None

    cuff_length = cc.length
    cuff_height = cc.width  # single (folded) height; full cut = 2×
    underlap = cc.underlap
    overlap = cc.overlap
    total_width = underlap + cuff_length + overlap
    total_height = 2.0 * cuff_height

    ax, ay = anchor.x, anchor.y

    # ── Button rows ───────────────────────────────────────────────────────────
    bc = cc.button_config
    if bc is not None and bc.num_buttons > 0:
        button_rows = _build_button_rows(
            num_buttons=bc.num_buttons,
            button_diameter=bc.button_diameter,
            buttonhole_ease=bc.buttonhole_ease,
            margin=bc.margin,
            ax=ax,
            ay=ay,
            cuff_height=cuff_height,
            cuff_length=cuff_length,
            underlap=underlap,
            overlap=overlap,
        )
    else:
        button_rows = ()

    return _CuffGeometry(
        cuff_length=cuff_length,
        cuff_height=cuff_height,
        underlap=underlap,
        overlap=overlap,
        top_left=Point(ax, ay, "Cuff TL"),
        top_right=Point(ax + total_width, ay, "Cuff TR"),
        bottom_right=Point(ax + total_width, ay + total_height, "Cuff BR"),
        bottom_left=Point(ax, ay + total_height, "Cuff BL"),
        fold_left=Point(ax, ay + cuff_height, "Fold Left"),
        fold_right=Point(ax + total_width, ay + cuff_height, "Fold Right"),
        main_left_x=ax + underlap,
        main_right_x=ax + underlap + cuff_length,
        button_rows=button_rows,
    )


# ---------------------------------------------------------------------------
# _build_wide_sleeve_geometry
# ---------------------------------------------------------------------------


def _build_wide_sleeve_geometry(
    grid: WideSleeveGrid,
    sleeve_config: SleeveConfig,
    armhole: SleeveArmhole | None = None,
) -> _WideSleeveGeometry:
    """Build all geometric elements for the wide sleeve block.

    Computes key intersection points, applies hem shortening, fits the cap and
    hem Béziers, and resolves the slit / pleat markings.  The result is a pure
    data object — no :class:`~sewpat.pattern.PatternPart` is touched.

    Args:
        grid:          Constructed wide sleeve grid with all construction lines.
        sleeve_config: Garment config — slit height, pleat config, cuff dims.
        armhole:       Optional armhole seam data used to fit the cap curve.

    Returns:
        Fully populated :class:`_WideSleeveGeometry`.
    """
    # ── Key intersection points ───────────────────────────────────────────────
    cap_left = intersect(grid.left_sleeve, grid.cap_line)[0]
    cap_right = intersect(grid.right_sleeve, grid.cap_line)[0]
    hem_left = intersect(grid.left_sleeve, grid.hem_line)[0]
    hem_right = intersect(grid.right_sleeve, grid.hem_line)[0]

    # ── Hem shortening — symmetric around the centre fold ─────────────────────
    # Shorten by (full_width − cuff_width) / 2 on each side using arc-length
    # projection so the result is orientation-independent.
    sleeve_hem_width = grid.construction_measures.sleeve_hem_width
    if sleeve_hem_width is not None:
        shortening = (2 * grid.sleeve_width - sleeve_hem_width) / 2
        if shortening > 0:
            hem_raw = Segment(hem_left, hem_right)
            hem_left = hem_raw.point_along_from(hem_left, shortening)
            hem_right = hem_raw.point_along_from(hem_right, -shortening)

    # ── Cap crown (apex) ──────────────────────────────────────────────────────
    crown_y = grid.cap_line.p1.y - grid.cap_height
    cap_crown = Point(grid.center_sleeve.p1.x, crown_y, "Cap Crown")

    # ── Auxiliary construction lines ──────────────────────────────────────────
    cap_left_slope = Segment(cap_crown, cap_left, "Cap Left Slope")
    cap_right_slope = Segment(cap_right, cap_crown, "Cap Right Slope")

    # ── Precision reference points along the cap slopes ───────────────────────
    cap_left_notch_pts = tuple(
        cap_left_slope.point_perpendicular(off, t=t) for t, off in _CAP_LEFT_NOTCH_PARAMS
    )
    cap_right_notch_pts = tuple(
        cap_right_slope.point_perpendicular(off, t=t) for t, off in _CAP_RIGHT_NOTCH_PARAMS
    )

    # ── Sleeve cap Bézier stitch curves ───────────────────────────────────────
    cap_left_curve = fit_cubic_bezier(cap_left, cap_crown, cap_left_notch_pts).set_name(
        "Cap Left Curve"
    )
    cap_right_curve = fit_cubic_bezier(cap_right, cap_crown, cap_right_notch_pts).set_name(
        "Cap Right Curve"
    )

    # ── Rectangle body ────────────────────────────────────────────────────────
    # Side seams: gently curved 1 cm inward at mid-height.
    _left_straight = Segment(cap_left, hem_left)
    _left_mid = _left_straight.point_perpendicular(distance=-1.0 * CM, t=0.5)
    left_side = fit_cubic_bezier_free(cap_left, hem_left, [_left_mid], [0.5]).set_name("Left Side")

    hem = Segment(hem_left, hem_right, "Hem")

    _right_straight = Segment(hem_right, cap_right)
    _right_mid = _right_straight.point_perpendicular(distance=-1.0 * CM, t=0.5)
    right_side = fit_cubic_bezier_free(hem_right, cap_right, [_right_mid], [0.5]).set_name(
        "Right Side"
    )

    # ── Shaped hem Bézier — split at midpoint (ref 3) for exact fit ───────────
    hem_ref_pts = tuple(hem.point_perpendicular(off, t=t) for t, off in _HEM_NOTCH_PARAMS)
    mid_hem = hem_ref_pts[2]
    hem_left_curve = fit_cubic_bezier_free(
        hem_left,
        mid_hem,
        [hem_ref_pts[0], hem_ref_pts[1]],
        t_params=(1 / 3, 2 / 3),
    ).set_name("Hem Left")
    hem_right_curve = fit_cubic_bezier_free(
        mid_hem,
        hem_right,
        [hem_ref_pts[3], hem_ref_pts[4]],
        t_params=(1 / 3, 2 / 3),
    ).set_name("Hem Right")

    # ── Direction vector: hem edge → sleeve interior ──────────────────────────
    _dc = grid.center_sleeve.unit_direction
    d_up = Point(-float(_dc[0]), -float(_dc[1]))

    # slit_bottom is always hem_ref_pts[3] (4/6 of hem, 1.5 cm outward).
    slit_bottom = hem_ref_pts[3]

    # ── Slit — parallel to the centre sleeve line at the 4/6 position ─────────
    slit: Segment | None = None
    if sleeve_config.slit_height is not None and sleeve_config.slit_height > 0:
        slit_top = slit_bottom + d_up * sleeve_config.slit_height
        slit = Segment(slit_bottom, slit_top, "Slit")

    # ── Pleats — left and right of the slit ───────────────────────────────────
    pleats: tuple[Pleat, ...]
    if (
        slit is not None
        and sleeve_config.pleat_config is not None
        and sleeve_config.pleat_config.num_pleats > 0
        and sleeve_config.pleat_config.depth > 0
    ):
        hem_base = split_bezier_seam_fn(
            hem_left_curve, hem_right_curve, hem.project_length(hem_right)
        )
        slit_proj = hem.project_length(slit_bottom)
        pleats = tuple(
            Pleat.build_along_seam(
                sleeve_config.pleat_config,
                hem,
                hem_base,
                slit_proj,
                d_up,
            )
        )
    else:
        pleats = ()

    # ── Cut line (sleeve length — construction reference only) ────────────────
    cut_left = intersect(grid.left_sleeve, grid.sleeve_length_line)[0]
    cut_right = intersect(grid.right_sleeve, grid.sleeve_length_line)[0]
    cut_seg = Segment(cut_left, cut_right, "Sleeve Length")

    # ── Cap notch points (requires armhole geometry) ──────────────────────────
    front_armscye_notch_on_cap: Point | None = None
    shoulder_on_cap: Point | None = None
    back_armscye_notch_on_cap: Point | None = None

    if armhole is not None:
        _cap_seam = seam_length([cap_left_curve, cap_right_curve])
        _sleeve_ease = _cap_seam - grid.construction_measures.armscye_circumference
        _ease_q = 0.25 * _sleeve_ease

        _d_front = armhole.front_armscye.arc_length_from_end(armhole.front_armscye_notch)
        if 0.0 < _d_front < cap_left_curve.length:
            _p = cap_left_curve.point_at_length(_d_front)
            front_armscye_notch_on_cap = Point(_p.x, _p.y, "Front Armscye Notch")

        _d_shoulder = armhole.front_armscye.length + _ease_q
        if 0.0 < _d_shoulder < cap_left_curve.length:
            _p = cap_left_curve.point_at_length(_d_shoulder)
            shoulder_on_cap = Point(_p.x, _p.y, "Shoulder Notch")

        _d_back = armhole.back_armscye_lower.length + _ease_q
        if 0.0 < _d_back < cap_right_curve.length:
            _p = cap_right_curve.point_at_length(_d_back)
            back_armscye_notch_on_cap = Point(_p.x, _p.y, "Back Armscye Notch")

    return _WideSleeveGeometry(
        cap_crown=cap_crown,
        cap_left=cap_left,
        cap_right=cap_right,
        hem_left=hem_left,
        hem_right=hem_right,
        cap_left_slope=cap_left_slope,
        cap_right_slope=cap_right_slope,
        cap_left_curve=cap_left_curve,
        cap_right_curve=cap_right_curve,
        left_side=left_side,
        hem=hem,
        hem_left_curve=hem_left_curve,
        hem_right_curve=hem_right_curve,
        right_side=right_side,
        cut_seg=cut_seg,
        slit=slit,
        pleats=pleats,
        cap_left_notch_pts=cap_left_notch_pts,
        cap_right_notch_pts=cap_right_notch_pts,
        hem_ref_pts=hem_ref_pts,
        front_armscye_notch_on_cap=front_armscye_notch_on_cap,
        shoulder_on_cap=shoulder_on_cap,
        back_armscye_notch_on_cap=back_armscye_notch_on_cap,
    )
