from dataclasses import dataclass
from enum import Enum

from sewpat.geometry import CM



class Gender(Enum):
    male = "m"
    female = "f"


@dataclass
class Person:
    KöH: float
    BrU: float
    TaU: float
    HüU: float
    HüT: float
    BrT: float
    HlB: float
    BrPA: float
    SuB: float
    RüL: float
    VL: float
    SiH: float = 0. * CM
    SrH: float = 0. * CM
    RüB: float = None
    AlT: float = None
    ArD: float = None
    BrB: float = None
    gender: Gender = Gender.female

    def __post_init__(self):
        if (self.BrU > 60 * CM) and (self.BrU < 70 * CM):
            self.AlT = 0 if self.AlT is None else self.AlT
            self.ArD = 0 if self.ArD is None else self.ArD
            self.BrB = 0 if self.BrB is None else self.BrB
            self.RüB = 0 if self.RüB is None else self.RüB
            self.BrU = (self.RüB + self.ArD + self.BrB) * 2
            print("Warning: Only for Trousers, no tops")
        elif (self.BrU > 80 * CM) and (self.BrU <= 89 * CM):
            self.AlT = self.BrU / 10 + 11 * CM if self.AlT is None else self.AlT
            self.ArD = self.BrU / 8 - 1.5 * CM if self.ArD is None else self.ArD
            self.BrB = self.BrU / 4 - 4.0 * CM if self.BrB is None else self.BrB
            self.RüB = self.BrU / 8 + 5.5 * CM if self.RüB is None else self.RüB
        elif self.AlT is None or self.ArD is None or self.BrB is None:
            raise NotImplementedError(
                "Matching formula for given bustline is not yet implemented."
            )
        if self.BrU / 2 != (self.RüB + self.ArD + self.BrB):
            raise ValueError("Brustline measurements are not matching.")


@dataclass
class Allowance:
    RüB: float
    ArD: float
    BrB: float
    AlT: float
    TaU: float
    HüU: float
    BrU: float = 0.0
    SiH: float = 0.
    SrH: float = 0.

    def __post_init__(self):
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
class ConstructionMeasurments:
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
    SiH: float
    SrH: float
    vHoB: float = None  # Vorderhosenbreite
    gender: Gender = Gender.female

    def __post_init__(self):
        if self.gender == Gender.female:
            if (self.VL - self.RüL) > get_optimal_balance(self.BrU):
                raise ValueError("VL and RüB are not properly balanced")

        self.vHoB = -0.25 * self.HüW if self.vHoB is None else self.vHoB

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
) -> ConstructionMeasurments:
    measurements = {key: val for key, val in person.__dict__.items()}
    for key, val in allowance.__dict__.items():
        if key not in ["TaU", "BrU", "HüU"]:
            measurements[key] += val
    for perimeter, width in zip(["TaU", "BrU", "HüU"], ["TaW", "BrW", "HüW"]):
        measurements[width] = measurements[perimeter] + allowance.__getattribute__(
            perimeter
        )
    measurements.pop("KöH")

    if balance is not None:
        for key, val in balance.__dict__.items():
            measurements[key] += balance.__getattribute__(key)

    return ConstructionMeasurments(**measurements)
