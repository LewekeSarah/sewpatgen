from dataclasses import dataclass

from sewpat.geometry import CM
from sewpat.person import Gender, Person


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


def get_optimal_balance(BrU: float) -> float:
    if (BrU > 80 * CM) and (BrU <= 89 * CM):
        return 3.5 * CM
    elif (BrU > 60 * CM) and (BrU < 70 * CM):
        return 3.5 * CM
    else:
        raise NotImplementedError(
            "Matching balance for given bustline is not yet implemented."
        )


@dataclass
class TrouserMeasurements:
    TaU: float
    HüU: float
    HüT: float
    SiH: float
    SrH: float
    TaW: float
    HüW: float
    vHoB: float = None  # Vorderhosenbreite
    gender: Gender = Gender.female

    def __post_init__(self):
        self.vHoB = -0.25 * self.HüW if self.vHoB is None else self.vHoB


@dataclass
class BlouseMeasurements:
    BrU: float  # bustline
    TaU: float
    HüU: float
    AlT: float
    HüT: float
    BrT: float
    HlB: float
    RüB: float
    ArD: float
    BrB: float
    BrPA: float
    SuB: float
    RüL: float
    VL: float
    BrW: float
    TaW: float
    HüW: float
    gender: Gender = Gender.female

    def __post_init__(self):
        if self.gender == Gender.female:
            if (self.VL - self.RüL) > get_optimal_balance(self.BrU):
                raise ValueError("VL and RüB are not properly balanced")


@dataclass
class BalanceAdjustements:
    RüL: float = 0.0
    VL: float = 0.0


@dataclass
class ModelConfig:
    MoL: float
    BeckenAdjustment: float = None
    ZuvHoB: float = None


def make_measurements(
    person: Person, allowance: Allowance, balance: BalanceAdjustements = None
) -> BlouseMeasurements:
    measurements = {key: val for key, val in person.__dict__.items() if val is not None}
    for key, val in allowance.__dict__.items():
        if (val is not None) and (key not in ["TaU", "BrU", "HüU"]):
            measurements[key] += val
    for perimeter, width in zip(["TaU", "BrU", "HüU"], ["TaW", "BrW", "HüW"]):
        measurements[width] = measurements[perimeter] + allowance.__getattribute__(
            perimeter
        )
    measurements.pop("KöH")

    if balance is not None:
        for key, val in balance.__dict__.items():
            measurements[key] += balance.__getattribute__(key)

    return BlouseMeasurements(**measurements)


def make_measurements_trouser(
    person: Person, allowance: Allowance, balance: BalanceAdjustements = None
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
