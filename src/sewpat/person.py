"""Person related information required for pattern construction."""

import copy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd

from sewpat.units import CM

_PERSONS_CSV = Path(__file__).parent / "data" / "persons.csv"

# Float measurement columns — all values stored in cm, converted to mm on load.
_FLOAT_COLS = (
    "height",
    "bust",
    "waist",
    "hip",
    "hip_depth",
    "bust_depth",
    "neck_size",
    "bust_span",
    "shoulder_width",
    "back_length",
    "front_length",
    "body_rise",
    "inseam",
    "back_width",
    "armscye_depth",
    "armscye_width",
    "chest_width",
)


def load_person(name: str, date: str | None = None) -> Person:
    """Load a :class:`Person` from ``persons.csv`` by name.

    Args:
        name: Person name as stored in the CSV (case-insensitive).
        date: Optional measurement date (``YYYY-MM-DD``).  If *None* the most
            recent row for the given name is used.

    Returns:
        A :class:`Person` with all measured fields populated (unmeasured fields
        remain ``None``).

    Raises:
        KeyError: if no matching row is found.
    """
    df = pd.read_csv(_PERSONS_CSV, dtype={"date": str})
    df["name_lower"] = df["name"].str.strip().str.lower()

    mask = df["name_lower"] == name.strip().lower()
    if date is not None:
        mask &= df["date"] == date
    rows = df[mask]

    if rows.empty:
        raise KeyError(
            f"No person named {name!r}"
            + (f" measured on {date!r}" if date else "")
            + f" found in {_PERSONS_CSV}."
        )

    row = rows.sort_values("date").iloc[-1]  # most recent if multiple

    kwargs: dict = {}
    for col in _FLOAT_COLS:
        val = row.get(col)
        if pd.notna(val):
            kwargs[col] = float(val) * CM

    gender_str = str(row.get("gender", "female")).strip().lower()
    kwargs["gender"] = Gender(gender_str)

    return Person(**kwargs)


class Gender(Enum):
    """Some pattern have gender-specific adjustments."""

    male = "male"
    female = "female"
    boy = "boy"
    girl = "girl"
    baby = "baby"


@dataclass
class Person:
    """Raw body measurements for a single person.

    All values are stored in mm (the project's internal unit).
    Unmeasured fields remain ``None`` and are excluded from calculations.

    Attributes:
        bust: BrU — Brustumfang (bust circumference).
        waist: TaU — Taillenumfang (waist circumference).
        hip: HüU — Hüftumfang (hip circumference).
        hip_depth: HüT — Hüfttiefe (hip depth).
        bust_depth: BrT — Brusttiefe (bust depth).
        neck_size: HlB — Halslochbreite (neck hole width).
        bust_span: BrPA — Brustpunktabstand (bust point distance).
        shoulder_width: SuB — Schulterbreite (shoulder width).
        back_length: RüL — Rückenlänge (back length).
        front_length: VL — Vorderlänge (front length).
        body_rise: SiH — Sitzhöhe (body rise).
        inseam: SrH — Schritthöhe (inside leg).
        back_width: RüB — Rückenbreite (back width).
        armscye_depth: AlT — Armlochtiefe (armhole depth).
        armscye_width: ArD — Armdurchmesser (arm diameter).
        chest_width: BrB — Brustbreite (chest width).
        height: KöH — Körperhöhe (body height).
        gender: Geschlecht (gender for gender-specific adjustments).
    """

    bust: float | None = None  # BrU — Brustumfang
    waist: float | None = None  # TaU — Taillenumfang
    hip: float | None = None  # HüU — Hüftumfang
    hip_depth: float | None = None  # HüT — Hüfttiefe
    bust_depth: float | None = None  # BrT — Brusttiefe
    neck_size: float | None = None  # HlB — Halslochbreite
    bust_span: float | None = None  # BrPA — Brustpunktabstand
    shoulder_width: float | None = None  # SuB — Schulterbreite
    back_length: float | None = None  # RüL — Rückenlänge
    front_length: float | None = (
        None  # VL  — Vorderlänge (VL2 variant: balancing, future feature)
    )
    body_rise: float | None = None  # SiH — Sitzhöhe
    inseam: float | None = None  # SrH — Schritthöhe
    back_width: float | None = None  # RüB — Rückenbreite
    armscye_depth: float | None = None  # AlT — Armlochtiefe
    armscye_width: float | None = None  # ArD — Armdurchmesser
    chest_width: float | None = None  # BrB — Brustbreite
    height: float | None = None  # KöH — Körperhöhe
    gender: Gender = Gender.female  # Geschlecht


@dataclass
class BalanceAdjustments:
    """Front/back length corrections for balance adjustments.

    Attributes:
        back_length: RüL — Rückenlänge correction in mm.
        front_length: VL — Vorderlänge correction in mm.
    """

    back_length: float = 0.0  # RüL — Rückenlänge
    front_length: float = 0.0  # VL  — Vorderlänge


