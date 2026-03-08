from core.collector import Collector
from core.dto import Source, Frame
from lges.event import FrameCaptured
from common.event import EventBus

import cv2
import threading
import time
import logging
import av
import av.datasets


logger = logging.getLogger(__name__)


class VideoCapture(Collector):
    def __init__(self, source: Source, event_bus: EventBus):
        super().__init__(source, event_bus)

        self._cap = None
        self._fps = None
        self._frame_delay = None
        self._is_running = False
        self._thread = threading.Thread(target=self._process, daemon=True)

    def connect(self):
        self._cap = cv2.VideoCapture(self._source.path)
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_delay = 1.0 / self._fps
        logger.info("Video 연결 중...")
        while not self._cap.isOpened():
            time.sleep(self._frame_delay)
        logger.info("Video 연결 성공!")

    def disconnect(self):
        if self._is_running:
            self.stop()
        if self._cap:
            self._cap.release()
        self._cap = None
        self._fps = None
        self._frame_delay = None

    def start(self):
        self._is_running = True
        self._thread.start()

    def stop(self):
        self._is_running = False
        self._thread.join()

    def _process(self):
        idx = 0
        while self._is_running:
            ret, frame = self._cap.read()
            if not ret:
                break
            event = FrameCaptured(session_id=idx, frame=Frame(idx=idx, data=frame))
            self._event_bus.publish(event)
            idx += 1
            time.sleep(self._frame_delay)


class AvVideoCapture(Collector):
    def __init__(self, source: Source, event_bus: EventBus):
        super().__init__(source, event_bus)

        self._container = None
        self._stream = None
        self._fps = None
        self._frame_delay = None
        self._is_running = False
        self._thread = threading.Thread(target=self._process, daemon=True)

    def connect(self):
        self._container = av.open(av.datasets.curated(self._source.path))
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

    def _process(self):
        idx = 0
        for packet in self._container.demux(self._stream):
            try:
                if not self._is_running:
                    break
                if packet.size == 0 or packet.dts is None:
                    continue
                # if packet.dts is None:
                #     logger.warn(f"{idx}'s packet's dts is None!")
                # logger.info(
                #     f"{idx} pts: {packet.pts}, dts: {packet.dts}, is_keyframe: {packet.is_keyframe}"
                # )
                event = FrameCaptured(
                    session_id=idx,
                    frame=Frame(idx=idx, data=packet),
                )
                self._event_bus.publish(event)
                idx += 1
                time.sleep(self._frame_delay)
            except Exception as e:
                logger.error(f"[VideoCapture] Error. {e}")

    @property
    def stream(self):
        return self._stream
