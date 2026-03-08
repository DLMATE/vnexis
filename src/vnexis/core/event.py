from dataclasses import dataclass
from typing import Any

from vnexis.common.event import Event
from vnexis.core.entity.raw_data import RawData
from vnexis.core.entity.target import DetectResult, Frame, Target


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
    result: Any = None


@dataclass(kw_only=True, frozen=True)
class TargetCreated(Event):
    client_id: int
    session_id: int
    target: Target


@dataclass(kw_only=True, frozen=True)
class DetectionDone(Event):
    client_id: int
    session_id: int
    target: Target
    detect_result: DetectResult


@dataclass(kw_only=True, frozen=True)
class DefectDetected(Event):
    client_id: int
    session_id: int
    target: Target
    detect_result: DetectResult


@dataclass(kw_only=True, frozen=True)
class FrameCaptured(Event):
    client_id: int
    session_id: int
    frame: Frame
