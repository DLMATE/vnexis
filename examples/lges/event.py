__all__ = [
    "KeyFrameDetectionDone",
    "KeyFrameDetected",
    "FaultFrameDetectionDone",
    "FaultFrameDetected",
]

from dataclasses import dataclass

from lges.vo import (
    DetectionResultDto,
    FaultFrameDetectResult,
    LgesMetadata,
)
from vnexis.event import (
    DefectDetected,
    DetectionDone,
    DomainEvent,
    Preprocessed,
)
from vnexis.vo import Frame


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetectionDone(DomainEvent):
    raw_data: Frame
    metadata: LgesMetadata
    result: DetectionResultDto


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetected(Preprocessed[Frame, LgesMetadata]): ...


@dataclass(kw_only=True, frozen=True)
class FaultFrameDetectionDone(
    DetectionDone[Frame, LgesMetadata, FaultFrameDetectResult]
): ...


@dataclass(kw_only=True, frozen=True)
class FaultFrameDetected(
    DefectDetected[Frame, LgesMetadata, FaultFrameDetectResult]
): ...
