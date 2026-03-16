import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Iterator, Literal

from vnexis.core.common.event import EventBus
from vnexis.core.domain.event import RawDataCollected
from vnexis.core.domain.value_object import RawData

logger = logging.getLogger(__name__)


class RawDataCollector(ABC):
    def __init__(
        self,
        session_id: int,
        source_type: Literal["rtsp", "file", "nas", "camera", "db"],
        path: str,
        event_bus: EventBus = EventBus(),
        delay: float = 0.1,
    ):
        self._session_id = session_id
        self._source_type = source_type
        self._path = path
        self._event_bus = event_bus
        self._delay = delay

        self._is_running: bool = False
        self._thread: threading.Thread = threading.Thread(
            target=self._process, daemon=True
        )

    @property
    def source_type(self) -> str:
        return self._source_type

    def __del__(self):
        self.disconnect()

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def collect(self) -> Iterator[RawData | None]:
        pass

    def start(self):
        self._is_running = True
        self._thread.start()

    def stop(self):
        self._is_running = False
        self._thread.join()

    def _process(self):
        for raw_data in self.collect():
            if not raw_data:
                continue
            event = RawDataCollected(session_id=self._session_id, raw_data=raw_data)
            self._event_bus.publish(event)
            # logger.info(f"[{self._session_id}] RawDataCollected: {session_id}")
            if not self._is_running:
                break
            time.sleep(self._delay)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus
