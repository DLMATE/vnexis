import logging
from abc import ABC, abstractmethod
from typing import Generic

from vnexis.core.common import AsyncEventHandler
from vnexis.core.common.event import E, EventBus
from vnexis.core.domain.event import (
    DefectDetected,
    DetectionDone,
    FrameBuffered,
    FrameCaptured,
    FramePendingDone,
    Preprocessed,
    RawDataCollected,
)
from vnexis.core.domain.value_object import TDetectResult, TMetadata, TRawData

logger = logging.getLogger(__name__)


class DomainEventHandler(ABC, AsyncEventHandler, Generic[E]):
    def __init__(self, session_id: int, event_bus: EventBus = EventBus()):
        self._session_id = session_id
        self._event_bus = event_bus

        super().__init__()

    def handle(self, event: E):
        if event.session_id != self._session_id:
            return
        super().handle(event)

    @abstractmethod
    def process(self, event: E) -> None:
        pass

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus


class RawDataCollectedHandler(
    ABC, DomainEventHandler[RawDataCollected], Generic[TRawData]
):
    pass


class PreprocessedHandler(
    ABC, DomainEventHandler[Preprocessed], Generic[TRawData, TMetadata]
):
    pass


class DetectionDoneHandler(
    ABC,
    DomainEventHandler[DetectionDone],
    Generic[TRawData, TMetadata, TDetectResult],
):
    pass


class DefectDetectedHandler(
    ABC,
    DomainEventHandler[DefectDetected],
    Generic[TRawData, TMetadata, TDetectResult],
):
    pass


class FrameCapturedHandler(ABC, DomainEventHandler[FrameCaptured]):
    pass


class FrameBufferedHandler(ABC, DomainEventHandler[FrameBuffered]):
    pass


class FramePendingDoneHandler(ABC, DomainEventHandler[FramePendingDone]):
    pass
