from dataclasses import dataclass
from sewpat.units import MM


@dataclass
class DinA4:
    width: float = 210 * MM
    height: float = 297 * MM


@dataclass
class DinA2:
    width: float = 420 * MM
    height: float = 594 * MM


@dataclass
class DinA1:
    width: float = 594 * MM
    height: float = 841 * MM


@dataclass
class DinA0:
    width: float = 841 * MM
    height: float = 1189 * MM
