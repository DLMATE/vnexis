from vnexis.core.domain.event import (
    DefectDetected,
    DetectionDone,
    DomainEvent,
    Preprocessed,
    RawDataCollected,
)
from vnexis.lges.domain.value_object import (
    DetectionResultDto,
    FaultFrameDetectResult,
    FrameData,
    LgesMetadata,
)


class FrameCaptured(RawDataCollected[FrameData]): ...


class KeyFrameDetectionDone(DomainEvent):
    raw_data: FrameData
    metadata: LgesMetadata
    result: DetectionResultDto


class KeyFrameDetected(Preprocessed[FrameData, LgesMetadata]): ...


class FaultFrameDetectionDone(
    DetectionDone[FrameData, LgesMetadata, FaultFrameDetectResult]
): ...


class FaultFrameDetected(
    DefectDetected[FrameData, LgesMetadata, FaultFrameDetectResult]
): ...
