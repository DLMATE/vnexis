import logging
from typing import Iterator

import av
import av.datasets

from vnexis.common.event import EventBus
from vnexis.core.dto import Frame
from vnexis.core.event import FrameCaptured
from vnexis.core.service.source_gateway import SourceGateway
from vnexis.lges.dto import LgesRawData

logger = logging.getLogger(__name__)


class AvSourceGateway(SourceGateway):
    def __init__(self, client_id: int, path: str, event_bus: EventBus):
        super().__init__(client_id, "video", path, event_bus)

        self._container = None
        self._stream = None
        self._fps = None

    def connect(self):
        # self._container = av.open(av.datasets.curated(self._path))
        self._container = av.open(self._path)
        self._stream = self._container.streams.video[0]
        self._fps = float(self._stream.average_rate or 30)
        self._delay = 1.0 / self._fps
        logger.info("Video 연결 성공!")

    def disconnect(self):
        if self._is_running:
            self.stop()
        if self._container:
            self._container.close()
        self._container = None
        self._stream = None
        self._fps = None
        self._delay = None

    def start(self):
        self._is_running = True
        self._thread.start()

    def stop(self):
        self._is_running = False
        self._thread.join()

    def collect(self) -> Iterator[LgesRawData | None]:
        idx = 0
        for packet in self._container.demux(self._stream):
            if packet.size == 0 or packet.dts is None:
                yield None
                continue
            data = packet.decode()
            if len(data) != 1:
                yield None
                continue
                # raise Exception(f"frame data size is not 1. size: {len(data)}")
            frame = Frame(idx=idx, raw=packet, data=data[0].to_ndarray(format="bgr24"))
            yield LgesRawData(
                frame=Frame(
                    idx=idx, raw=packet, data=data[0].to_ndarray(format="bgr24")
                )
            )
            self._event_bus.publish(
                FrameCaptured(client_id=self._client_id, session_id=idx, frame=frame)
            )
            idx += 1

    @property
    def stream(self):
        return self._stream
