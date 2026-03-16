"""Test print_full_flow with a simulated handler graph (single EventBus + session_id routing)."""
from dataclasses import dataclass

from vnexis.event import (
    DefectDetected,
    EventBus,
    FrameBuffered,
    FrameCaptured,
    FramePendingDone,
    RawDataCollected,
    print_full_flow,
    save_mermaid_flow,
)
from vnexis.event.base import AsyncEventHandler
from vnexis.event.event import DomainEvent
from vnexis.handler import (
    DomainEventHandler,
    FrameBuffering,
    FrameBufferManager,
    FrameClipperManager,
    FrameClipping,
    RawDataCollectedHandler,
)


# ── Stub events ──


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetectionDone(DomainEvent):
    pass


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetected(DomainEvent):
    pass


@dataclass(kw_only=True, frozen=True)
class FaultFrameDetected(DefectDetected):
    pass


# ── Stub handlers ──


class StubCollector:
    """Simulates VideoReader without real video dependencies."""

    publishes = [RawDataCollected, FrameCaptured]

    def __init__(self, session_id: int, event_bus: EventBus):
        self._session_id = session_id
        self._event_bus = event_bus


class StubKeyFrameDetector(RawDataCollectedHandler):
    publishes = [KeyFrameDetectionDone]

    def __init__(self, session_id: int, event_bus: EventBus):
        super().__init__(event_bus, session_id)

    def process(self, event):
        pass


class StubTriggerTracker(DomainEventHandler[KeyFrameDetectionDone]):
    publishes = [KeyFrameDetected]

    def __init__(self, session_id: int, event_bus: EventBus):
        super().__init__(event_bus, session_id)

    def process(self, event):
        pass


class StubFaultFrameDetector(DomainEventHandler):
    publishes = [FaultFrameDetected]

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus, None)

    def process(self, event):
        pass


class StubWebDisplayer(AsyncEventHandler):
    def process(self, event):
        pass


class StubFaultFrameSaver(AsyncEventHandler):
    def process(self, event):
        pass


class StubVideoRequester(AsyncEventHandler):
    def process(self, event):
        pass


class StubVideoSaver(AsyncEventHandler):
    def process(self, event):
        pass


def main():
    bus = EventBus()

    frame_buffer_manager = FrameBufferManager()
    frame_clipper_manager = FrameClipperManager()

    frame_buffering = FrameBuffering(
        event_bus=bus, frame_buffer_manager=frame_buffer_manager
    )
    frame_clipping = FrameClipping(
        event_bus=bus, frame_clipper_manager=frame_clipper_manager
    )

    fault_frame_saver = StubFaultFrameSaver()
    video_requester = StubVideoRequester()
    video_saver = StubVideoSaver()
    web_displayer = StubWebDisplayer()
    fault_frame_detector = StubFaultFrameDetector(bus)

    # Global subscriptions (session_id=None)
    bus.subscribe(FrameCaptured, frame_buffering)
    bus.subscribe(FrameBuffered, frame_clipping)
    bus.subscribe(DefectDetected, fault_frame_saver)
    bus.subscribe(DefectDetected, video_requester)
    bus.subscribe(FramePendingDone, video_saver)
    bus.subscribe(KeyFrameDetected, fault_frame_detector)

    collectors = []
    for client_id in range(2):
        collector = StubCollector(client_id, bus)
        key_frame_detector = StubKeyFrameDetector(client_id, bus)
        trigger_tracker = StubTriggerTracker(client_id, bus)

        # Session-scoped subscriptions
        bus.subscribe(RawDataCollected, key_frame_detector, session_id=client_id)
        bus.subscribe(KeyFrameDetectionDone, trigger_tracker, session_id=client_id)
        bus.subscribe(KeyFrameDetectionDone, web_displayer, session_id=client_id)

        collectors.append(collector)

    print("=== CLI Flow ===")
    print_full_flow(*collectors)

    print("\n=== Mermaid Flow ===")
    save_mermaid_flow(*collectors, path="docs/flow.md")
    print("Saved to docs/flow.md")


if __name__ == "__main__":
    main()
