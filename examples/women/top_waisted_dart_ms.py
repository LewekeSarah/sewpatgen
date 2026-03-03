#!/usr/bin/env python3
"""Waisted women's top with waist darts — Mueller & Sohn method.

Construction follows the classic Mueller & Sohn "Grundschnitt Bluse" system
(Rundschau / Modenähen), adapted for a fitted waisted top with:

  - Rücken (back): waist dart along the back-arm line
  - Vorderteil (front): waist dart along the front-arm line, plus bust dart
    from the side seam toward the bust point

Coordinate system: SVG — x increases right, y increases DOWN.

Construction order
------------------
1. Construction grid (Konstruktionsgitter)
2. Back piece (Rücken)
3. Front piece (Vorderteil)
Both pieces are kept in the same coordinate frame, mirrored across the
centre-back / centre-front vertical — exactly as drawn on paper.

Measurements used (all in mm internally, entered in cm)
---------------------------------------------------------
Person
  BrU   Brustumfang         bust circumference
  TaU   Taillenumfang       waist circumference
  HüU   Hüftumfang          hip circumference
  HüT   Hüfttiefe           hip depth (waist to hip)
  BrT   Brusttiefe          bust depth (shoulder to bust point, vertical)
  HlB   Halslochbreite      neck width (half)
  BrPA  Brustpunktabstand   bust point spacing (half, centre to centre)
  SuB   Schulterbreite      shoulder width
  RüL   Rückenlänge         back length (nape to waist)
  VL    Vorderlänge         front length (shoulder point to waist)
  AlT   Armlochtiefe        armscye depth

Ease (Zugabe / Weite)
  ease_BrU    bust ease          default 8 cm
  ease_TaU    waist ease         default 6 cm
  ease_HüU    hip ease           default 4 cm
  sa          seam allowance     default 1 cm
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from sewpat.geometry import (
    CubicBezier,
    Point,
    Segment,
    intersect,
)
from sewpat.pages import DinA0, DinA1
from sewpat.part import ConstructionGrid, Pattern, PatternPart
from sewpat.person import Person
from sewpat.render import export_pattern_svg_mm
from sewpat.style import StyleOptions
from sewpat.units import CM


# ---------------------------------------------------------------------------
# Measurements dataclass
# ---------------------------------------------------------------------------

@dataclass
class TopMeasurements:
    """All working measurements (body + ease) for the waisted top."""

    # ── Body measurements (mm) ─────────────────────────────────────────────
    BrU: float   # Brustumfang
    TaU: float   # Taillenumfang
    HüU: float   # Hüftumfang
    HüT: float   # Hüfttiefe
    BrT: float   # Brusttiefe
    HlB: float   # Halslochbreite
    BrPA: float  # Brustpunktabstand (half)
    SuB: float   # Schulterbreite
    RüL: float   # Rückenlänge
    VL: float    # Vorderlänge (already balanced by caller if needed)
    AlT: float   # Armlochtiefe

    # ── Ease (mm) ─────────────────────────────────────────────────────────
    ease_BrU: float = 8.0 * CM
    ease_TaU: float = 6.0 * CM
    ease_HüU: float = 4.0 * CM

    # ── Seam allowance ─────────────────────────────────────────────────────
    sa: float = 1.0 * CM

    # ── Derived widths ─────────────────────────────────────────────────────
    BrW: float = field(init=False)   # total bust width (body + ease)
    TaW: float = field(init=False)   # total waist width
    HüW: float = field(init=False)   # total hip width

    # ── Width components (¼ of total width) ────────────────────────────────
    RüB: float = field(init=False)   # back width   = BrU/8 + 5.5 cm
    ArD: float = field(init=False)   # armhole width = BrU/8 – 1.5 cm
    BrB: float = field(init=False)   # chest width  = BrU/4 – 4.0 cm

    def __post_init__(self) -> None:
        # Mueller & Sohn / existing blouse.py convention:
        #   BrW = BrU + ease_BrU   (full half-pattern width incl. ease)
        #   RüB + ArD + BrB = BrU/2  (body-only half width, ease distributed in ArD zone)
        self.BrW = self.BrU + self.ease_BrU
        self.TaW = self.TaU + self.ease_TaU
        self.HüW = self.HüU + self.ease_HüU
        # Mueller & Sohn width formulae for BrU 80–89 cm (body only, no ease)
        self.RüB = self.BrU / 8 + 5.5 * CM
        self.ArD = self.BrU / 8 - 1.5 * CM
        self.BrB = self.BrU / 4 - 4.0 * CM


def make_measurements(person: Person, ease_TaU: float = 6.0 * CM,
                       ease_HüU: float = 4.0 * CM) -> TopMeasurements:
    """Build TopMeasurements from a Person, computing missing derived values."""
    if person.AlT is None:
        alT = person.BrU / 10 + 11.0 * CM
    else:
        alT = person.AlT
    return TopMeasurements(
        BrU=person.BrU,
        TaU=person.TaU,
        HüU=person.HüU,
        HüT=person.HüT,
        BrT=person.BrT,
        HlB=person.HlB,
        BrPA=person.BrPA,
        SuB=person.SuB,
        RüL=person.RüL,
        VL=person.VL,
        AlT=alT,
        ease_TaU=ease_TaU,
        ease_HüU=ease_HüU,
    )


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------

def _bezier_neck_back(corner: Point, shoulder_end: Point, spine_top: Point) -> CubicBezier:
    """Smooth quarter-ellipse neck curve for the back piece.

    From *corner* (shoulder/neck corner) down to *spine_top* (centre-back
    neck point at shoulder level) with a gentle inward bow.
    """
    dx = abs(shoulder_end.x - spine_top.x)
    dy = abs(corner.y - spine_top.y)
    cp1 = corner.translate(0, dy * 0.5)
    cp2 = spine_top.translate(dx * 0.4, 0)
    return CubicBezier(corner, cp1, cp2, spine_top, name="hintere Halsrundung")


def _bezier_neck_front(
    neckline_shoulder: Point,
    neckline_centre: Point,
) -> CubicBezier:
    """Smooth front neckline from shoulder to centre-front.

    Tangent at the shoulder end is horizontal; tangent at centre-front is vertical.
    """
    dx = abs(neckline_shoulder.x - neckline_centre.x)
    dy = abs(neckline_shoulder.y - neckline_centre.y)
    cp1 = neckline_shoulder.translate(-dx * 0.5, 0)
    cp2 = neckline_centre.translate(0, -dy * 0.4)
    return CubicBezier(neckline_shoulder, cp1, cp2, neckline_centre, name="vordere Halsrundung")


def _bezier_armscye_back(
    shoulder_pt: Point,
    armscye_side: Point,
    control_depth: float,
) -> CubicBezier:
    """Back armscye curve from shoulder point down to the side armscye point."""
    cp1 = shoulder_pt.translate(0, control_depth * 0.6)
    cp2 = armscye_side.translate(-control_depth * 0.2, -control_depth * 0.3)
    return CubicBezier(shoulder_pt, cp1, cp2, armscye_side, name="hinteres Armloch")


def _bezier_armscye_front(
    armscye_side: Point,
    shoulder_pt: Point,
    control_depth: float,
) -> CubicBezier:
    """Front armscye curve from the side armscye point up to the shoulder point."""
    cp1 = armscye_side.translate(control_depth * 0.25, -control_depth * 0.35)
    cp2 = shoulder_pt.translate(0, control_depth * 0.55)
    return CubicBezier(armscye_side, cp1, cp2, shoulder_pt, name="vorderes Armloch")


# ---------------------------------------------------------------------------
# Pattern construction
# ---------------------------------------------------------------------------

def make_top(meas: TopMeasurements, model_length: float = 55.0 * CM) -> Pattern:
    """Draft the full waisted top pattern.

    Args:
        meas:          Computed measurements (body + ease).
        model_length:  Finished garment length from nape to hem (default 55 cm).

    Returns:
        A :class:`Pattern` with construction grid, back piece, and front piece.
    """
    # SVG origin — top-left margin
    anchor = Point(5.0 * CM, 5.0 * CM, "Ursprung")
    pattern = Pattern(name="Tailliertes Top mit Abnähern", anchor=anchor)

    # ── Width shortcuts ────────────────────────────────────────────────────
    # BeckenAdjustment: slight diagonal shift of the vertical "spine" at hip
    # level (Mueller & Sohn §2.6).  For simplicity we set it to 1 cm.
    becken_adj = 1.0 * CM

    # ──────────────────────────────────────────────────────────────────────
    # 1. CONSTRUCTION GRID
    # ──────────────────────────────────────────────────────────────────────
    # pt7_shift: the intersection of the hip diagonal with the bust line
    # shifts all width measurements by this amount (see blouse_grid.py).
    pt7_shift = becken_adj * meas.AlT / meas.RüL

    grid = ConstructionGrid(
        anchor=anchor,
        horizontals=[
            ("Schulterlinie",  0),
            ("Brustlinie",     meas.AlT),
            ("Taillenlinie",   meas.RüL),
            ("Hüftlinie",      meas.RüL + meas.HüT),
            ("Saumlinie",      model_length),
        ],
        verticals=[
            ("hintere Mitte",           0),
            ("hintere Armlinie",        pt7_shift + meas.RüB),
            ("Seitenlinie RT",          pt7_shift + meas.RüB + meas.ArD * 2 / 3),
            ("Seitenlinie VT",          pt7_shift + meas.RüB + meas.ArD * 2 / 3 + 10 * CM),
            ("vordere Armlinie",        pt7_shift + meas.RüB + meas.ArD * 2 / 3 + 10 * CM + meas.ArD / 3),
            ("vordere Mitte",           pt7_shift + meas.BrW / 2 + 10 * CM),
        ],
        part_name="Konstruktionsgitter",
    )
    grid_part = grid.build()
    pattern.add_part(grid_part)

    # Retrieve named grid lines
    seg_schulter   = grid_part.get_element("Schulterlinie").geometry
    seg_bust       = grid_part.get_element("Brustlinie").geometry
    seg_waist      = grid_part.get_element("Taillenlinie").geometry
    seg_hip        = grid_part.get_element("Hüftlinie").geometry
    seg_hem        = grid_part.get_element("Saumlinie").geometry
    seg_hm         = grid_part.get_element("hintere Mitte").geometry       # back centre
    seg_ha         = grid_part.get_element("hintere Armlinie").geometry    # back arm line
    seg_srt        = grid_part.get_element("Seitenlinie RT").geometry      # side RT
    seg_svt        = grid_part.get_element("Seitenlinie VT").geometry      # side VT
    seg_va         = grid_part.get_element("vordere Armlinie").geometry    # front arm line
    seg_vm         = grid_part.get_element("vordere Mitte").geometry       # front centre

    # Key grid intersections
    pt_bust_hm     = intersect(seg_bust, seg_hm)[0]    # back centre × bust
    pt_bust_ha     = intersect(seg_bust, seg_ha)[0]    # back arm × bust
    pt_bust_srt    = intersect(seg_bust, seg_srt)[0]   # side RT × bust
    pt_bust_svt    = intersect(seg_bust, seg_svt)[0]   # side VT × bust
    pt_bust_va     = intersect(seg_bust, seg_va)[0]    # front arm × bust
    pt_bust_vm     = intersect(seg_bust, seg_vm)[0]    # front centre × bust

    pt_waist_hm    = intersect(seg_waist, seg_hm)[0]
    pt_waist_ha    = intersect(seg_waist, seg_ha)[0]
    pt_waist_srt   = intersect(seg_waist, seg_srt)[0]
    pt_waist_svt   = intersect(seg_waist, seg_svt)[0]
    pt_waist_va    = intersect(seg_waist, seg_va)[0]
    pt_waist_vm    = intersect(seg_waist, seg_vm)[0]

    pt_hip_hm      = intersect(seg_hip, seg_hm)[0]
    pt_hip_srt     = intersect(seg_hip, seg_srt)[0]
    pt_hip_svt     = intersect(seg_hip, seg_svt)[0]
    pt_hip_vm      = intersect(seg_hip, seg_vm)[0]

    pt_hem_hm      = intersect(seg_hem, seg_hm)[0]
    pt_hem_srt     = intersect(seg_hem, seg_srt)[0]
    pt_hem_svt     = intersect(seg_hem, seg_svt)[0]
    pt_hem_vm      = intersect(seg_hem, seg_vm)[0]

    pt_shoulder_hm = intersect(seg_schulter, seg_hm)[0]
    pt_shoulder_vm = intersect(seg_schulter, seg_vm)[0]

    # ──────────────────────────────────────────────────────────────────────
    # 2. BACK PIECE  (Rücken)
    # ──────────────────────────────────────────────────────────────────────
    back = PatternPart(name="Rücken")
    pattern.add_part(back)

    # ── Back neck (Halslochbreite × Halstiefe) ─────────────────────────────
    # Neck width = HlB from centre, neck depth ≈ 2 cm (Mueller & Sohn)
    neck_width_b  = meas.HlB
    neck_depth_b  = 2.0 * CM

    pt_neck_cb    = pt_shoulder_hm.translate(neck_width_b, 0)     # corner of neck
    pt_neck_top   = pt_shoulder_hm.translate(0, neck_depth_b)     # nape drop on CB
    # Smooth back neck curve
    curve_neck_b  = _bezier_neck_back(pt_neck_cb, anchor, pt_neck_top)
    back.append(curve_neck_b, is_outline=True)

    # ── Back shoulder line ─────────────────────────────────────────────────
    # Shoulder width = SuB/2 from neck corner; slight drop ≈ 1.5 cm (Mueller & Sohn)
    shoulder_width_b  = meas.SuB / 2
    shoulder_drop_b   = 1.5 * CM
    pt_shoulder_back  = pt_neck_cb.translate(shoulder_width_b, shoulder_drop_b)
    seg_shoulder_b    = Segment(pt_neck_cb, pt_shoulder_back, "hintere Schulterlinie")
    back.append(seg_shoulder_b, is_outline=True)

    # ── Back armscye (Armloch) ─────────────────────────────────────────────
    # Mueller & Sohn: the armscye runs from the shoulder point to the side
    # seam point (Seitenpunkt) at bust level.  The curve bows outward via a
    # control point placed at the hintere Armlinie, giving the classic hollow
    # back armscye shape.
    curve_arm_b = _bezier_armscye_back(
        pt_shoulder_back, pt_bust_srt, meas.ArD
    )
    back.append(curve_arm_b, is_outline=True)

    # ── Side seam — back (RT) ──────────────────────────────────────────────
    # The total waist intake (half-pattern) is split across four elements:
    #   back dart  35 %  ·  front dart  35 %  ·  side seam back  15 %  ·  side seam front  15 %
    total_waist_reduction = meas.BrW - meas.TaW   # total half-pattern reduction
    dart_back_width       = total_waist_reduction * 0.35
    side_reduction_back   = total_waist_reduction * 0.15  # back side-seam share

    pt_side_bust_b   = pt_bust_srt
    pt_side_waist_b  = pt_waist_srt.translate(-side_reduction_back, 0)
    pt_side_hip_b    = pt_hip_srt
    pt_side_hem_b    = pt_hem_srt

    seg_side_bust_waist_b  = Segment(pt_side_bust_b, pt_side_waist_b, "Seitennaht Rücken ob.")
    seg_side_waist_hip_b   = Segment(pt_side_waist_b, pt_side_hip_b, "Seitennaht Rücken u.")
    seg_side_hip_hem_b     = Segment(pt_side_hip_b, pt_side_hem_b, "Seitennaht Rücken Saum")
    back.append(seg_side_bust_waist_b, is_outline=True)
    back.append(seg_side_waist_hip_b, is_outline=True)
    back.append(seg_side_hip_hem_b, is_outline=True)

    # ── Hem — back ─────────────────────────────────────────────────────────
    seg_hem_b = Segment(pt_hem_hm, pt_side_hem_b, "Saumlinie Rücken")
    back.append(seg_hem_b, is_outline=True)

    # ── Centre back (hintere Mitte) — from hem up to nape ──────────────────
    # seam_allowance=0.0: cut on the fold, no SA on this edge.
    _fold = StyleOptions(seam_allowance=0.0)
    seg_cb_hem_waist  = Segment(pt_hem_hm, pt_waist_hm, "hintere Mitte Saum–Taille")
    seg_cb_waist_bust = Segment(pt_waist_hm, pt_bust_hm, "hintere Mitte Taille–Brust")
    seg_cb_bust_neck  = Segment(pt_bust_hm, pt_neck_top, "hintere Mitte Brust–Hals")
    back.append(seg_cb_hem_waist,  style=_fold, is_outline=True)
    back.append(seg_cb_waist_bust, style=_fold, is_outline=True)
    back.append(seg_cb_bust_neck,  style=_fold, is_outline=True)

    # ── Back waist dart (Rücken-Taillenausnäher) ───────────────────────────
    # The dart is centred on the back-arm line (hintere Armlinie).
    # Dart centre line runs vertically through pt_waist_ha.
    dart_b_centre_x  = pt_waist_ha.x
    half_dw_b        = dart_back_width / 2

    dart_b_left      = Point(dart_b_centre_x - half_dw_b, pt_waist_ha.y, "Abnäher hR links")
    dart_b_right     = Point(dart_b_centre_x + half_dw_b, pt_waist_ha.y, "Abnäher hR rechts")
    # Dart point: on the bust line at the arm-line intersection
    dart_b_tip       = pt_bust_ha.translate(0, -2.0 * CM)  # 2 cm above bust for ease
    dart_b_tip       = Point(dart_b_tip.x, dart_b_tip.y, "Abnäherspitze Rücken")

    # Draw dart legs as construction lines (fold lines)
    back.append(Segment(dart_b_left,  dart_b_tip,  "Abnäher Rücken links"))
    back.append(Segment(dart_b_right, dart_b_tip,  "Abnäher Rücken rechts"))
    # Dart base on waist line
    back.append(Segment(dart_b_left,  dart_b_right, "Abnäherweite Rücken"))

    # Precision marks at dart points
    back.add_precision_points(dart_b_tip, dart_b_left, dart_b_right)

    # ── Grainline — back (parallel to hintere Mitte) ───────────────────────
    grain_start_b = pt_bust_hm.translate(3.0 * CM, 0)
    grain_end_b   = grain_start_b.translate(0, meas.RüL * 0.7)
    back.add_grainline(grain_start_b, grain_end_b)

    # ── Seam allowance — back ──────────────────────────────────────────────
    # CB edges carry seam_allowance=0.0 in their style → kept in place (fold line).
    back.add_seam_allowance(meas.sa)
    back.add_info_box(
        header="Rücken",
        notes=[f"Nahtzugabe {meas.sa/CM:.0f} cm (außer Stoffbruch)", "1× zuschneiden, auf Falte legen"],
    )

    # ──────────────────────────────────────────────────────────────────────
    # 3. FRONT PIECE  (Vorderteil)
    # ──────────────────────────────────────────────────────────────────────
    front = PatternPart(name="Vorderteil")
    pattern.add_part(front)

    # ── Front neck ─────────────────────────────────────────────────────────
    neck_width_f  = meas.HlB + 0.5 * CM           # front neck slightly wider
    neck_depth_f  = meas.HlB + 1.0 * CM           # square-ish front neck

    pt_neck_cf_top    = pt_shoulder_vm.translate(-neck_width_f, 0)    # neck/shoulder corner
    pt_neck_cf_bottom = pt_shoulder_vm.translate(0, neck_depth_f)     # centre-front neck depth

    # Smooth front neck curve (shoulder corner → CF neck point)
    curve_neck_f = _bezier_neck_front(pt_neck_cf_top, pt_neck_cf_bottom)
    front.append(curve_neck_f, is_outline=True)

    # ── Front shoulder ─────────────────────────────────────────────────────
    shoulder_width_f = meas.SuB / 2 - 0.5 * CM   # front shoulder slightly shorter
    shoulder_drop_f  = 1.5 * CM
    pt_shoulder_front = pt_neck_cf_top.translate(-shoulder_width_f, shoulder_drop_f)
    seg_shoulder_f    = Segment(pt_neck_cf_top, pt_shoulder_front, "vordere Schulterlinie")
    front.append(seg_shoulder_f, is_outline=True)

    # ── Bust point (Brustpunkt) ─────────────────────────────────────────────
    # BrPA from centre-front; BrT below shoulder line
    pt_bust_point = pt_shoulder_vm.translate(-meas.BrPA, meas.BrT)

    # ── Front armscye ──────────────────────────────────────────────────────
    # Runs from the side seam bust point up to the shoulder point.
    curve_arm_f = _bezier_armscye_front(
        pt_bust_svt, pt_shoulder_front, meas.ArD
    )
    front.append(curve_arm_f, is_outline=True)

    # ── Side seam — front ──────────────────────────────────────────────────
    side_reduction_front = total_waist_reduction * 0.15  # front side-seam share (= back)
    dart_front_width     = total_waist_reduction * 0.35  # waist dart on front arm line

    pt_side_bust_f   = pt_bust_svt
    pt_side_waist_f  = pt_waist_svt.translate(side_reduction_front, 0)  # +x = toward CF
    pt_side_hip_f    = pt_hip_svt
    pt_side_hem_f    = pt_hem_svt

    seg_side_bust_waist_f  = Segment(pt_side_bust_f, pt_side_waist_f, "Seitennaht Vorderteil ob.")
    seg_side_waist_hip_f   = Segment(pt_side_waist_f, pt_side_hip_f, "Seitennaht Vorderteil u.")
    seg_side_hip_hem_f     = Segment(pt_side_hip_f, pt_side_hem_f, "Seitennaht Vorderteil Saum")
    front.append(seg_side_bust_waist_f, is_outline=True)
    front.append(seg_side_waist_hip_f, is_outline=True)
    front.append(seg_side_hip_hem_f, is_outline=True)

    # ── Hem — front ────────────────────────────────────────────────────────
    seg_hem_f = Segment(pt_side_hem_f, pt_hem_vm, "Saumlinie Vorderteil")
    front.append(seg_hem_f, is_outline=True)

    # ── Centre front (from hem up to neck point) ───────────────────────────
    # seam_allowance=0.0: cut on the fold, no SA on this edge.
    _fold = StyleOptions(seam_allowance=0.0)
    seg_cf_hem_waist  = Segment(pt_hem_vm, pt_waist_vm, "vordere Mitte Saum–Taille")
    seg_cf_waist_bust = Segment(pt_waist_vm, pt_bust_vm, "vordere Mitte Taille–Brust")
    seg_cf_bust_neck  = Segment(pt_bust_vm, pt_neck_cf_bottom, "vordere Mitte Brust–Hals")
    front.append(seg_cf_hem_waist,  style=_fold, is_outline=True)
    front.append(seg_cf_waist_bust, style=_fold, is_outline=True)
    front.append(seg_cf_bust_neck,  style=_fold, is_outline=True)

    # ── Front waist dart (Taillenabnäher Vorderteil) ───────────────────────
    # Centred on the front-arm line (vordere Armlinie), pointing to the bust point.
    dart_f_centre_x = pt_waist_va.x
    half_dw_f       = dart_front_width / 2

    dart_f_left  = Point(dart_f_centre_x - half_dw_f, pt_waist_va.y, "Taillenabnh. vorn links")
    dart_f_right = Point(dart_f_centre_x + half_dw_f, pt_waist_va.y, "Taillenabnh. vorn rechts")
    # Dart tip: toward bust point, stopping ~2 cm short
    dart_f_dir   = (
        pt_bust_point.x - dart_f_centre_x,
        pt_bust_point.y - pt_waist_va.y,
    )
    dart_f_len   = math.hypot(*dart_f_dir)
    dart_f_unit  = (dart_f_dir[0] / dart_f_len, dart_f_dir[1] / dart_f_len)
    dart_f_tip   = Point(
        dart_f_centre_x  + dart_f_unit[0] * (dart_f_len - 2.0 * CM),
        pt_waist_va.y    + dart_f_unit[1] * (dart_f_len - 2.0 * CM),
        "Taillenabnh. Spitze",
    )

    front.append(Segment(dart_f_left,  dart_f_tip,  "Taillenabnäher links"))
    front.append(Segment(dart_f_right, dart_f_tip,  "Taillenabnäher rechts"))
    front.append(Segment(dart_f_left,  dart_f_right, "Taillenabnäherweite"))

    front.add_precision_points(dart_f_tip, dart_f_left, dart_f_right)

    # ── Side bust dart (Seitenabnäher) ─────────────────────────────────────
    # Mueller & Sohn: small bust dart from the side seam toward the bust point.
    # Dart opens at the bust line on the side seam (Seitenlinie VT).
    bust_dart_width = 2.5 * CM          # standard opening for BrU 80–89 cm
    half_bdw        = bust_dart_width / 2

    pt_bust_dart_upper = pt_side_bust_f.translate(0, -half_bdw)
    pt_bust_dart_lower = pt_side_bust_f.translate(0, half_bdw)
    # Tip: 2.5 cm short of the bust point
    bp_dir   = (pt_bust_point.x - pt_side_bust_f.x, pt_bust_point.y - pt_side_bust_f.y)
    bp_dist  = math.hypot(*bp_dir)
    bp_unit  = (bp_dir[0] / bp_dist, bp_dir[1] / bp_dist)
    pt_bust_dart_tip = Point(
        pt_side_bust_f.x + bp_unit[0] * (bp_dist - 2.5 * CM),
        pt_side_bust_f.y + bp_unit[1] * (bp_dist - 2.5 * CM),
        "Seitenabnäher Spitze",
    )

    front.append(Segment(pt_bust_dart_upper, pt_bust_dart_tip, "Seitenabnäher oben"))
    front.append(Segment(pt_bust_dart_lower, pt_bust_dart_tip, "Seitenabnäher unten"))
    front.append(Segment(pt_bust_dart_upper, pt_bust_dart_lower, "Seitenabnäherweite"))

    front.add_precision_points(pt_bust_dart_tip, pt_bust_point)

    # ── Grainline — front (parallel to vordere Mitte) ─────────────────────
    grain_start_f = pt_bust_vm.translate(-3.0 * CM, 0)
    grain_end_f   = grain_start_f.translate(0, meas.RüL * 0.7)
    front.add_grainline(grain_start_f, grain_end_f)

    # ── Seam allowance — front ─────────────────────────────────────────────
    # CF edges carry seam_allowance=0.0 in their style → kept in place (fold line).
    front.add_seam_allowance(meas.sa)
    front.add_info_box(
        header="Vorderteil",
        notes=[f"Nahtzugabe {meas.sa/CM:.0f} cm (außer Stoffbruch)", "1× zuschneiden, auf Falte legen"],
    )

    # ── Grid notches on both pieces ────────────────────────────────────────
    back.add_grid_notches(grid_part)
    front.add_grid_notches(grid_part)

    return pattern


# ---------------------------------------------------------------------------
# Example person & main
# ---------------------------------------------------------------------------

def make_person() -> Person:
    """Standard size 38 (Mueller & Sohn, BrU 84 cm)."""
    return Person(
        KöH=168 * CM,
        BrU=84.0 * CM,
        TaU=68.0 * CM,
        HüU=94.0 * CM,
        HüT=20.0 * CM,
        BrT=26.0 * CM,
        HlB=6.8 * CM,
        BrPA=9.0 * CM,
        SuB=13.0 * CM,
        RüL=40.0 * CM,
        VL=43.5 * CM,
    )


if __name__ == "__main__":
    person  = make_person()
    meas    = make_measurements(person)
    pattern = make_top(meas)

    out_dir = Path(__file__).parent

    # With construction grid
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA0.width,
        height_mm=DinA0.height,
        filename=str(out_dir / "top_waisted_dart_grid.svg"),
        parts=["Konstruktionsgitter", "Rücken", "Vorderteil"],
    )

    # Clean pattern pieces only
    export_pattern_svg_mm(
        pattern,
        width_mm=DinA1.width,
        height_mm=DinA1.height,
        filename=str(out_dir / "top_waisted_dart.svg"),
        parts=["Rücken", "Vorderteil"],
    )

    print("✓ top_waisted_dart.svg")
    print("✓ top_waisted_dart_grid.svg")








