from dataclasses import dataclass
from typing import ClassVar

from sewpat.units import MM


@dataclass(frozen=True)
class DinA4:
    width: ClassVar[float] = 210 * MM
    height: ClassVar[float] = 297 * MM


@dataclass(frozen=True)
class DinA2:
    width: ClassVar[float] = 420 * MM
    height: ClassVar[float] = 594 * MM


@dataclass(frozen=True)
class DinA1:
    width: ClassVar[float] = 594 * MM
    height: ClassVar[float] = 841 * MM


@dataclass(frozen=True)
class DinA0:
    width: ClassVar[float] = 841 * MM
    height: ClassVar[float] = 1189 * MM
