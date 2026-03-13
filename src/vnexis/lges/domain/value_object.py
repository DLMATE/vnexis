from dataclasses import dataclass

import numpy as np

from vnexis.core.domain.value_object import (
    DetectResult,
    Frame,
    Metadata,
    RawData,
)


@dataclass
class FrameData(RawData):
    frame: Frame


@dataclass
class LgesMetadata(Metadata):
    cell_id: str
    key_frame_detect_time: float


@dataclass
class DetectionResultDto:
    boxes: np.ndarray
    labels: np.ndarray
    scores: np.ndarray
    masks: np.ndarray
    img_size: tuple[int, int]


@dataclass
class FaultFrameDetectResult(DetectResult):
    detection_result: DetectionResultDto
    time: float
