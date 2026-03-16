from dataclasses import dataclass

from vnexis.core.domain.event import (
    DefectDetected,
    DetectionDone,
    DomainEvent,
    Preprocessed,
)
from vnexis.lges.domain.value_object import (
    DetectionResultDto,
    FaultFrameDetectResult,
    FrameData,
    LgesMetadata,
)

# class FrameCaptured(RawDataCollected[FrameData]): ...


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
