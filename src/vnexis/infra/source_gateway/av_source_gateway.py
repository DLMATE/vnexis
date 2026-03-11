import logging
from typing import Iterator

import av
import av.datasets

from vnexis.common.event import EventBus
from vnexis.core.dto import Frame
from vnexis.core.service.source_gateway import SourceGateway

logger = logging.getLogger(__name__)


class AvSourceGateway(SourceGateway):
    def __init__(self, path: str, event_bus: EventBus):
        super().__init__(path, "video", event_bus)

        self._container = None
        self._stream = None
        self._fps = None

    def connect(self):
        self._container = av.open(av.datasets.curated(self._path))
        self._stream = self._container.streams.video[0]
        self._fps = float(self._stream.average_rate or 30)
        self._frame_delay = 1.0 / self._fps
        logger.info("Video 연결 성공!")

    def disconnect(self):
        if self._is_running:
            self.stop()
        if self._container:
            self._container.close()
        self._container = None
        self._stream = None
        self._fps = None
        self._frame_delay = None

    def start(self):
        self._is_running = True
        self._thread.start()

    def stop(self):
        self._is_running = False
        self._thread.join()

    def read(self) -> Iterator[Frame | None]:
        idx = 0
        for packet in self._container.demux(self._stream):
            if packet.size == 0 or packet.dts is None:
                yield None
            yield packet
            idx += 1

    @property
    def stream(self):
        return self._stream
