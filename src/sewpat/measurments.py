from dataclasses import dataclass

from sewpat.geometry import CM
from sewpat.person import Gender, Person, BalanceAdjustments, PersonAnalyser


@dataclass
class Allowance:
    RüB: float = None
    ArD: float = None
    BrB: float = None
    AlT: float = None
    TaU: float = None
    HüU: float = None
    BrU: float = None
    SiH: float = None
    SrH: float = None

    def __post_init__(self):
        if (self.RüB is not None) & (self.ArD is not None) & (self.BrB is not None):
            self.BrU = 2 * (self.RüB + self.ArD + self.BrB)


@dataclass
class TrouserMeasurements:
    TaU: float
    HüU: float
    HüT: float
    SiH: float
    TaW: float
    HüW: float
    SrH: float = None
    sTaH: float = None
    KnH: float = None  # Kniehöhe
    vHoB: float = None  # Vorderhosenbreite
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
    BeckenAdjustment: float = None
    ZuvHoB: float = None


def make_blouse_measurements(
    person: Person, allowance: Allowance, balance: BalanceAdjustments
) -> BlouseMeasurements:
    person = PersonAnalyser(person, balance).get_balanced_person()

    measurements = {key: val for key, val in person.__dict__.items() if val is not None}
    allowances = {key: val for key, val in allowance.__dict__.items() if val is not None}
    width_instead_update = {"TaU", "BrU", "HüU"}
    for key in set(measurements.keys()).intersection(allowances.keys()).difference(width_instead_update):
        measurements[key] += allowances[key]
    for perimeter, width in zip(["TaU", "BrU", "HüU"], ["TaW", "BrW", "HüW"]):
        measurements[width] = measurements[perimeter] + allowance.__getattribute__(
            perimeter
        )
    measurements.pop("KöH")

    return BlouseMeasurements(**measurements)


def make_measurements_trouser(
    person: Person, allowance: Allowance, balance: BalanceAdjustments = None
) -> TrouserMeasurements:
    measurements = {key: val for key, val in person.__dict__.items() if val is not None}
    allowances = {key: val for key, val in allowance.__dict__.items() if val is not None}
    width_instead_update = {"TaU", "HüU"}
    for key in set(measurements.keys()).intersection(allowances.keys()).difference(width_instead_update):
        measurements[key] += allowances[key]
    for perimeter, width in zip(["TaU", "HüU"], ["TaW", "HüW"]):
        measurements[width] = measurements[perimeter]
        if perimeter in allowances.keys():
            measurements[width] += allowances[key]
    measurements.pop("KöH")

    if balance is not None:
        for key, val in balance.__dict__.items():
            measurements[key] += balance.__getattribute__(key)

    return TrouserMeasurements(
        **{
            "TaU": measurements["TaU"],
            "HüU": measurements["HüU"],
            "HüT": measurements["HüT"],
            "SiH": measurements["SiH"],
            "SrH": measurements["SrH"],
            "TaW": measurements["TaW"],
            "HüW": measurements["HüW"],
            "gender": person.gender,}
    )
