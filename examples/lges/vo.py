__all__ = [
    "FrameData",
    "LgesMetadata",
    "DetectionResultDto",
    "FaultFrameDetectResult",
]

from dataclasses import dataclass

import numpy as np

from vnexis.vo import (
    DetectResult,
    Frame,
    Metadata,
    RawData,
)


@dataclass(frozen=True)
class FrameData(RawData):
    frame: Frame


@dataclass(frozen=True)
class LgesMetadata(Metadata):
    cell_id: str
    key_frame_detect_time: float


@dataclass(frozen=True)
class DetectionResultDto:
    boxes: np.ndarray
    labels: np.ndarray
    scores: np.ndarray
    masks: np.ndarray
    img_size: tuple[int, int]


@dataclass(frozen=True)
class FaultFrameDetectResult(DetectResult):
    detection_result: DetectionResultDto
    time: float
