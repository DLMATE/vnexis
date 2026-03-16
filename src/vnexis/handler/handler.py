import logging
from abc import abstractmethod
from typing import Generic

from vnexis.event import (
    AsyncEventHandler,
    DefectDetected,
    DetectionDone,
    EventBus,
    FrameBuffered,
    FrameCaptured,
    FramePendingDone,
    Preprocessed,
    RawDataCollected,
    TEvent,
)
from vnexis.handler.frame_buffer import FrameBufferManager
from vnexis.handler.frame_clipper import FrameClipperManager
from vnexis.vo import TDetectResult, TMetadata, TRawData

logger = logging.getLogger(__name__)


class DomainEventHandler(AsyncEventHandler[TEvent]):
    def __init__(self, event_bus: EventBus, session_id: int | None = None):
        self._session_id = session_id
        self._event_bus = event_bus

        super().__init__()

    def handle(self, event: TEvent):
        # if self._session_id is not None and event.session_id != self._session_id:
        #     return
        super().handle(event)

    @abstractmethod
    def process(self, event: TEvent) -> None:
        pass

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus


class RawDataCollectedHandler(DomainEventHandler[RawDataCollected], Generic[TRawData]):
    pass


class PreprocessedHandler(
    DomainEventHandler[Preprocessed], Generic[TRawData, TMetadata]
):
    pass


class DetectionDoneHandler(
    DomainEventHandler[DetectionDone],
    Generic[TRawData, TMetadata, TDetectResult],
):
    pass


class DefectDetectedHandler(
    DomainEventHandler[DefectDetected],
    Generic[TRawData, TMetadata, TDetectResult],
):
    pass


class FrameCapturedHandler(DomainEventHandler[RawDataCollected]):
    pass


class FrameBuffering(FrameCapturedHandler):
    publishes = [FrameBuffered]

    def __init__(
        self,
        event_bus: EventBus,
        session_id: int | None = None,
        frame_buffer_manager: FrameBufferManager | None = None,
    ):
        super().__init__(event_bus, session_id)
        self._frame_buffer_manager = frame_buffer_manager or FrameBufferManager()

    def process(self, event: FrameCaptured) -> None:
        self._frame_buffer_manager.add_frame(event.session_id, event.frame)
        self._event_bus.publish(
            FrameBuffered(session_id=event.session_id, frame=event.frame)
        )


class FrameBufferedHandler(DomainEventHandler[FrameBuffered]):
    pass


class FrameClipping(FrameBufferedHandler):
    publishes = [FramePendingDone]

    def __init__(
        self,
        event_bus: EventBus,
        session_id: int | None = None,
        frame_clipper_manager: FrameClipperManager | None = None,
    ):
        super().__init__(event_bus, session_id)
        self._frame_clipper_manager = frame_clipper_manager

    def process(self, event: FrameBuffered) -> None:
        completed = self._frame_clipper_manager.clipping(event.session_id, event.frame)
        for clip in completed:
            self.logger.info(f"[FrameClipper] clip completed: {clip.key_frame_idx}")
            self._event_bus.publish(
                FramePendingDone(
                    session_id=event.session_id,
                    key_frame_idx=clip.key_frame_idx,
                    frames=clip.frames,
                )
            )


class FramePendingDoneHandler(DomainEventHandler[FramePendingDone]):
    pass
