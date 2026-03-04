import warnings
from dataclasses import dataclass

from sewpat.person import BalanceAdjustments, Gender, Person, PersonAnalyser
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


# Fractions used by calculate_waist_distribution().
_SN_FRACTION: float = 0.25    # fraction of Ausfallbetrag → each side seam
_FRONT_FRACTION: float = 0.40  # fraction of residual → front waist dart


@dataclass
class Allowance:
    RüB: float | None = None
    ArD: float | None = None
    BrB: float | None = None
    AlT: float | None = None
    TaU: float | None = None
    HüU: float | None = None
    BrU: float | None = None
    SiH: float | None = None
    SrH: float | None = None

    def __post_init__(self):
        if (self.RüB is not None) and (self.ArD is not None) and (self.BrB is not None):
            self.BrU = 2 * (self.RüB + self.ArD + self.BrB)


@dataclass
class TrouserMeasurements:
    TaU: float
    HüU: float
    SiH: float
    TaW: float
    HüW: float
    HüT: float | None = None
    SrH: float | None = None
    sTaH: float | None = None
    KnH: float | None = None  # Kniehöhe
    vHoB: float | None = None  # Vorderhosenbreite
    gender: Gender = Gender.female

    def __post_init__(self):
        self.vHoB = 0.25 * self.HüW if self.vHoB is None else self.vHoB
        if self.gender in [Gender.boy, Gender.girl]:
            self.KnH = 0.5 * self.SrH if self.KnH is None else self.KnH
            self.sTaH = self.SrH + self.SiH
        elif self.gender == Gender.female:
            self.KnH = 0.5 * self.SrH - self.SrH / 10 if self.KnH is None else self.KnH
            self.SrH = self.sTaH - self.SrH
        if self.KnH is None:
            raise NotImplementedError("Kniehöhe is missing.")


@dataclass
class BlouseMeasurements:
    BrU: float  # bustline
    TaU: float
    HüU: float
    HüT: float
    BrT: float
    HlB: float
    BrPA: float
    SuB: float
    RüL: float
    VL: float
    BrW: float
    TaW: float
    HüW: float
    AlT: float
    RüB: float
    ArD: float
    BrB: float
    gender: Gender = Gender.female

    def __post_init__(self):
        if self.BrW / 2 != (self.RüB + self.ArD + self.BrB):
            raise ValueError("Brustline measurements are not matching.")


@dataclass
class ModelConfig:
    MoL: float
    BeckenAdjustment: float | None = None
    ZuvHoB: float | None = None
    SaW: float | None = None  # Saumweite
    seam_allowance: float = 1 * CM  # Nahtzugabe
    ZuBrA: float | None = None  # Zugabe Brustpunktabstand


@dataclass
class WaistDistribution:
    """Result of the waist-dart excess (Ausfallbetrag) calculation.

    All values are in the project's internal unit (mm).

    Attributes:
        vTaB:          Distance from center-front to side-seam at waist level.
        hTaB:          Distance from side-seam to center-back at waist level.
        TaB:           Total waist width on the pattern (= vTaB + hTaB).
        Ausfallbetrag: Waist excess = TaB − TaW / 2 to be distributed as darts.
        SaEinzug:      Side-seam take-in per side (clamped to 0–2 cm).
        vAbI:          Front waist dart intake (clamped to 1–3 cm).
        hAbI:          Back waist dart intake (clamped to 2–4 cm).
        remainder:     Undistributed excess after clamping (0 if perfectly distributed).
    """

    vTaB: float
    hTaB: float
    TaB: float
    Ausfallbetrag: float
    SaEinzug: float
    vAbI: float
    hAbI: float
    remainder: float


@dataclass
class HipDistribution:
    """Result of the hip excess (Fehlbetrag) calculation.

    All values are in the project's internal unit (mm).

    Attributes:
        vHüB:         Distance from center-front to side-seam at hip level.
        hHüB:         Distance from side-seam to center-back at hip level.
        HüB:          Total hip width on the pattern (= vHüB + hHüB).
        Fehlbetrag:   Hip excess = HüB − HüW / 2.
                      Positive → pattern is wider than the finished hip measurement
                      (excess needs to be taken in or used for ease).
                      Negative → pattern is narrower than the finished hip
                      measurement (additional width required).
    """

    vHüB: float
    hHüB: float
    HüB: float
    Fehlbetrag: float


