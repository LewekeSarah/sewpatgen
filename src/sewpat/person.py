"""Person related information required for pattern construction"""

import copy
from dataclasses import dataclass, field
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
    bust: float | None = None            # BrU — Brustumfang
    waist: float | None = None           # TaU — Taillenumfang
    hip: float | None = None             # HüU — Hüftumfang
    hip_depth: float | None = None       # HüT — Hüfttiefe
    bust_depth: float | None = None      # BrT — Brusttiefe
    neck_size: float | None = None       # HlB — Halslochbreite
    bust_span: float | None = None       # BrPA — Brustpunktabstand
    shoulder_width: float | None = None  # SuB — Schulterbreite
    back_length: float | None = None     # RüL — Rückenlänge
    front_length: float | None = None    # VL  — Vorderlänge (VL2 variant: balancing, future feature)
    body_rise: float | None = None       # SiH — Sitzhöhe
    inseam: float | None = None          # SrH — Schritthöhe
    back_width: float | None = None      # RüB — Rückenbreite
    armscye_depth: float | None = None   # AlT — Armlochtiefe
    armscye_width: float | None = None   # ArD — Armdurchmesser
    chest_width: float | None = None     # BrB — Brustbreite
    height: float | None = None          # KöH — Körperhöhe
    gender: Gender = Gender.female       # Geschlecht


@dataclass
class BalanceAdjustments:
    back_length: float = 0.0   # RüL — Rückenlänge
    front_length: float = 0.0  # VL  — Vorderlänge


@dataclass(frozen=True)
class PersonalAdjustments:
    """Body-deviation corrections for non-standard figures.

    These are individual corrections applied on top of standard block
    construction.  Two people with the same measurements and
    :class:`~sewpat.fitclass.FitClass` may still need different adjustments.

    Attributes:
        hip_offset: Horizontal hip offset — shifts the hip-adjustment
            vertical grid line outward (positive) or inward (negative).
            (BeckenAdjustment — Becken-Korrektur)
        balance: Front/back length balance corrections.
    """

    hip_offset: float = 2.0  # BeckenAdjustment — Becken-Korrektur
    balance: BalanceAdjustments = field(default_factory=BalanceAdjustments)


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

    def _set_armscye_depth(self):
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.armscye_depth = (
                self.person.bust / 10 + 11 * CM
                if self.person.armscye_depth is None
                else self.person.armscye_depth
            )
        if self.person.armscye_depth is None:
            raise NotImplementedError(
                "Matching armscye_depth formula for given bustline is not yet implemented."
            )

    def _set_armscye_width(self):
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.armscye_width = (
                self.person.bust / 8 - 1.5 * CM
                if self.person.armscye_width is None
                else self.person.armscye_width
            )
        if self.person.armscye_width is None:
            raise NotImplementedError(
                "Matching armscye_width formula for given bustline is not yet implemented."
            )

    def _set_chest_width(self):
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.chest_width = (
                self.person.bust / 4 - 4.0 * CM
                if self.person.chest_width is None
                else self.person.chest_width
            )
        if self.person.chest_width is None:
            raise NotImplementedError(
                "Matching chest_width formula for given bustline is not yet implemented."
            )

    def _set_back_width(self):
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.back_width = (
                self.person.bust / 8 + 5.5 * CM
                if self.person.back_width is None
                else self.person.back_width
            )
        if self.person.back_width is None:
            raise NotImplementedError(
                "Matching formula for given bustline is not yet implemented."
            )

    def calculate_measurements(self):
        if self.person.bust is not None:
            self._set_armscye_depth()
            self._set_armscye_width()
            self._set_chest_width()
            self._set_back_width()

    def balance_person(self):
        person_balanced = copy.deepcopy(self.person)
        if self.balance is not None:
            for key, val in self.balance.__dict__.items():
                person_balanced.__setattr__(
                    key, person_balanced.__getattribute__(key) + val
                )
        if person_balanced.gender == Gender.female:
            if (person_balanced.front_length - person_balanced.back_length) > self.optimal_balance:
                raise ValueError("front_length and back_length are not properly balanced")
            else:
                self.person_balanced = person_balanced

    def get_balanced_person(self) -> Person:
        return self.person_balanced

    def get_optimal_balance(self) -> float:
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            return 3.5 * CM
        else:
            raise NotImplementedError(
                "Matching balance for given bustline is not yet implemented."
            )
