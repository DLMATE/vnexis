from common.event import EventBus, EventHandler
from core.dto import Frame
from lges.event import KeyFrameDetectionDone
from common.utils import draw_text
import cv2
from collections import deque
import threading
import time
from datetime import datetime
import logging

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc import VideoStreamTrack
from av import VideoFrame

import asyncio

logger = logging.getLogger(__name__)


class Displayer(EventHandler):
    def __init__(self, event_bus: EventBus, width: int = 800, height: int = 600):
        super().__init__(event_bus)
        self._queue: deque[Frame] = deque(maxlen=30 * 2)
        self._lock = threading.Lock()
        self._width = width
        self._height = height
        self._color = (0, 255, 0)  # 초록색
        self._thickness = 2

    def handle(self, event: KeyFrameDetectionDone):
        with self._lock:
            self._queue.append(event.frame)

    def show(self):
        self._is_running = True
        start = time.perf_counter()
        while self._is_running:
            with self._lock:
                qsize = len(self._queue)
                if qsize > 0:
                    frame = self._queue.popleft()
                    end = time.perf_counter()
                else:
                    frame = None
                    end = None
            if not frame:
                # print("frame is none")
                continue
            # data = cv2.resize(frame.data, (self._width, self._height))
            data = frame.data.copy()
            display_data = draw_text(
                data,
                f"idx: {frame.idx}, fps: {int(1 / (end - start))}, qsize: {qsize}",
            )
            cv2.imshow("display", display_data)
            key = cv2.waitKey(30)
            if key == 27:
                self._is_running = False
                break
            start = end

    @property
    def is_running(self) -> bool:
        return self._is_running


class EventFrameStreamTrack(EventHandler, VideoStreamTrack):
    def __init__(self, event_bus: EventBus, width: int = 800, height: int = 600):
        EventHandler.__init__(self, event_bus)
        VideoStreamTrack.__init__(self)
        self._queue: deque[Frame] = deque(maxlen=30 * 2)
        self._lock = threading.Lock()
        self._width = width
        self._height = height
        self._color = (0, 255, 0)  # 초록색
        self._thickness = 2
        self._start_time = time.perf_counter()

    def handle(self, event: KeyFrameDetectionDone):
        frame = Frame(
            idx=event.frame.idx,
            # data=cv2.resize(event.frame.data, (self._width, self._height)),
            data=event.frame.data.copy(),
        )
        with self._lock:
            self._queue.append(frame)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        frame = None

        while frame is None:
            with self._lock:
                qsize = len(self._queue)
                if qsize > 0:
                    frame = self._queue.popleft()
                    end = time.perf_counter()
                else:
                    frame = None
                    end = None
            await asyncio.sleep(0.01)

        display_data = draw_text(
            frame.data,
            f"idx: {frame.idx}, fps: {int(1 / (end - self._start_time))}, qsize: {qsize}",
        )

        video_frame = VideoFrame.from_ndarray(display_data, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        self._start_time = end
        return video_frame


class WebrtcStreamPublisher:
    def __init__(self, video_stream_track: VideoStreamTrack):
        self._video_stream_track = video_stream_track
        # self._pcs: dict[int, set[RTCPeerConnection]] = {}
        self._pcs: set[RTCPeerConnection] = set()

    async def publish(self, connection_info: dict = {}) -> dict:
        pc = RTCPeerConnection()
        # self._pcs.setdefault(camera_id, set()).add(pc)
        self._pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state: {pc.connectionState}")
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                self._video_stream_track.stop()
                await pc.close()
                self._pcs.discard(pc)

        # Offer 설정
        offer_desc = RTCSessionDescription(
            sdp=connection_info["sdp"], type=connection_info["type"]
        )
        await pc.setRemoteDescription(offer_desc)

        pc.addTrack(self._video_stream_track)

        logger.info("Video track added, creating answer...")

        # Answer 생성 및 설정
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        logger.info("Answer created and set as local description")

        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }

    async def unpublish(self):
        for pc in self._pcs:
            await pc.close()
