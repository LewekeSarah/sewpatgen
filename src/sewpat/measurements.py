"""Ease-adjusted garment measurements derived from body measurements and fit class.

This module provides dataclasses for garment measurements (with ease already
applied), distribution helpers that split waist and hip shortfall into darts
and side-seam intakes, and factory functions that combine a
:class:`~sewpat.person.Person` with a :class:`~sewpat.fitclass.FitClass` to
produce construction-ready measurements.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sewpat.geometry import Point
from sewpat.person import BalanceAdjustments, BalancedPerson, Gender, Person
from sewpat.units import CM

if TYPE_CHECKING:
    from sewpat.fitclass import FitClass

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


# Fractions used by calculate_waist_distribution().
_SN_FRACTION: float = 0.25  # fraction of hip_shortfall → each side seam
_FRONT_FRACTION: float = 0.40  # fraction of residual → front waist dart

# Map from FitClass resolved property names → body measurement field names.
_BODY_EASE_MAP: dict[str, str] = {
    "back_width_ease": "back_width",
    "armscye_width_ease": "armscye_width",
    "chest_width_ease": "chest_width",
    "armscye_depth_ease": "armscye_depth",
    "shoulder_width_ease": "shoulder_width",
}


@dataclass
class TrouserEase:
    """Explicit ease additions for trouser construction.

    Used when no fit-class PK table entry is available for the garment type
    (e.g. children's shorts, sportswear).  All values in mm.

    Attributes:
        body_rise_ease: Added to body rise (SiH).
        inseam_ease:    Added to inside-leg length (SrH).
        hip_ease:       Added to hip circumference (HüU).
    """

    body_rise_ease: float = 0.0  # SiH — Sitzhöhe-Zugabe
    inseam_ease: float = 0.0  # SrH — Schritthöhe-Zugabe
    hip_ease: float = 0.0  # HüU — Hüftumfang-Zugabe
    waist_ease: float = 0.0  # TaU — Taillenumfang-Zugabe


@dataclass
class TrouserMeasurements:
    """Ease-adjusted measurements for trouser construction.

    All values are in mm (the project's internal unit).

    Attributes:
        waist: TaU — Taillenumfang (waist circumference, with ease).
        hip: HüU — Hüftumfang (hip circumference, with ease).
        body_rise: SiH — Sitzhöhe (body rise, with ease).
        waist_width: TaW — Taillenweite fertig (finished waist half-width).
        hip_width: HüW — Hüftweite fertig (finished hip half-width).
        hip_depth: HüT — Hüfttiefe (hip depth; optional).
        inseam: SrH — Schritthöhe (inside leg length; optional).
        sTaH: Combined rise + inseam for children (optional).
        knee_height: Kniehöhe (knee height, derived if not given).
        front_trouser_width: vHoB — Vorderhosenbreite (defaults to 25 % of hip_width).
        gender: Used for gender-specific construction formulas.
    """

    waist: float  # TaU — Taillenumfang
    hip: float  # HüU — Hüftumfang
    body_rise: float  # SiH — Sitzhöhe
    waist_width: float  # TaW — Taillenweite fertig
    hip_width: float  # HüW — Hüftweite fertig
    hip_depth: float | None = None  # HüT — Hüfttiefe
    inseam: float | None = None  # SrH — Schritthöhe
    sTaH: float | None = None
    knee_height: float | None = None  # Kniehöhe
    front_trouser_width: float | None = None  # vHoB — Vorderhosenbreite
    gender: Gender = Gender.female

    def __post_init__(self) -> None:
        """Derive ``front_trouser_width`` and ``knee_height`` when not explicitly set."""
        self.front_trouser_width = (
            0.25 * self.hip_width if self.front_trouser_width is None else self.front_trouser_width
        )
        if self.gender in [Gender.boy, Gender.girl]:
            inseam = self.inseam
            if inseam is None:
                raise ValueError("inseam must be set for boy/girl trouser construction.")
            self.knee_height = 0.5 * inseam if self.knee_height is None else self.knee_height
            self.sTaH = inseam + self.body_rise
        elif self.gender == Gender.female:
            inseam = self.inseam
            stah = self.sTaH
            if inseam is None:
                raise ValueError("inseam must be set for female trouser construction.")
            if stah is None:
                raise ValueError("sTaH must be set for female trouser construction.")
            self.knee_height = (
                0.5 * inseam - inseam / 10 if self.knee_height is None else self.knee_height
            )
            self.inseam = stah - inseam
        if self.knee_height is None:
            raise NotImplementedError("knee_height is missing.")


@dataclass
class BlouseMeasurements:
    """Ease-adjusted measurements for blouse / top construction.

    All values are in mm (the project's internal unit).
    Build via :func:`make_top_measurements` from a
    :class:`~sewpat.person.BalancedPerson` and a
    :class:`~sewpat.fitclass.FitClass`.

    Attributes:
        bust: BrU — Brustumfang (bust circumference).
        waist: TaU — Taillenumfang (waist circumference).
        hip: HüU — Hüftumfang (hip circumference).
        hip_depth: HüT — Hüfttiefe (hip depth).
        bust_depth: BrT — Brusttiefe (bust depth).
        neck_size: HlB — Halslochbreite (neck hole width).
        bust_span: BrPA — Brustpunktabstand (bust point distance).
        shoulder_width: SuB — Schulterbreite (shoulder width, with ease).
        back_length: RüL — Rückenlänge (back length).
        front_length: VL — Vorderlänge (front length).
        bust_width: BrW — Brustbreite fertig (half-width, with ease).
        waist_width: TaW — Taillenweite fertig (half-width, with ease).
        hip_width: HüW — Hüftweite fertig (half-width, with ease).
        armscye_depth: AlT — Armlochtiefe (armhole depth, with ease).
        back_width: RüB — Rückenbreite (back width, with ease).
        armscye_width: ArD — Armdurchmesser (arm diameter, with ease).
        chest_width: BrB — Brustbreite (chest width, with ease).
        gender: Used for gender-specific construction formulas.
    """

    bust: float  # BrU — Brustumfang
    waist: float  # TaU — Taillenumfang
    hip: float  # HüU — Hüftumfang
    hip_depth: float  # HüT — Hüfttiefe
    bust_depth: float  # BrT — Brusttiefe
    neck_size: float  # HlB — Halslochbreite
    bust_span: float  # BrPA — Brustpunktabstand
    shoulder_width: float  # SuB — Schulterbreite
    back_length: float  # RüL — Rückenlänge
    front_length: float  # VL  — Vorderlänge
    bust_width: float  # BrW — Brustbreite fertig (half-width)
    waist_width: float  # TaW — Taillenweite fertig (half-width)
    hip_width: float  # HüW — Hüftweite fertig (half-width)
    armscye_depth: float  # AlT — Armlochtiefe
    back_width: float  # RüB — Rückenbreite
    armscye_width: float  # ArD — Armdurchmesser
    chest_width: float  # BrB — Brustbreite
    gender: Gender = Gender.female

    def __post_init__(self) -> None:
        """Validate that back + armscye + chest widths sum to bust_width / 2."""
        if (
            abs(self.bust_width / 2 - (self.back_width + self.armscye_width + self.chest_width))
            > 1e-6
        ):
            raise ValueError(
                f"Bust width components do not match bust_width: "
                f"bust_width/2={self.bust_width / 2:.6f} != "
                f"back+armscye+chest="
                f"{self.back_width + self.armscye_width + self.chest_width:.6f}"
            )


@dataclass
class GarmentConfig:
    """Pure garment-design choices — independent of body measurements and fit.

    Attributes:
        length:                Modell-Länge (MoL) — finished garment length
                               (hem to nape).
        seam_allowance:        Nahtzugabe — seam allowance width added to all seams.
        hem_width:             Saumweite (SaW) — hem width (optional; used for
                               trousers).
        shoulder_gather:       Schulter-Weite — gather/ease added to the shoulder seam
                               length.  Lengthens the shoulder seam on both pieces so
                               fabric can be eased or gathered at the sleeve head.
        armscye_fit:           Controls how tightly the front armscye fits around the
                               upper arm.  Range 0–1 cm: 0 = regular fit, 1 = tight fit.
                               Shifts the front armscye shoulder point inward, reducing
                               the armhole circumference.
        waist_dart_back_tip:   Distance from the waist dart centre to its lower
                               (hem-side) tip on the back piece.  Range: 13–16 cm.
        waist_dart_front_tip:  Distance from the waist dart centre to its lower
                               (hem-side) tip on the front piece.
    """

    length: float  # MoL — Modell-Länge
    seam_allowance: float = 1 * CM
    hem_width: float | None = None  # SaW — Saumweite
    shoulder_gather: float = 1 * CM  # Schulter-Weite — shoulder seam gather
    armscye_fit: float = 0.0  # Armlochpassform — 0 regular, 1 tight
    waist_dart_back_tip: float = 16 * CM  # hAbI-Spitze — back waist dart lower tip
    waist_dart_front_tip: float = 12 * CM  # vAbI-Spitze — front waist dart lower tip

    def __post_init__(self) -> None:
        """Validate ``armscye_fit`` and ``waist_dart_back_tip`` are within permitted ranges."""
        if not (0.0 - 1e-9 <= self.armscye_fit <= 1.0 * CM + 1e-9):
            raise ValueError(
                f"armscye_fit={self.armscye_fit / CM:.2f} cm is outside the valid "
                f"range [0, 1] cm.  0 = regular fit, 1 cm = tight fit."
            )
        if not (13.0 * CM - 1e-9 <= self.waist_dart_back_tip <= 16.0 * CM + 1e-9):
            raise ValueError(
                f"waist_dart_back_tip={self.waist_dart_back_tip / CM:.2f} cm is "
                f"outside the valid range [13, 16] cm."
            )


@dataclass
class TrouserConfig(GarmentConfig):
    """Garment-design choices specific to trousers.

    Attributes:
        front_trouser_ease: Zugabe vordere Hosenbreite (ZuvHoB).
    """

    front_trouser_ease: float | None = None  # ZuvHoB — Zugabe vordere Hosenbreite


@dataclass
class WaistDistribution:
    """Result of the waist-dart hip_shortfall (Ausfallbetrag) calculation.

    All values are in the project's internal unit (mm).

    Attributes:
        front_waist_width: Distance from center-front to side-seam at waist level.
        back_waist_width:  Distance from side-seam to center-back at waist level.
        total_waist_width: Total waist width on the pattern (= front + back).
        hip_shortfall:     Waist excess = total_waist_width − waist_width / 2.
        side_seam_intake:  Side-seam take-in per side (clamped to 0–2 cm).
        front_dart_width:  Front waist dart intake (clamped to 1–3 cm).
        back_dart_width:   Back waist dart intake (clamped to 2–4 cm).
        remainder:         Undistributed excess after clamping
                           (0 if perfectly distributed).
    """

    front_waist_width: float  # vTaB — vordere Taillenbreite
    back_waist_width: float  # hTaB — hintere Taillenbreite
    total_waist_width: float  # TaB  — Taillenbreite gesamt
    hip_shortfall: float  # Ausfallbetrag
    side_seam_intake: float  # SaEinzug — Seitennaht-Einzug
    front_dart_width: float  # vAbI — vorderer Abnäher-Einzug
    back_dart_width: float  # hAbI — hinterer Abnäher-Einzug
    remainder: float


@dataclass
class HipDistribution:
    """Result of the hip excess / shortfall (Fehlbetrag) calculation.

    All values are in the project's internal unit (mm).

    Attributes:
        front_hip_width:  Distance from center-front to side-seam at hip level.
        back_hip_width:   Distance from side-seam to center-back at hip level.
        total_hip_width:  Total hip width on the pattern (= front + back).
        hip_shortfall:    Hip excess = total_hip_width − hip_width / 2.
    """

    front_hip_width: float  # vHüB — vordere Hüftbreite
    back_hip_width: float  # hHüB — hintere Hüftbreite
    total_hip_width: float  # HüB  — Hüftbreite gesamt
    hip_shortfall: float  # Fehlbetrag


def calculate_hip_distribution(
    meas: BlouseMeasurements,
    pt_hip_cf: Point,
    pt_hip_sf: Point,
    pt_hip_sb: Point,
    pt_hip_cb: Point,
) -> HipDistribution:
    """Calculate the hip excess / shortfall at the hip line.

    Args:
        meas:       Blouse measurements (ease already included).
        pt_hip_cf:  Intersection of center-front with hip line.
        pt_hip_sf:  Intersection of side-front with hip line.
        pt_hip_sb:  Intersection of side-back with hip line.
        pt_hip_cb:  Intersection of center-back with hip line.

    Returns:
        :class:`HipDistribution` with all computed values.
    """
    front_hip_width = pt_hip_cf.distance_to(pt_hip_sf)
    back_hip_width = pt_hip_sb.distance_to(pt_hip_cb)
    total_hip_width = front_hip_width + back_hip_width
    hip_shortfall = total_hip_width - meas.hip_width / 2

    return HipDistribution(
        front_hip_width=front_hip_width,
        back_hip_width=back_hip_width,
        total_hip_width=total_hip_width,
        hip_shortfall=hip_shortfall,
    )


def calculate_waist_distribution(
    meas: BlouseMeasurements,
    pt_waist_cf: Point,
    pt_waist_sf: Point,
    pt_waist_sb: Point,
    pt_waist_cb: Point,
) -> WaistDistribution:
    """Calculate how the waist hip_shortfall (Ausfallbetrag) is distributed to darts.

    Measures the pattern distances at the waist line, computes the total
    excess over the finished waist measurement, and splits it between the two
    side seams and the front / back waist darts using rule-based clamping.

    Args:
        meas:        Blouse measurements (ease already included).
        pt_waist_cf: Intersection of center-front with waist line.
        pt_waist_sf: Intersection of side-front with waist line.
        pt_waist_sb: Intersection of side-back with waist line.
        pt_waist_cb: Intersection of center-back with waist line.

    Returns:
        :class:`WaistDistribution` with all computed values.
    """
    front_waist_width = pt_waist_cf.distance_to(pt_waist_sf)
    back_waist_width = pt_waist_sb.distance_to(pt_waist_cb)
    total_waist_width = front_waist_width + back_waist_width
    hip_shortfall = total_waist_width - meas.waist_width / 2

    side_seam_intake = _clamp(hip_shortfall * _SN_FRACTION, 0.0, 2.0 * CM)
    rest = hip_shortfall - 2.0 * side_seam_intake
    rest_pos = max(0.0, rest)
    front_dart_width = _clamp(
        rest * _FRONT_FRACTION,
        min(1.0 * CM, rest_pos),
        min(3.0 * CM, rest_pos),
    )
    remaining_after_front = rest_pos - front_dart_width
    back_dart_width = _clamp(
        rest - front_dart_width,
        min(2.0 * CM, remaining_after_front),
        min(4.0 * CM, remaining_after_front),
    )
    remainder = max(0.0, rest - front_dart_width - back_dart_width)

    return WaistDistribution(
        front_waist_width=front_waist_width,
        back_waist_width=back_waist_width,
        total_waist_width=total_waist_width,
        hip_shortfall=hip_shortfall,
        side_seam_intake=side_seam_intake,
        front_dart_width=front_dart_width,
        back_dart_width=back_dart_width,
        remainder=remainder,
    )


def make_top_measurements(
    person: BalancedPerson,
    fit_class: FitClass,
) -> BlouseMeasurements:
    """Build ease-included top measurements from a balanced person and fit class.

    Args:
        person:    A :class:`~sewpat.person.BalancedPerson` — use
                   :meth:`~sewpat.person.PersonAnalyser.get_balanced_person`
                   to obtain one.
        fit_class: :class:`~sewpat.fitclass.FitClass` providing all ease values.
    """
    measurements = {k: v for k, v in person.person.__dict__.items() if v is not None}

    for fc_attr, body_key in _BODY_EASE_MAP.items():
        if body_key in measurements:
            measurements[body_key] += getattr(fit_class, fc_attr)

    measurements["bust_width"] = measurements["bust"] + fit_class.bust_width_ease
    measurements["waist_width"] = measurements["waist"] + fit_class.waist_ease
    measurements["hip_width"] = measurements["hip"] + fit_class.hip_ease

    measurements.pop("height", None)
    return BlouseMeasurements(**measurements)


def make_measurements_trouser(
    person: Person,
    ease: TrouserEase,
    balance: BalanceAdjustments | None = None,
) -> TrouserMeasurements:
    """Build ease-included trouser measurements.

    Args:
        person:  Body measurements.
        ease:    :class:`TrouserEase` with trouser-specific ease additions.
        balance: Optional front/back length corrections.
    """
    measurements = {k: v for k, v in person.__dict__.items() if v is not None}

    if ease.body_rise_ease and "body_rise" in measurements:
        measurements["body_rise"] += ease.body_rise_ease
    if ease.inseam_ease and "inseam" in measurements:
        measurements["inseam"] += ease.inseam_ease

    measurements["waist_width"] = measurements["waist"] + ease.waist_ease
    measurements["hip_width"] = measurements["hip"] + ease.hip_ease

    measurements.pop("height", None)

    if balance is not None:
        for key, val in balance.__dict__.items():
            if key in measurements:
                measurements[key] += val

    trouser_keys = [
        "waist",
        "hip",
        "hip_depth",
        "body_rise",
        "inseam",
        "waist_width",
        "hip_width",
    ]
    trouser_dict = {k: v for k, v in measurements.items() if k in trouser_keys}
    trouser_dict["gender"] = person.gender
    return TrouserMeasurements(**trouser_dict)
