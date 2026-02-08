from dataclasses import dataclass

from ivs.common.event import Event
from ivs.domain.entities import DetectionResult, Frame


@dataclass(kw_only=True, frozen=True)
class FrameCapturedEvent(Event):
    client_id: int
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class DetectionDoneEvent(Event):
    client_id: int
    frame: Frame
    detection_result: DetectionResult


@dataclass(kw_only=True, frozen=True)
class FaultDetectedEvent(Event):
    client_id: int
    frame: Frame
    detection_result: DetectionResult
