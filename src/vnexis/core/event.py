from dataclasses import dataclass

from vnexis.common.event import Event
from vnexis.core.dto import (
    DetectResult,
    Frame,
    PreprocessResult,
    RawData,
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
class DefectDetected(DetectionDone): ...


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
