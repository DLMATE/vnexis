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
    FrameData,
    LgesMetadata,
)
from vnexis.event import (
    DefectDetected,
    DetectionDone,
    DomainEvent,
    Preprocessed,
)


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetectionDone(DomainEvent):
    raw_data: FrameData
    metadata: LgesMetadata
    result: DetectionResultDto


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetected(Preprocessed[FrameData, LgesMetadata]): ...


@dataclass(kw_only=True, frozen=True)
class FaultFrameDetectionDone(
    DetectionDone[FrameData, LgesMetadata, FaultFrameDetectResult]
): ...


@dataclass(kw_only=True, frozen=True)
class FaultFrameDetected(
    DefectDetected[FrameData, LgesMetadata, FaultFrameDetectResult]
): ...
