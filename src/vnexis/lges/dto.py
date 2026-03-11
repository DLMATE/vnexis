from dataclasses import dataclass

import numpy as np

from vnexis.core.dto import (
    DetectResult,
    Frame,
    Metadata,
    PreprocessResult,
    RawData,
)


@dataclass
class LgesRawData(RawData):
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
class LgesPreprocessResult(PreprocessResult):
    frame: Frame
    metadata: LgesMetadata
    key_frame_detection_result: DetectionResultDto


@dataclass
class LgesDetectResult(DetectResult):
    fault_frame_detection_result: DetectionResultDto
    time: float
