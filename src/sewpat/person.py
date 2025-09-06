""" Person related information required for pattern construction """
from dataclasses import dataclass
from enum import Enum

from sewpat.geometry import CM


class Gender(Enum):
    """ Some pattern have gender-specific adjustments"""
    male = "m"
    female = "f"


@dataclass
class Person:
    BrU: float = None  # Brustumfang
    TaU: float = None  # Taillenumfang
    HüU: float = None  # Hüftumfang
    HüT: float = None  # Hüfttiefe
    BrT: float = None  # Brusttiefe
    HlB: float = None  # Halslochbreite
    BrPA: float = None  # Brustpunktabstand
    SuB: float = None  # Schulterbreite
    RüL: float = None  # Rückenlänge
    VL: float = None  # Vorderlänge
    SiH: float = None  # Sitzhöhe
    SrH: float = None  # Schritthöhe
    RüB: float = None  # Rückenbreite
    AlT: float = None  # Armlochtiefe
    ArD: float = None  # Armdurchmesser
    BrB: float = None  # Brustbreite
    KöH: float = None  # Körperhöhe
    gender: Gender = Gender.female  # Geschlecht

    def __post_init__(self):
        if (self.BrU > 60 * CM) and (self.BrU < 70 * CM):
            if (self.RüB is not None) & (self.ArD is not None) & (self.BrB is not None):
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
        if (self.BrU is not None) & (self.RüB is not None) & (self.ArD is not None) & (self.BrB is not None):
            if self.BrU / 2 != (self.RüB + self.ArD + self.BrB):
                raise ValueError("Brustline measurements are not matching.")