def calculate_hip_distribution(
    meas: "BlouseMeasurements",
    pt_hip_cf: "Point",
    pt_hip_sf: "Point",
    pt_hip_sb: "Point",
    pt_hip_cb: "Point",
) -> HipDistribution:
    """Calculate the hip excess / shortfall (Fehlbetrag) at the hip line.

    Measures the pattern distances at the hip line and computes the difference
    from the finished hip measurement ``HüW``.

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

    vHüB = Segment(pt_hip_cf, pt_hip_sf).length
    hHüB = Segment(pt_hip_sb, pt_hip_cb).length
    HüB = vHüB + hHüB
    Fehlbetrag = HüB - meas.HüW / 2

    return HipDistribution(
        vHüB=vHüB,
        hHüB=hHüB,
        HüB=HüB,
        Fehlbetrag=Fehlbetrag,
    )


def calculate_waist_distribution(
    meas: "BlouseMeasurements",
    pt_waist_cf: "Point",
    pt_waist_sf: "Point",
    pt_waist_sb: "Point",
    pt_waist_cb: "Point",
) -> WaistDistribution:
    """Calculate how the waist excess (Ausfallbetrag) is distributed to darts.

    Measures the pattern distances at the waist line, computes the total
    excess over the finished waist measurement ``TaW``, and splits it between
    the two side seams and the front / back waist darts using rule-based
    clamping.

    Args:
        meas:        Blouse measurements (ease already included).
        pt_waist_cf: Intersection of center-front with waist line.
        pt_waist_sf: Intersection of side-front with waist line.
        pt_waist_sb: Intersection of side-back with waist line.
        pt_waist_cb: Intersection of center-back with waist line (= pt6).

    Returns:
        :class:`WaistDistribution` with all computed values.

    Raises:
        warnings.warn: If clamping leaves undistributed excess > 0.5 cm.
    """
    # Import here to avoid a circular import at module level.
    from sewpat.geometry import Segment  # noqa: PLC0415

    vTaB = Segment(pt_waist_cf, pt_waist_sf).length
    hTaB = Segment(pt_waist_sb, pt_waist_cb).length
    TaB = vTaB + hTaB
    Ausfallbetrag = TaB - meas.TaW / 2

    # Distribute: first to side seams (each side), then to back and front darts.
    SaEinzug = _clamp(Ausfallbetrag * _SN_FRACTION, 0.0, 2.0 * CM)
    rest = Ausfallbetrag - 2.0 * SaEinzug
    # Clamp dart intakes within their allowed ranges, but never exceed the
    # available rest so that 2·SaEinzug + vAbI + hAbI + remainder == Ausfallbetrag.
    rest_pos = max(0.0, rest)
    vAbI = _clamp(rest * _FRONT_FRACTION, min(1.0 * CM, rest_pos), min(3.0 * CM, rest_pos))
    remaining_after_v = rest_pos - vAbI
    hAbI = _clamp(rest - vAbI, min(2.0 * CM, remaining_after_v), min(4.0 * CM, remaining_after_v))
    remainder = max(0.0, rest - vAbI - hAbI)

    if remainder > 0.5 * CM:
        warnings.warn(
            f"Ausfallbetrag nicht vollständig verteilt: "
            f"{remainder / CM:.1f} cm Rest nach Clamping.",
            stacklevel=2,
        )

    return WaistDistribution(
        vTaB=vTaB,
        hTaB=hTaB,
        TaB=TaB,
        Ausfallbetrag=Ausfallbetrag,
        SaEinzug=SaEinzug,
        vAbI=vAbI,
        hAbI=hAbI,
        remainder=remainder,
    )


def make_blouse_measurements(
    person: Person, allowance: Allowance, balance: BalanceAdjustments
) -> BlouseMeasurements:
    person = PersonAnalyser(person, balance).get_balanced_person()

    measurements = {key: val for key, val in person.__dict__.items() if val is not None}
    allowances = {
        key: val for key, val in allowance.__dict__.items() if val is not None
    }
    width_instead_update = {"TaU", "BrU", "HüU"}
    for key in (
        set(measurements.keys())
        .intersection(allowances.keys())
        .difference(width_instead_update)
    ):
        measurements[key] += allowances[key]
    for perimeter, width in zip(["TaU", "BrU", "HüU"], ["TaW", "BrW", "HüW"]):
        measurements[width] = measurements[perimeter] + getattr(allowance, perimeter)
    measurements.pop("KöH")

    return BlouseMeasurements(**measurements)


def make_measurements_trouser(
    person: Person, allowance: Allowance, balance: BalanceAdjustments = None
) -> TrouserMeasurements:
    measurements = {key: val for key, val in person.__dict__.items() if val is not None}
    allowances = {
        key: val for key, val in allowance.__dict__.items() if val is not None
    }
    width_instead_update = {"TaU", "HüU"}
    for key in (
        set(measurements.keys())
        .intersection(allowances.keys())
        .difference(width_instead_update)
    ):
        measurements[key] += allowances[key]
    for perimeter, width in zip(["TaU", "HüU"], ["TaW", "HüW"]):
        measurements[width] = measurements[perimeter]
        if perimeter in allowances.keys():
            measurements[width] += allowances[perimeter]
    measurements.pop("KöH")

    if balance is not None:
        for key, val in balance.__dict__.items():
            measurements[key] += getattr(balance, key)

    trouser_keys = ["TaU", "HüU", "HüT", "SiH", "SrH", "TaW", "HüW"]
    trouser_dict = {
        key: val for key, val in measurements.items() if key in trouser_keys
    }
    trouser_dict["gender"] = person.gender
    return TrouserMeasurements(**trouser_dict)
