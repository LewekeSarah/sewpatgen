from dataclasses import dataclass
from typing import TYPE_CHECKING

from sewpat.person import BalanceAdjustments, Gender, Person, PersonalAdjustments, PersonAnalyser
from sewpat.units import CM

if TYPE_CHECKING:
    from sewpat.fitclass import FitClass
    from sewpat.geometry import Point

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


# Fractions used by calculate_waist_distribution().
_SN_FRACTION: float = 0.25    # fraction of hip_shortfall → each side seam
_FRONT_FRACTION: float = 0.40  # fraction of residual → front waist dart


@dataclass
class Allowance:
    back_width_ease: float | None = None      # RüB — Rückenbreite-Zugabe
    armscye_width_ease: float | None = None   # ArD — Armdurchmesser-Zugabe
    chest_width_ease: float | None = None     # BrB — Brustbreite-Zugabe
    armscye_depth_ease: float | None = None   # AlT — Armlochtiefe-Zugabe
    waist_ease: float | None = None           # TaU — Taillenumfang-Zugabe
    hip_ease: float | None = None             # HüU — Hüftumfang-Zugabe
    bust_ease: float | None = None            # BrU — Brustumfang-Zugabe (derived)
    body_rise_ease: float | None = None       # SiH — Sitzhöhe-Zugabe
    inseam_ease: float | None = None          # SrH — Schritthöhe-Zugabe

    def __post_init__(self):
        if (
            self.back_width_ease is not None
            and self.armscye_width_ease is not None
            and self.chest_width_ease is not None
        ):
            self.bust_ease = 2 * (
                self.back_width_ease + self.armscye_width_ease + self.chest_width_ease
            )

    @classmethod
    def from_fit_class(cls, fc: "FitClass") -> "Allowance":
        """Derive standard allowances from a :class:`~sewpat.fitclass.FitClass`."""
        return cls(
            back_width_ease=fc.resolved_back_width_ease,
            armscye_width_ease=fc.resolved_armscye_width_ease,
            chest_width_ease=fc.resolved_chest_width_ease,
            armscye_depth_ease=fc.resolved_armscye_depth_ease,
            waist_ease=fc.resolved_waist_ease,
            hip_ease=fc.resolved_hip_ease,
        )


@dataclass
class TrouserMeasurements:
    waist: float          # TaU — Taillenumfang
    hip: float            # HüU — Hüftumfang
    body_rise: float      # SiH — Sitzhöhe
    waist_width: float    # TaW — Taillenweite fertig
    hip_width: float      # HüW — Hüftweite fertig
    hip_depth: float | None = None   # HüT — Hüfttiefe
    inseam: float | None = None      # SrH — Schritthöhe
    sTaH: float | None = None
    knee_height: float | None = None       # Kniehöhe
    front_trouser_width: float | None = None  # vHoB — Vorderhosenbreite
    gender: Gender = Gender.female

    def __post_init__(self):
        self.front_trouser_width = (
            0.25 * self.hip_width if self.front_trouser_width is None
            else self.front_trouser_width
        )
        if self.gender in [Gender.boy, Gender.girl]:
            self.knee_height = 0.5 * self.inseam if self.knee_height is None else self.knee_height
            self.sTaH = self.inseam + self.body_rise
        elif self.gender == Gender.female:
            self.knee_height = (
                0.5 * self.inseam - self.inseam / 10 if self.knee_height is None
                else self.knee_height
            )
            self.inseam = self.sTaH - self.inseam
        if self.knee_height is None:
            raise NotImplementedError("knee_height is missing.")


