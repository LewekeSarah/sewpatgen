"""Person related information required for pattern construction."""

import copy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from sewpat.units import CM

_PERSONS_CSV = Path(__file__).parent / "data" / "persons.csv"

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

    kwargs: dict[str, Any] = {}
    for col in _FLOAT_COLS:
        val = row.get(col)
        if pd.notna(val):
            kwargs[col] = float(val) * CM

    gender_str = str(row.get("gender", "female")).strip().lower()
    kwargs["gender"] = Gender(gender_str)

    return Person(**kwargs)


class Gender(Enum):
    """Some pattern have gender-specific adjustments."""

    MALE = "male"
    FEMALE = "female"
    BOY = "boy"
    GIRL = "girl"
    BABY = "baby"


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
    front_length: float | None = None  # VL  — Vorderlänge (VL2 variant: balancing, future feature)
    body_rise: float | None = None  # SiH — Sitzhöhe
    inseam: float | None = None  # SrH — Schritthöhe
    back_width: float | None = None  # RüB — Rückenbreite
    armscye_depth: float | None = None  # AlT — Armlochtiefe
    armscye_width: float | None = None  # ArD — Armdurchmesser
    chest_width: float | None = None  # BrB — Brustbreite
    height: float | None = None  # KöH — Körperhöhe
    gender: Gender = Gender.FEMALE  # Geschlecht


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

    def __init__(self, person: Person) -> None:  # private — only PersonAnalyser calls this
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


class MeasurementDeriver:
    """Derives missing body measurements from bust circumference.

    Single responsibility: Calculate derived measurements using standard formulas
    for a given bust range (currently 80–89 cm).
    """

    def __init__(self, bust: float | None) -> None:
        """Initialize with a bust circumference.

        Args:
            bust: Bust circumference in mm, or None.

        Raises:
            NotImplementedError: If bust is None or outside the supported range.
        """
        self._assert_bust_range(bust)
        self.bust: float = bust  # type: ignore[assignment]  # bust is guaranteed non-None after assertion

    def _assert_bust_range(self, bust: float | None) -> None:
        """Assert that bust is within the supported range [80, 89] cm.

        Raises:
            NotImplementedError: If bust is None or outside the supported range.
        """
        if bust is None or bust <= 80 * CM or bust > 89 * CM:
            raise NotImplementedError("Matching formula for given bustline is not yet implemented.")

    def derive_armscye_depth(self) -> float:
        """Calculate armscye depth from bust circumference."""
        return self.bust / 10 + 11 * CM

    def derive_armscye_width(self) -> float:
        """Calculate armscye width from bust circumference."""
        return self.bust / 8 - 1.5 * CM

    def derive_chest_width(self) -> float:
        """Calculate chest width from bust circumference."""
        return self.bust / 4 - 4.0 * CM

    def derive_back_width(self) -> float:
        """Calculate back width from bust circumference."""
        return self.bust / 8 + 5.5 * CM

    def apply_to_person(self, person: Person) -> Person:
        """Create a copy of *person* with missing measurements derived.

        Only measurements that are currently ``None`` are filled in.

        Args:
            person: Raw body measurements.

        Returns:
            A copy of *person* with derived measurements filled in.
        """
        person_copy = copy.copy(person)
        if person_copy.armscye_depth is None:
            person_copy.armscye_depth = self.derive_armscye_depth()
        if person_copy.armscye_width is None:
            person_copy.armscye_width = self.derive_armscye_width()
        if person_copy.chest_width is None:
            person_copy.chest_width = self.derive_chest_width()
        if person_copy.back_width is None:
            person_copy.back_width = self.derive_back_width()
        return person_copy


class BalanceAdjuster:
    """Applies balance adjustments to body measurements.

    Single responsibility: Apply front_length and back_length corrections.
    """

    def __init__(self, adjustments: BalanceAdjustments) -> None:
        """Initialize with balance adjustments.

        Args:
            adjustments: Front/back length corrections.
        """
        self.adjustments = adjustments

    def apply_to_person(self, person: Person) -> Person:
        """Create a copy of *person* with balance adjustments applied.

        Args:
            person: Body measurements.

        Returns:
            A copy of *person* with adjustments applied.
        """
        person_copy = copy.deepcopy(person)
        for key, val in self.adjustments.__dict__.items():
            current = getattr(person_copy, key)
            if current is not None:
                setattr(person_copy, key, current + val)
        return person_copy


class BalanceValidator:
    """Validates front/back length balance for pattern construction.

    Single responsibility: Check that front_length and back_length are
    properly balanced according to bust-specific optimal ranges.
    """

    def __init__(self, bust: float | None) -> None:
        """Initialize with a bust circumference to determine optimal balance.

        Args:
            bust: Bust circumference in mm.

        Raises:
            NotImplementedError: If bust is outside the supported range.
        """
        self.optimal_balance = self._get_optimal_balance(bust)

    def _get_optimal_balance(self, bust: float | None) -> float:
        """Determine the optimal front/back balance for the given bustline.

        Raises:
            NotImplementedError: If bustline is outside the supported range.
        """
        if bust is not None and (bust > 80 * CM) and (bust <= 89 * CM):
            return 3.5 * CM
        else:
            raise NotImplementedError("Matching balance for given bustline is not yet implemented.")

    def validate(self, person: Person) -> BalancedPerson:
        """Validate that *person* is properly balanced and wrap in BalancedPerson.

        Args:
            person: Body measurements to validate.

        Returns:
            A BalancedPerson wrapper indicating validation passed.

        Raises:
            ValueError: If front_length and back_length are not both set, or if
                the difference exceeds the optimal balance.
        """
        if person.gender != Gender.FEMALE:
            return BalancedPerson(person)

        fl = person.front_length
        bl = person.back_length
        if fl is None or bl is None:
            raise ValueError("front_length and back_length must both be set to balance the person.")
        if (fl - bl) > self.optimal_balance:
            diff_cm = (fl - bl) / CM
            optimal_cm = self.optimal_balance / CM
            raise ValueError(
                f"front_length and back_length are not properly balanced: "
                f"difference {diff_cm:.2f} cm exceeds optimal {optimal_cm:.2f} cm"
            )
        return BalancedPerson(person)


class PersonAnalyser:
    """Orchestrates measurement derivation, balance adjustment, and validation.

    This is a facade that coordinates the three single-responsibility classes:
    - :class:`MeasurementDeriver` — derives missing measurements from bust
    - :class:`BalanceAdjuster` — applies balance corrections
    - :class:`BalanceValidator` — validates front/back length balance

    The result is a :class:`BalancedPerson` ready for pattern construction.

    Args:
        person: Raw body measurements.
        balance_adjustments: Optional front/back length corrections.
    """

    def __init__(
        self, person: Person, balance_adjustments: BalanceAdjustments | None = None
    ) -> None:
        """Initialise and process *person* through derivation, adjustment, and validation."""
        self._original_person = person
        self.balance_adjustments = balance_adjustments

        if person.bust is not None:
            deriver = MeasurementDeriver(person.bust)
            self.person = deriver.apply_to_person(person)
        else:
            self.person = copy.copy(person)

        if balance_adjustments is not None:
            adjuster = BalanceAdjuster(balance_adjustments)
            self.person = adjuster.apply_to_person(self.person)

        validator = BalanceValidator(self.person.bust)
        self.person_balanced = validator.validate(self.person)

    def get_balanced_person(self) -> BalancedPerson:
        """Return the validated and balanced person, ready for pattern construction."""
        return self.person_balanced
