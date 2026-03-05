"""Person related information required for pattern construction"""

import copy
from dataclasses import dataclass
from enum import Enum

from sewpat.units import CM


class Gender(Enum):
    """Some pattern have gender-specific adjustments"""

    male = "male"
    female = "female"
    boy = "boy"
    girl = "girl"
    baby = "baby"


@dataclass
class Person:
    BrU: float | None = None  # Brustumfang
    TaU: float | None = None  # Taillenumfang
    HüU: float | None = None  # Hüftumfang
    HüT: float | None = None  # Hüfttiefe
    BrT: float | None = None  # Brusttiefe
    HlB: float | None = None  # Halslochbreite
    BrPA: float | None = None  # Brustpunktabstand
    SuB: float | None = None  # Schulterbreite
    RüL: float | None = None  # Rückenlänge
    VL: float | None = None  # Vorderlänge
    SiH: float | None = None  # Sitzhöhe
    SrH: float | None = None  # Schritthöhe
    RüB: float | None = None  # Rückenbreite
    AlT: float | None = None  # Armlochtiefe
    ArD: float | None = None  # Armdurchmesser
    BrB: float | None = None  # Brustbreite
    KöH: float | None = None  # Körperhöhe
    gender: Gender = Gender.female  # Geschlecht


@dataclass
class BalanceAdjustments:
    RüL: float = 0.0
    VL: float = 0.0


class PersonAnalyser:
    def __init__(
        self, person: Person, balance_adjustments: BalanceAdjustments | None = None
    ):
        self.person = person
        self.person_balanced: Person | None = None
        self.balance = balance_adjustments
        self.optimal_balance = self.get_optimal_balance()
        self.calculate_measurements()
        self.balance_person()

    def _set_alt(self):
        if (self.person.BrU > 80 * CM) and (self.person.BrU <= 89 * CM):
            self.person.AlT = (
                self.person.BrU / 10 + 11 * CM
                if self.person.AlT is None
                else self.person.AlT
            )
        if self.person.AlT is None:
            raise NotImplementedError(
                "Matching AlT formula for given bustline is not yet implemented."
            )

    def _set_ard(self):
        if (self.person.BrU > 80 * CM) and (self.person.BrU <= 89 * CM):
            self.person.ArD = (
                self.person.BrU / 8 - 1.5 * CM
                if self.person.ArD is None
                else self.person.ArD
            )
        if self.person.ArD is None:
            raise NotImplementedError(
                "Matching ArD formula for given bustline is not yet implemented."
            )

    def _set_brb(self):
        if (self.person.BrU > 80 * CM) and (self.person.BrU <= 89 * CM):
            self.person.BrB = (
                self.person.BrU / 4 - 4.0 * CM
                if self.person.BrB is None
                else self.person.BrB
            )
        if self.person.BrB is None:
            raise NotImplementedError(
                "Matching BrB formula for given bustline is not yet implemented."
            )

    def _set_rüb(self):
        if (self.person.BrU > 80 * CM) and (self.person.BrU <= 89 * CM):
            self.person.RüB = (
                self.person.BrU / 8 + 5.5 * CM
                if self.person.RüB is None
                else self.person.RüB
            )
        if self.person.RüB is None:
            raise NotImplementedError(
                "Matching formula for given bustline is not yet implemented."
            )

    def calculate_measurements(self):
        if self.person.BrU is not None:
            self._set_alt()
            self._set_ard()
            self._set_brb()
            self._set_rüb()

    def balance_person(self):
        person_balanced = copy.deepcopy(self.person)
        if self.balance is not None:
            for key, val in self.balance.__dict__.items():
                person_balanced.__setattr__(
                    key, person_balanced.__getattribute__(key) + val
                )
        if person_balanced.gender == Gender.female:
            if (person_balanced.VL - person_balanced.RüL) > self.optimal_balance:
                raise ValueError("VL and RüB are not properly balanced")
            else:
                self.person_balanced = person_balanced

    def get_balanced_person(self) -> Person:
        return self.person_balanced

    def get_optimal_balance(self) -> float:
        if (self.person.BrU > 80 * CM) and (self.person.BrU <= 89 * CM):
            return 3.5 * CM
        else:
            raise NotImplementedError(
                "Matching balance for given bustline is not yet implemented."
            )
