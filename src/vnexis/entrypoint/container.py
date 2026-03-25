from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from vnexis.event import Event, EventBus, save_mermaid_flow
from vnexis.event.event import (
    DefectDetected,
    EventHandled,
    FrameCaptured,
    FramePendingDone,
)
from vnexis.handler import (
    DefectDetectedFrameSaver,
    DomainEventHandler,
    FrameBufferManager,
    StatisticsManager,
    VideoReader,
    VideoRequester,
    VideoSaver,
)
from vnexis.handler.raw_data_collector import RawDataCollector


class StreamContainer(containers.DeclarativeContainer):
    """단일 스트림 파이프라인의 DI 컨테이너.

    공통 인프라(EventBus, FrameBuffer, Statistics)를 선언적으로 구성하고,
    각 핸들러에 의존성을 자동 주입한다.
    """

    config = providers.Configuration(default={"save_dir": "output"})

    # ── Core ──
    event_bus = providers.Singleton(EventBus)

    defect_detected_frame_saver = providers.Singleton(
        DefectDetectedFrameSaver,
        save_dir=Path(config.save_dir()),
        event_bus=event_bus,
    )
    video_saver = providers.Singleton(
        VideoSaver,
        save_dir=Path(config.save_dir()),
        event_bus=event_bus,
    )
    statistics_manager = providers.Singleton(StatisticsManager)
    frame_buffer_manager = providers.Singleton(
        FrameBufferManager,
        event_bus=event_bus,
    )
    video_requester = providers.Singleton(
        VideoRequester,
        frame_buffer_manager=frame_buffer_manager,
    )

    # ── Stream ──
    video_reader = providers.Factory(
        VideoReader,
        event_bus=event_bus,
    )


class Stream:
    def __init__(
        self,
        max_sessions: int,
        paths: list[str],
        container: StreamContainer | None = None,
        save_defect_frame: bool = False,
        save_video: bool = False,
    ):
        self._container = container or StreamContainer()
        self._save_defect_frame = save_defect_frame
        self._save_video = save_video

        self._video_readers = [
            self._container.video_reader(session_id=i, path=path)
            for i, path in enumerate(paths)
        ]

        event_bus = self._container.event_bus()
        event_bus.subscribe(EventHandled, self._container.statistics_manager())
        if self._save_defect_frame:
            event_bus.subscribe(
                DefectDetected, self._container.defect_detected_frame_saver()
            )
        if self._save_video:
            frame_buffer_manager = self._container.frame_buffer_manager()
            for i in range(max_sessions):
                frame_buffer_manager.add_session(i)
            event_bus.subscribe(FramePendingDone, self._container.video_saver())
            event_bus.subscribe(FrameCaptured, frame_buffer_manager)
            event_bus.subscribe(DefectDetected, self._container.video_requester())

    def add_handler(
        self,
        event: type[Event],
        handler: DomainEventHandler,
        session_id: int | None = None,
    ):
        event_bus = self._container.event_bus()
        handler._event_bus = event_bus
        event_bus.subscribe(event, handler, session_id)

    def connect(self):
        for i, video_reader in enumerate(self._video_readers):
            video_reader.connect()
            frame_clipper = self._container.frame_buffer_manager().get_frame_clipper(i)
            frame_clipper.av_input_stream = video_reader.stream

    def start(self):
        for video_reader in self._video_readers:
            video_reader.start()

    def stop(self):
        for video_reader in self._video_readers:
            video_reader.stop()

    def disconnect(self):
        for video_reader in self._video_readers:
            video_reader.disconnect()

    def save_mermaid_flow(self, path: str = "docs/flow.md"):
        save_mermaid_flow(*self._video_readers, path=path)

    def save_statistics(self, path: str = "output/statistics.json"):
        self._container.statistics_manager().save(path)

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def collector(self) -> RawDataCollector:
        return self._collector
