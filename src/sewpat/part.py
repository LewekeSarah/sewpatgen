from dataclasses import dataclass
from typing import List
from .geometry import GEOMETRIC_TYPE


@dataclass
class PatternPart:
    name: str
    elements: List[GEOMETRIC_TYPE]
