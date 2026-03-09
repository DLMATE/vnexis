from dataclasses import dataclass

from vnexis.common.event import Event
from vnexis.core.entity.raw_data import RawData
from vnexis.core.entity.target import (
    DetectResult,
    Frame,
    PostprocessResult,
    PreprocessResult,
    Target,
)


@dataclass(kw_only=True, frozen=True)
class RawDataCollected(Event):
    client_id: int
    session_id: int
    raw_data: RawData


@dataclass(kw_only=True, frozen=True)
class Preprocessed(Event):
    client_id: int
    session_id: int
    raw_data: RawData
    result: PreprocessResult


@dataclass(kw_only=True, frozen=True)
class TargetCreated(Event):
    client_id: int
    session_id: int
    raw_data: RawData
    preprocess_result: PreprocessResult
    target: Target


@dataclass(kw_only=True, frozen=True)
class DetectionDone(Event):
    client_id: int
    session_id: int
    raw_data: RawData
    preprocess_result: PreprocessResult
    target: Target
    detect_result: DetectResult


@dataclass(kw_only=True, frozen=True)
class Postprocessed(Event):
    client_id: int
    session_id: int
    raw_data: RawData
    preprocess_result: PreprocessResult
    target: Target
    detect_result: DetectResult
    postprocess_result: PostprocessResult


@dataclass(kw_only=True, frozen=True)
class DefectDetected(Postprocessed): ...


@dataclass(kw_only=True, frozen=True)
class FrameCaptured(Event):
    client_id: int
    session_id: int
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class FrameBuffered(Event):
    client_id: int
    session_id: int
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class FramePendingDone(Event):
    client_id: int
    session_id: int
    key_frame_idx: int
    frames: list[Frame]
