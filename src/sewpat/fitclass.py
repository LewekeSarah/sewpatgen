"""Fit class (Passformklasse) — single source of truth for garment ease.

The :class:`FitClass` wraps a single integer ``pk`` in the range 0–12 that
encodes how tightly a garment fits the body.  All ease values are read from
``src/sewpat/data/fitclass.csv`` (multi-index: pk × ease field × lo/hi).

Default values are the upper bound (hi) of the published range.
Any field may be overridden at construction time; the value must lie within
the published [lo, hi] range or a :class:`ValueError` is raised.

``bust_point_ease`` (ZuBrA) is derived as a construction offset and is
included in the table; ``bust_width_ease`` is *never* stored — it is always
derived as ``2 × (back_width_ease + armscye_width_ease + chest_width_ease)``.

Only PK 4 is populated with real values.  All other PKs raise
:class:`KeyError` until the full Mueller & Sohn table is digitised.

Typical PK ranges
-----------------
0–3   Swimwear, underwear, bodysuits
4–7   Blouses, light dresses, fitted tops
8–11  Jackets, structured coats
12    Heavy coats

Source: Mueller & Sohn, Rundschau / Modenähen drafting system.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from .units import CM

_CSV_PATH = Path(__file__).parent / "data" / "fitclass.csv"

#: Ease fields exposed on FitClass (matches CSV column level-0 names).
EASE_FIELDS = (
    "back_width_ease",  # RüB   — Rückenbreite-Zugabe
    "armscye_width_ease",  # ArD   — Armdurchmesser-Zugabe
    "chest_width_ease",  # BrB   — Brustbreite-Zugabe
    "armscye_depth_ease",  # AlT   — Armlochtiefe-Zugabe
    "waist_ease",  # TaU   — Taillenumfang-Zugabe
    "hip_ease",  # HüU   — Hüftumfang-Zugabe
    "bust_point_ease",  # ZuBrA — Zugabe Brustpunktabstand
    "shoulder_width_ease",  # SuB   — Schulterbreite-Zugabe
)


class _Range(NamedTuple):
    """Published [lo, hi] range for a single ease field at a given PK."""

    lo: float
    hi: float


def _load_table() -> dict[int, dict[str, _Range]]:
    """Load fitclass.csv into a nested dict: pk → field → _Range (values in mm)."""
    df = pd.read_csv(_CSV_PATH, header=[0, 1], index_col=0)
    result: dict[int, dict[str, _Range]] = {}
    for pk_val in df.index:
        row: dict[str, _Range] = {}
        for ef in EASE_FIELDS:
            lo = float(df.loc[pk_val, (ef, "lo")]) * CM
            hi = float(df.loc[pk_val, (ef, "hi")]) * CM
            row[ef] = _Range(lo=lo, hi=hi)
        result[int(pk_val)] = row
    return result


_TABLE: dict[int, dict[str, _Range]] = _load_table()


@dataclass
class FitClass:
    """Fit class — single source of truth for ease and construction offsets.

    Pass only ``pk`` to use upper-bound defaults for all ease fields.
    Override individual fields as needed; each must lie within the published
    range for the given PK or a :class:`ValueError` is raised.

    ``bust_width_ease`` is always derived and cannot be set directly.

    Args:
        pk:                 Integer 0–12 describing garment fit tightness.
        back_width_ease:    RüB  — override in mm.
        armscye_width_ease: ArD  — override in mm.
        chest_width_ease:   BrB  — override in mm.
        armscye_depth_ease: AlT  — override in mm.
        waist_ease:         TaU  — override in mm.
        hip_ease:           HüU  — override in mm.
        bust_point_ease:    ZuBrA — override in mm.
        shoulder_width_ease: ScB  — override in mm.

    Examples::

        fc = FitClass(pk=4)                         # all upper-bound defaults
        fc = FitClass(pk=4, back_width_ease=0.7*CM) # override one field
        fc.back_width_ease                          # → resolved value (mm)
        fc.bust_width_ease                          # → always derived
    """

    pk: int
    # Private overrides — use the public properties to read resolved values.
    _back_width_ease: float | None = None  # RüB  — Rückenbreite-Zugabe
    _armscye_width_ease: float | None = None  # ArD  — Armdurchmesser-Zugabe
    _chest_width_ease: float | None = None  # BrB  — Brustbreite-Zugabe
    _armscye_depth_ease: float | None = None  # AlT  — Armlochtiefe-Zugabe
    _waist_ease: float | None = None  # TaU  — Taillenumfang-Zugabe
    _hip_ease: float | None = None  # HüU  — Hüftumfang-Zugabe
    _bust_point_ease: float | None = None  # ZuBrA — Zugabe Brustpunktabstand
    _shoulder_width_ease: float | None = None  # ScB  — Schulterbreite-Zugabe

    def __init__(
        self,
        pk: int,
        back_width_ease: float | None = None,
        armscye_width_ease: float | None = None,
        chest_width_ease: float | None = None,
        armscye_depth_ease: float | None = None,
        waist_ease: float | None = None,
        hip_ease: float | None = None,
        bust_point_ease: float | None = None,
        shoulder_width_ease: float | None = None,
    ) -> None:
        """Initialise FitClass from *pk* with optional per-field ease overrides."""
        self.pk = pk
        self._back_width_ease = back_width_ease
        self._armscye_width_ease = armscye_width_ease
        self._chest_width_ease = chest_width_ease
        self._armscye_depth_ease = armscye_depth_ease
        self._waist_ease = waist_ease
        self._hip_ease = hip_ease
        self._bust_point_ease = bust_point_ease
        self._shoulder_width_ease = shoulder_width_ease
        self.__post_init__()

    def __post_init__(self) -> None:
        """Validate *pk* and resolve ease fields from the table."""
        if not (0 <= self.pk <= 12):
            raise ValueError(f"FitClass pk must be 0–12, got {self.pk!r}")
        if self.pk not in _TABLE:
            raise KeyError(
                f"PK {self.pk} is not yet in the fit-class table. Only PK 4 is currently populated."
            )
        row = _TABLE[self.pk]
        for ef in EASE_FIELDS:
            override = getattr(self, f"_{ef}")
            if override is not None:
                r = row[ef]
                if not (r.lo - 1e-9 <= override <= r.hi + 1e-9):
                    raise ValueError(
                        f"FitClass pk={self.pk}: {ef}={override / CM:.2f} cm is "
                        f"outside the valid range "
                        f"[{r.lo / CM:.2f}, {r.hi / CM:.2f}] cm."
                    )

    def _resolve(self, field_name: str) -> float:
        """Return override if set, otherwise the table upper bound (hi)."""
        override = getattr(self, f"_{field_name}")
        if override is not None:
            return float(override)
        return float(_TABLE[self.pk][field_name].hi)

    @property
    def back_width_ease(self) -> float:
        """RüB — Rückenbreite-Zugabe (override or table hi)."""
        return self._resolve("back_width_ease")

    @property
    def armscye_width_ease(self) -> float:
        """ArD — Armdurchmesser-Zugabe (override or table hi)."""
        return self._resolve("armscye_width_ease")

    @property
    def chest_width_ease(self) -> float:
        """BrB — Brustbreite-Zugabe (override or table hi)."""
        return self._resolve("chest_width_ease")

    @property
    def armscye_depth_ease(self) -> float:
        """AlT — Armlochtiefe-Zugabe (override or table hi)."""
        return self._resolve("armscye_depth_ease")

    @property
    def waist_ease(self) -> float:
        """TaU — Taillenumfang-Zugabe (override or table hi)."""
        return self._resolve("waist_ease")

    @property
    def hip_ease(self) -> float:
        """HüU — Hüftumfang-Zugabe (override or table hi)."""
        return self._resolve("hip_ease")

    @property
    def bust_point_ease(self) -> float:
        """ZuBrA — Zugabe Brustpunktabstand (override or table hi)."""
        return self._resolve("bust_point_ease")

    @property
    def shoulder_width_ease(self) -> float:
        """ScB — Schulterbreite-Zugabe (override or table hi)."""
        return self._resolve("shoulder_width_ease")

    @property
    def bust_width_ease(self) -> float:
        """BrW-Zugabe — always derived: 2 × (back + armscye_width + chest)."""
        return 2.0 * (self.back_width_ease + self.armscye_width_ease + self.chest_width_ease)

    def range(self, field_name: str) -> _Range:
        """Return the published [lo, hi] range for *field_name* at this PK.

        Args:
            field_name: One of the names in :data:`EASE_FIELDS`.

        Raises:
            KeyError: if *field_name* is not a recognised ease field.
        """
        if field_name not in _TABLE[self.pk]:
            raise KeyError(f"{field_name!r} is not a recognised ease field.")
        return _TABLE[self.pk][field_name]
