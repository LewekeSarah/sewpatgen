from dataclasses import dataclass

from sewpat.person import BalanceAdjustments, Gender, Person, PersonAnalyser
from sewpat.units import CM


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
