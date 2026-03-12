"""Pattern package — re-exports every public name from :mod:`sewpat.pattern.part`.

Importing from ``sewpat.pattern`` continues to work unchanged after the split
of the old monolithic ``pattern.py`` into sub-modules.
"""

from ..element import GeometryType, PatternElement, PrecisionPoint
from .construction import ConstructionGrid, ConstructionGridPart
from .part import (
    Block,
    GarmentPart,
    NamedAccessMixin,
    OverlayPart,
    Pattern,
    PatternConfig,
    PatternPart,
)

__all__ = [
    "GeometryType",
    "PatternElement",
    "PrecisionPoint",
    "PatternConfig",
    "GarmentPart",
    "DartResult",
    "NamedAccessMixin",
    "PatternPart",
    "ConstructionGridPart",
    "ConstructionGrid",
    "Block",
    "OverlayPart",
    "Pattern",
]