@dataclass
class BlouseMeasurements:
    bust: float             # BrU — Brustumfang
    waist: float            # TaU — Taillenumfang
    hip: float              # HüU — Hüftumfang
    hip_depth: float        # HüT — Hüfttiefe
    bust_depth: float       # BrT — Brusttiefe
    neck_size: float        # HlB — Halslochbreite
    bust_span: float        # BrPA — Brustpunktabstand
    shoulder_width: float   # SuB — Schulterbreite
    back_length: float      # RüL — Rückenlänge
    front_length: float     # VL  — Vorderlänge
    bust_width: float       # BrW — Brustbreite fertig (half-width)
    waist_width: float      # TaW — Taillenweite fertig (half-width)
    hip_width: float        # HüW — Hüftweite fertig (half-width)
    armscye_depth: float    # AlT — Armlochtiefe
    back_width: float       # RüB — Rückenbreite
    armscye_width: float    # ArD — Armdurchmesser
    chest_width: float      # BrB — Brustbreite
    gender: Gender = Gender.female

    def __post_init__(self):
        if abs(self.bust_width / 2 - (self.back_width + self.armscye_width + self.chest_width)) > 1e-6:
            raise ValueError(
                f"Bust width components do not match bust_width: "
                f"bust_width/2={self.bust_width/2:.6f} != "
                f"back+armscye+chest={self.back_width+self.armscye_width+self.chest_width:.6f}"
            )


@dataclass(frozen=True)
class GarmentConfig:
    """Pure garment-design choices — independent of body measurements and fit.

    Attributes:
        length:          Modell-Länge (MoL) — finished garment length (hem to nape).
        seam_allowance:  Nahtzugabe — seam allowance width added to all seams.
        hem_width:       Saumweite (SaW) — hem width (optional; used for trousers).
    """
    length: float                        # MoL — Modell-Länge
    seam_allowance: float = 1 * CM
    hem_width: float | None = None       # SaW — Saumweite


