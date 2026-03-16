import logging
from typing import Iterator

import av
import av.datasets

from vnexis.core.common.event import EventBus
from vnexis.core.domain.event import FrameCaptured
from vnexis.core.domain.service.raw_data_collector import RawDataCollector
from vnexis.core.domain.value_object import Frame
from vnexis.lges.domain.value_object import FrameData

logger = logging.getLogger(__name__)


class VideoReader(RawDataCollector):
    def __init__(self, session_id: int, event_bus: EventBus, path: str):
        super().__init__(session_id, "video", path, event_bus)

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

    def collect(self) -> Iterator[FrameData | None]:
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
            yield FrameData(frame=frame)
            self._event_bus.publish(
                FrameCaptured(session_id=self._session_id, frame=frame)
            )
            # logger.info(f"[{self._session_id}] FrameCaptured: {frame.idx}")
            idx += 1

    def _process(self):
        return super()._process()

    @property
    def stream(self):
        return self._stream
