from dataclasses import dataclass

import numpy as np

from vnexis.core.entity.raw_data import RawData
from vnexis.core.entity.target import (
    DetectResult,
    Frame,
    Metadata,
    PostprocessResult,
    PreprocessResult,
)


@dataclass
class LgesRawData(RawData):
    frame: Frame


@dataclass
class LgesMetadata(Metadata):
    cell_id: str


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
    fault_frame_detection_results: list[DetectionResultDto]


@dataclass
class LgesPostproessResult(PostprocessResult):
    fault_frame_detection_results: list[DetectionResultDto]
