from dataclasses import dataclass


@dataclass
class BBox:
    x1: float
    y1: int
    x2: int
    y2: int
