from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

import numpy as np

T = TypeVar("T")


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
class DetectionResult:
    data: Any
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, data: Any, latency_ms: float):
        return cls(data=data, latency_ms=latency_ms)

    @property
    def is_detected(self) -> bool:
        return False

    @property
    def detected_cnt(self) -> int:
        return 0


@dataclass
class SegmentDetectionData:
    boxes: np.ndarray
    scores: np.ndarray
    labels: np.ndarray
    masks: np.ndarray


@dataclass
class SegmentDetectionResult(DetectionResult):
    data: SegmentDetectionData

    @property
    def is_detected(self) -> bool:
        return self.data.labels

    @property
    @abstractmethod
    def detected_cnt(self) -> int:
        pass
