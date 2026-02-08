from dataclasses import dataclass
from pathlib import Path
from functools import cached_property

import numpy as np


@dataclass
class Frame:
    idx: int
    data: np.ndarray
    
    @property
    def width(self):
        return self.data.shape[1]
    
    @property
    def height(self):
        return self.data.shape[0]

@dataclass
class PredictResult:
    boxes: np.ndarray
    scores: np.ndarray
    labels: np.ndarray
    masks: np.ndarray