@dataclass(frozen=True)
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
        remainder:         Undistributed excess after clamping (0 if perfectly distributed).
    """

    front_waist_width: float   # vTaB — vordere Taillenbreite
    back_waist_width: float    # hTaB — hintere Taillenbreite
    total_waist_width: float   # TaB  — Taillenbreite gesamt
    hip_shortfall: float       # Ausfallbetrag
    side_seam_intake: float    # SaEinzug — Seitennaht-Einzug
    front_dart_width: float    # vAbI — vorderer Abnäher-Einzug
    back_dart_width: float     # hAbI — hinterer Abnäher-Einzug
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

    front_hip_width: float   # vHüB — vordere Hüftbreite
    back_hip_width: float    # hHüB — hintere Hüftbreite
    total_hip_width: float   # HüB  — Hüftbreite gesamt
    hip_shortfall: float     # Fehlbetrag


def calculate_hip_distribution(
    meas: "BlouseMeasurements",
    pt_hip_cf: "Point",
    pt_hip_sf: "Point",
    pt_hip_sb: "Point",
    pt_hip_cb: "Point",
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
    from sewpat.geometry import Segment  # noqa: PLC0415

    front_hip_width = Segment(pt_hip_cf, pt_hip_sf).length
    back_hip_width  = Segment(pt_hip_sb, pt_hip_cb).length
    total_hip_width = front_hip_width + back_hip_width
    hip_shortfall   = total_hip_width - meas.hip_width / 2

    return HipDistribution(
        front_hip_width=front_hip_width,
        back_hip_width=back_hip_width,
        total_hip_width=total_hip_width,
        hip_shortfall=hip_shortfall,
    )


def calculate_waist_distribution(
    meas: "BlouseMeasurements",
    pt_waist_cf: "Point",
    pt_waist_sf: "Point",
    pt_waist_sb: "Point",
    pt_waist_cb: "Point",
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
    from sewpat.geometry import Segment  # noqa: PLC0415

    front_waist_width = Segment(pt_waist_cf, pt_waist_sf).length
    back_waist_width  = Segment(pt_waist_sb, pt_waist_cb).length
    total_waist_width = front_waist_width + back_waist_width
    hip_shortfall     = total_waist_width - meas.waist_width / 2

    side_seam_intake = _clamp(hip_shortfall * _SN_FRACTION, 0.0, 2.0 * CM)
    rest = hip_shortfall - 2.0 * side_seam_intake
    rest_pos = max(0.0, rest)
    front_dart_width = _clamp(
        rest * _FRONT_FRACTION,
        min(1.0 * CM, rest_pos), min(3.0 * CM, rest_pos),
    )
    remaining_after_front = rest_pos - front_dart_width
    back_dart_width = _clamp(
        rest - front_dart_width,
        min(2.0 * CM, remaining_after_front), min(4.0 * CM, remaining_after_front),
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


def make_blouse_measurements(
    person: Person,
    fit_class_or_allowance: "FitClass | Allowance | None" = None,
    adjustments: "PersonalAdjustments | None" = None,
) -> "BlouseMeasurements":
    """Build ease-included blouse measurements from body measurements and fit.

    Args:
        person: Body measurements.
        fit_class_or_allowance: :class:`~sewpat.fitclass.FitClass` or explicit
            :class:`Allowance`.
        adjustments: Personal body-deviation corrections.
    """
    from sewpat.fitclass import FitClass  # local import to avoid circularity

    if isinstance(fit_class_or_allowance, FitClass):
        resolved_allowance = Allowance.from_fit_class(fit_class_or_allowance)
    elif fit_class_or_allowance is not None:
        resolved_allowance = fit_class_or_allowance
    else:
        raise TypeError("Provide a FitClass or Allowance as the second argument.")

    resolved_balance = (
        adjustments.balance if isinstance(adjustments, PersonalAdjustments)
        else BalanceAdjustments()
    )

    person = PersonAnalyser(person, resolved_balance).get_balanced_person()

    measurements = {k: v for k, v in person.__dict__.items() if v is not None}
    allowances   = {k: v for k, v in resolved_allowance.__dict__.items() if v is not None}

    # Map allowance field name → body measurement field name for additive ease.
    # Circumference fields (bust/waist/hip) are handled separately below.
    _body_ease_map = {
        "back_width_ease":    "back_width",
        "armscye_width_ease": "armscye_width",
        "chest_width_ease":   "chest_width",
        "armscye_depth_ease": "armscye_depth",
        "body_rise_ease":     "body_rise",
        "inseam_ease":        "inseam",
    }
    for ease_key, body_key in _body_ease_map.items():
        if ease_key in allowances and body_key in measurements:
            measurements[body_key] += allowances[ease_key]

    # Finished widths: body circumference + full-circumference ease
    _circ_ease_map = {"waist": "waist_ease", "bust": "bust_ease", "hip": "hip_ease"}
    _circ_finished = {"waist": "waist_width", "bust": "bust_width", "hip": "hip_width"}
    for body, ease_key in _circ_ease_map.items():
        measurements[_circ_finished[body]] = measurements[body] + allowances.get(ease_key, 0.0)

    measurements.pop("height", None)

    return BlouseMeasurements(**measurements)


def make_measurements_trouser(
    person: Person,
    allowance: Allowance,
    balance: BalanceAdjustments = None,
) -> TrouserMeasurements:
    """Build ease-included trouser measurements."""
    measurements = {k: v for k, v in person.__dict__.items() if v is not None}
    allowances   = {k: v for k, v in allowance.__dict__.items() if v is not None}

    _body_ease_map = {
        "back_width_ease":    "back_width",
        "armscye_width_ease": "armscye_width",
        "chest_width_ease":   "chest_width",
        "armscye_depth_ease": "armscye_depth",
        "body_rise_ease":     "body_rise",
        "inseam_ease":        "inseam",
    }
    for ease_key, body_key in _body_ease_map.items():
        if ease_key in allowances and body_key in measurements:
            measurements[body_key] += allowances[ease_key]

    for body, finished in [("waist", "waist_width"), ("hip", "hip_width")]:
        _ease_map = {"waist": "waist_ease", "hip": "hip_ease"}
        measurements[finished] = measurements[body] + allowances.get(_ease_map[body], 0.0)

    measurements.pop("height", None)

    if balance is not None:
        for key, val in balance.__dict__.items():
            measurements[key] += getattr(balance, key)

    trouser_keys = ["waist", "hip", "hip_depth", "body_rise", "inseam", "waist_width", "hip_width"]
    trouser_dict = {k: v for k, v in measurements.items() if k in trouser_keys}
    trouser_dict["gender"] = person.gender
    return TrouserMeasurements(**trouser_dict)
