"""DIN paper-size constants for sewing pattern export.

All dimensions are in mm (the project's internal unit).
Import the class that matches the target paper size and pass it to
:func:`~sewpat.render.export_pattern_svg_mm`.
"""

from dataclasses import dataclass
from typing import ClassVar

from sewpat.units import MM


@dataclass(frozen=True)
class DinA4:
    """DIN A4 paper size: 210 × 297 mm."""

    width: ClassVar[float] = 210 * MM
    height: ClassVar[float] = 297 * MM


@dataclass(frozen=True)
class DinA2:
    """DIN A2 paper size: 420 × 594 mm."""

    width: ClassVar[float] = 420 * MM
    height: ClassVar[float] = 594 * MM


@dataclass(frozen=True)
class DinA1:
    """DIN A1 paper size: 594 × 841 mm."""

    width: ClassVar[float] = 594 * MM
    height: ClassVar[float] = 841 * MM


@dataclass(frozen=True)
class DinA0:
    """DIN A0 paper size: 841 × 1189 mm."""

    width: ClassVar[float] = 841 * MM
    height: ClassVar[float] = 1189 * MM
