from dataclasses import dataclass

from sewpat.geometry import CM


@dataclass
class Person:
    KöH: float
    BrU: float
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


@dataclass
class Allowance:
    RüB: float
    ArD: float
    BrB: float
    AlT: float
    TaU: float
    HüU: float
    BrU: float = 0.0

    def __post_init__(self):
        self.BrU = 2 * (self.RüB + self.ArD + self.BrB)


def get_optimal_balance(BrU: float) -> float:
    if (BrU > 80 * CM) and (BrU <= 89 * CM):
        return 3.5 * CM
    else:
        raise NotImplementedError("Matching balance for given bustline is not yet implemented.")


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

    def __post_init__(self):
        if (self.VL - self.RüL) > get_optimal_balance(self.BrU):
            raise ValueError("VL and RüB are not properly balanced")


@dataclass
class BalanceAdjustements:
    RüL: float = 0.0
    VL: float = 0.0


@dataclass
class ModelConfig:
    MoL: float
    BeckenAdjustment: float


def make_measurements(
    person: Person,
    allowance: Allowance,
    balance: BalanceAdjustements = None
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
