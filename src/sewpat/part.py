from __future__ import annotations

from dataclasses import dataclass, field
from .geometry import GEOMETRIC_TYPE


@dataclass
class PatternPart:
    name: str
    elements: list[GEOMETRIC_TYPE] = field(default_factory=list)
