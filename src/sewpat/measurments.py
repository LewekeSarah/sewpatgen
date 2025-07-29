from dataclasses import dataclass


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
        self.BrU = self.RüB + self.ArD + self.BrB + self.AlT


@dataclass
class ConstructionMeasurments:
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
    BrW: float
    TaW: float
    HüW: float


@dataclass
class ModelConfig:
    MoL: float
    BeckenAdjustment: float
