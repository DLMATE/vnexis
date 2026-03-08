import logging
import threading
from abc import abstractmethod
from collections import deque
from typing import Any

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.event import DetectionDone, Preprocessed

logger = logging.getLogger(__name__)


class Displayer(EventHandler):
    def __init__(
        self,
        event_bus: EventBus,
        width: int = 800,
        height: int = 600,
    ):
        super().__init__(event_bus)
        self._width = width
        self._height = height

        self._is_running: bool = False
        self._queue: deque[Preprocessed] = deque(maxlen=30 * 2)
        self._lock = threading.Lock()

    def handle(self, event: Preprocessed):
        with self._lock:
            self._queue.append(event)

    @abstractmethod
    def visualize(self, result: Any) -> None:
        pass

    def _process(self, event: Preprocessed):
        try:
            is_defect, detect_result = self.visualize(event.target)
            self._event_bus.publish(
                DetectionDone(
                    client_id=event.client_id,
                    session_id=event.session_id,
                    target=event.target,
                    detect_result=detect_result,
                )
            )
            if is_defect:
                self._event_bus.publish(
                    DefectDetected(
                        client_id=event.client_id,
                        session_id=event.session_id,
                        target=event.target,
                        detect_result=detect_result,
                    )
                )
        except Exception as e:
            logger.error(f"Error: {e}")
