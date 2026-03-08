import threading
import time
from abc import ABC, abstractmethod
from typing import Iterator, Literal

from vnexis.common.event import EventBus
from vnexis.core.entity.raw_data import RawData
from vnexis.core.event import RawDataCollected


class SourceGateway(ABC):
    def __init__(
        self,
        source_type: Literal["rtsp", "file", "nas", "camera", "db"],
        path: str,
        event_bus: EventBus,
        delay: float = 0.1,
    ):
        self._source_type = source_type
        self._path = path
        self._event_bus = event_bus
        self._delay = delay

        self._is_running: bool = False
        self._thread: threading.Thread = threading.Thread(
            target=self._process, daemon=True
        )

    @property
    def media_type(self) -> str:
        return self._media_type

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
            event = RawDataCollected(raw_data=raw_data)
            self._event_bus.publish(event)
            if not self._is_running:
                break
            time.sleep(self._delay)
