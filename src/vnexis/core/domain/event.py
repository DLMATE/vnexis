__all__ = [
    "DomainEvent",
    "RawDataCollected",
    "Preprocessed",
    "DetectionDone",
    "DefectDetected",
    "FrameCaptured",
    "FrameBuffered",
    "FramePendingDone",
]

from dataclasses import dataclass
from typing import Generic

from vnexis.core.common.event import (
    Event,
)
from vnexis.core.domain.value_object import (
    Frame,
    TDetectResult,
    TMetadata,
    TRawData,
)


@dataclass(kw_only=True, frozen=True)
class DomainEvent(Event):
    session_id: int


@dataclass(kw_only=True, frozen=True)
class RawDataCollected(DomainEvent, Generic[TRawData]):
    raw_data: TRawData


@dataclass(kw_only=True, frozen=True)
class Preprocessed(DomainEvent, Generic[TRawData, TMetadata]):
    raw_data: TRawData
    frame: Frame
    metadata: TMetadata


# @dataclass(kw_only=True, frozen=True)
# class TargetCreated(DomainEvent, Generic[TRawData, TPreprocessResult]):
#     raw_data: TRawData
#     preprocess_result: TPreprocessResult


@dataclass(kw_only=True, frozen=True)
class DetectionDone(DomainEvent, Generic[TRawData, TMetadata, TDetectResult]):
    raw_data: TRawData
    frame: Frame
    metadata: TMetadata
    detect_result: TDetectResult


@dataclass(kw_only=True, frozen=True)
class DefectDetected(DomainEvent, Generic[TRawData, TMetadata, TDetectResult]):
    raw_data: TRawData
    frame: Frame
    metadata: TMetadata
    detect_result: TDetectResult


@dataclass(kw_only=True, frozen=True)
class FrameCaptured(DomainEvent):
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class FrameBuffered(DomainEvent):
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class FramePendingDone(DomainEvent):
    key_frame_idx: int
    frames: list[Frame]
