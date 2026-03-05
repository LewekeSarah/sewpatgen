"""Fit class (Passformklasse) — single source of truth for garment ease.

The :class:`FitClass` wraps a single integer ``pk`` in the range 0–12 that
encodes how tightly a garment fits the body.  All ease values and
PK-dependent construction offsets are derived from it, so no magic numbers
need to appear at call sites.

Typical PK ranges
-----------------
0–3   Swimwear, underwear, bodysuits
4–7   Blouses, light dresses, fitted tops
8–11  Jackets, structured coats
12    Heavy coats

Source: Mueller & Sohn, Rundschau / Modenähen drafting system.
"""

from dataclasses import dataclass
from typing import NamedTuple

from .units import CM


# ---------------------------------------------------------------------------
# Ranged PK value — stores the published range so callers can inspect it
# and optionally choose a position within it.
# ---------------------------------------------------------------------------

class _PKRange(NamedTuple):
    """A published range [lo, hi] for a PK-dependent construction value."""
    lo: float
    hi: float

    @property
    def midpoint(self) -> float:
        """Midpoint of the range — used as the default value."""
        return (self.lo + self.hi) / 2


# ---------------------------------------------------------------------------
# FitClass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FitClass:
    """Fit class — single source of truth for ease and construction offsets.

    Parameters
    ----------
    pk:
        Integer in the range 0–12 describing garment fit tightness.

    Examples
    --------
    ::

        from sewpat.fitclass import FitClass
        from sewpat.units import CM

        fc = FitClass(pk=4)
        offset = fc.bust_point_offset          # → 1.0 cm (midpoint)
        offset = fc.bust_point_offset_range.lo # → 1.0 cm (lower bound)
    """

    pk: int
    _ZuBrA: float | None = None  # optional override; use bust_point_offset_range midpoint if None

    def __post_init__(self) -> None:
        if not (0 <= self.pk <= 12):
            raise ValueError(f"FitClass pk must be 0–12, got {self.pk!r}")

    # ------------------------------------------------------------------
    # ZuBrA — Zugabe Brustpunktabstand (bust-point spacing offset)
    # Source: Mueller & Sohn; TODO: verify exact per-PK table reference.
    # ------------------------------------------------------------------

    @property
    def bust_point_offset_range(self) -> _PKRange:
        """Published [lo, hi] range for the bust-point spacing offset (ZuBrA).

        The midpoint is used as the default; callers that need a specific
        position within the range can read ``.lo`` and ``.hi`` directly.

        Source: Mueller & Sohn, Rundschau.
        TODO: confirm exact per-PK table page reference.
        """
        if self.pk < 4:
            return _PKRange(lo=0.0 * CM, hi=0.5 * CM)
        if self.pk < 8:
            return _PKRange(lo=1.0 * CM, hi=1.0 * CM)
        return _PKRange(lo=1.5 * CM, hi=1.5 * CM)

    @property
    def ZuBrA(self) -> float:
        """Bust-point spacing offset.

        Returns the override value if supplied, otherwise the midpoint of
        :attr:`bust_point_offset_range`.
        """
        if self._ZuBrA is not None:
            return self._ZuBrA
        return self.bust_point_offset_range.midpoint

