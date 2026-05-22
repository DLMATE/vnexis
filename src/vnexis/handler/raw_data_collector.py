import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Generic, Iterator, Literal

import av

from vnexis.event import EventBus, FrameCaptured, RawDataCollected
from vnexis.vo import Frame, RawData, TRawData

logger = logging.getLogger(__name__)


class RawDataCollector(ABC, Generic[TRawData]):
    publishes: list[type] = [RawDataCollected]

    def __init__(
        self,
        session_id: int,
        source_type: Literal["rtsp", "file", "nas", "camera", "db"],
        path: str,
        event_bus: EventBus | None = None,
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
            self._event_bus.publish(event, self._session_id)
            # logger.info(f"[{self._session_id}] RawDataCollected: {self._session_id}")
            if not self._is_running:
                break
            time.sleep(self._delay)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @event_bus.setter
    def event_bus(self, event_bus: EventBus):
        self._event_bus = event_bus


class VideoReader(RawDataCollector[Frame]):
    publishes = [RawDataCollected, FrameCaptured]

    def __init__(self, session_id: int, path: str, event_bus: EventBus | None = None):
        super().__init__(session_id, "video", path, event_bus)

        self._container = None
        self._stream = None
        self._fps = None

    def connect(self):
        self._container = av.open(self._path)
        self._stream = self._container.streams.video[0]
        self._stream.codec_context.thread_count = 2
        self._stream.codec_context.thread_type = "AUTO"
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

    def collect(self) -> Iterator[Frame | None]:
        idx = 0
        for packet in self._container.demux(self._stream):
            if packet.size == 0 or packet.dts is None:
                yield None
                continue
            t0 = time.time()
            data = packet.decode()
            t1 = time.time()
            if len(data) != 1:
                yield None
                continue
                # raise Exception(f"frame data size is not 1. size: {len(data)}")
            # frame = Frame(idx=idx, raw=packet, data=data[0].to_ndarray(format="bgr24"))
            data = data[0].reformat(width=640, height=640)
            data = data.to_ndarray(format="bgr24")
            frame = Frame(idx=idx, raw=packet, data=data)
            t2 = time.time()
            logger.info(
                f"[Collect] session_id: {self._session_id}, decode: {(t1 - t0) * 1000:.4f} ms | numpy: {(t2 - t1) * 1000:.4f} ms"
            )
            yield frame
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