@dataclass(frozen=True)
class PersonalAdjustments:
    """Body-deviation corrections for non-standard figures.

    These are individual corrections applied on top of standard block
    construction.  Two people with the same measurements and
    :class:`~sewpat.fitclass.FitClass` may still need different adjustments.

    Attributes:
        hip_offset:     Horizontal hip offset — shifts the hip-adjustment
                        vertical grid line outward (positive) or inward
                        (negative).  Range: 1 cm (nach hinten gekipptes
                        Becken) to 3 cm (Hohlkreuz / flacher Po).
                        (BeckenAdjustment — Becken-Korrektur)
        shoulder_drop:  Vertical drop applied at the armscye-shoulder
                        intersection (positive Y = downward in SVG).
                        Range: 1–1.5 cm.
        balance:        Front/back length balance corrections.
    """

    hip_offset: float = 2.0 * CM  # Becken-Korrektur
    shoulder_drop: float = 1.5 * CM  # Schulterabfall
    balance: BalanceAdjustments = field(default_factory=BalanceAdjustments)

    def __post_init__(self) -> None:
        """Validate hip_offset and shoulder_drop are within permitted ranges."""
        if not (1.0 * CM - 1e-9 <= self.hip_offset <= 3.0 * CM + 1e-9):
            raise ValueError(
                f"hip_offset={self.hip_offset / CM:.2f} cm is outside the valid "
                f"range [1.0, 3.0] cm.  "
                f"1 cm = nach hinten gekipptes Becken, 3 cm = Hohlkreuz / flacher Po."
            )
        if not (1.0 * CM - 1e-9 <= self.shoulder_drop <= 1.5 * CM + 1e-9):
            raise ValueError(
                f"shoulder_drop={self.shoulder_drop / CM:.2f} cm is outside the "
                f"valid range [1.0, 1.5] cm."
            )


class BalancedPerson:
    """A :class:`Person` validated and balanced by :class:`PersonAnalyser`.

    This type can only be created by :meth:`PersonAnalyser.get_balanced_person`.
    Passing a ``BalancedPerson`` instead of a raw :class:`Person` to construction
    functions signals — at the type level — that balancing has already been done.

    Access the underlying :class:`Person` via the ``.person`` attribute.
    """

    def __init__(
        self, person: Person
    ) -> None:  # private — only PersonAnalyser calls this
        """Wrap a validated, balanced *person*. Use :meth:`PersonAnalyser.get_balanced_person`."""
        self._person = person

    @property
    def person(self) -> Person:
        """Return the wrapped :class:`Person`."""
        return self._person

    def __getattr__(self, name: str) -> object:
        """Delegate attribute access to the wrapped :class:`Person`."""
        return getattr(self._person, name)

    def __repr__(self) -> str:
        """Return an unambiguous string representation."""
        return f"BalancedPerson({self._person!r})"


class PersonAnalyser:
    """Calculates and balances body measurements for pattern construction.

    Derives missing measurements from the bust circumference using standard
    formulas, then validates that the person is properly balanced
    (front length vs. back length within the optimal range).

    Args:
        person: Raw body measurements.
        balance_adjustments: Optional front/back length corrections.
    """

    def __init__(
        self, person: Person, balance_adjustments: BalanceAdjustments | None = None
    ) -> None:
        """Initialise, derive missing measurements, and balance *person* immediately."""
        self.person = person
        self.person_balanced: BalancedPerson | None = None
        self.balance = balance_adjustments
        self.optimal_balance = self.get_optimal_balance()
        self.calculate_measurements()
        self.balance_person()

    def _set_armscye_depth(self) -> None:
        """Derive armscye depth from bust circumference if not already set."""
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.armscye_depth = (
                self.person.bust / 10 + 11 * CM
                if self.person.armscye_depth is None
                else self.person.armscye_depth
            )
        if self.person.armscye_depth is None:
            raise NotImplementedError(
                "Matching armscye_depth formula for given bustline "
                "is not yet implemented."
            )

    def _set_armscye_width(self) -> None:
        """Derive armscye width from bust circumference if not already set."""
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.armscye_width = (
                self.person.bust / 8 - 1.5 * CM
                if self.person.armscye_width is None
                else self.person.armscye_width
            )
        if self.person.armscye_width is None:
            raise NotImplementedError(
                "Matching armscye_width formula for given bustline "
                "is not yet implemented."
            )

    def _set_chest_width(self) -> None:
        """Derive chest width from bust circumference if not already set."""
        if (self.person.bust > 80 * CM) and (self.person.bust <= 89 * CM):
            self.person.chest_width = (
                self.person.bust / 4 - 4.0 * CM
                if self.person.chest_width is None
                else self.person.chest_width
            )
        if self.person.chest_width is None:
            raise NotImplementedError(
                "Matching chest_width formula for given bustline "
                "is not yet implemented."
            )

    def _set_back_width(self) -> None:
        """Derive back width from bust circumference if not already set."""
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

    def calculate_measurements(self) -> None:
        """Derive all missing measurements from bust circumference."""
        if self.person.bust is not None:
            self._set_armscye_depth()
            self._set_armscye_width()
            self._set_chest_width()
            self._set_back_width()

    def balance_person(self) -> None:
        """Apply balance adjustments and validate front/back length balance."""
        person_balanced = copy.deepcopy(self.person)
        if self.balance is not None:
            for key, val in self.balance.__dict__.items():
                person_balanced.__setattr__(
                    key, person_balanced.__getattribute__(key) + val
                )
        if person_balanced.gender == Gender.female:
            if (
                person_balanced.front_length - person_balanced.back_length
            ) > self.optimal_balance:
                raise ValueError(
                    "front_length and back_length are not properly balanced"
                )
            else:
                self.person_balanced = BalancedPerson(person_balanced)

    def get_balanced_person(self) -> BalancedPerson:
        """Get the validated and balanced person.

        Raises:
            RuntimeError: If the person has not been balanced.
        """
        if self.person_balanced is None:
            raise RuntimeError(
                "balance_person() did not produce a BalancedPerson. "
                "Check that front_length and back_length are properly balanced."
            )
        return self.person_balanced

    def get_optimal_balance(self) -> float:
        """Determine the optimal front/back balance for the given bustline.

        Raises:
            NotImplementedError: If the bustline is outside the supported range.
        """
        if (
            self.person.bust is not None
            and (self.person.bust > 80 * CM)
            and (self.person.bust <= 89 * CM)
        ):
            return 3.5 * CM
        else:
            raise NotImplementedError(
                "Matching balance for given bustline is not yet implemented."
            )
