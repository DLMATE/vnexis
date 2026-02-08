import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import numpy as np

from ivs.common.event import EventBus, EventHandler, event_bus
from ivs.domain.entities.detection import DetectionResult, Frame
from ivs.domain.events import DetectionDoneEvent, FaultDetectedEvent, FrameCapturedEvent


class Detector(EventHandler):
    def __init__(
        self,
        detect_fn: Callable[[np.ndarray], Any],
        client_id: int = 0,
        event_bus: EventBus = event_bus,
    ):
        self._client_id = client_id
        self._event_bus = event_bus
        self._detect_fn = detect_fn
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Detector"
        )

    def handle(self, event: FrameCapturedEvent):
        if event.client_id != self._client_id:
            return
        self._executor.submit(self._process, event)

    def _detect(self, frame: Frame) -> DetectionResult:
        start = time.perf_counter()
        result = self._detect_fn(frame.data)
        end = time.perf_counter()
        return DetectionResult.create(result, end - start)

    def _process(self, event: FrameCapturedEvent):
        print(f"Detector Event Consumed: {event.frame.idx}")
        try:
            detection_result = self._detect(event.frame)
            self._event_bus.publish(
                DetectionDoneEvent(
                    client_id=self._client_id,
                    frame=event.frame,
                    detection_result=detection_result,
                )
            )
            if detection_result.is_detected:
                self._event_bus.publish(
                    FaultDetectedEvent(
                        client_id=self._client_id,
                        frame=event.frame,
                        detection_result=detection_result,
                    )
                )
        except Exception:
            print(f"Detector Exception: {traceback.format_exc()}")
