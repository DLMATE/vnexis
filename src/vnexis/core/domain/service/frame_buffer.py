import logging
import threading
from collections import deque

from vnexis.core.dto import Frame

logger = logging.getLogger(__name__)


class FrameBuffer:
    def __init__(self, max_size: int = 30 * 10):
        self._queue: deque[Frame] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add_frame(self, frame: Frame):
        with self._lock:
            self._queue.append(frame)

    def get_frames(self, s_idx: int, e_idx: int) -> list[Frame]:
        with self._lock:
            return [f for f in self._queue if s_idx <= f.idx <= e_idx]

    def get_recently_frame(self) -> Frame:
        with self._lock:
            return self._queue[-1]


class FrameBufferManager:
    def __init__(self):
        self._frame_buffers: dict[int, FrameBuffer] = {}

    def add_buffer(self, client_id: int, max_size: int = 30 * 10):
        if client_id in self._frame_buffers.keys():
            raise Exception(f"FrameBuffer already exists. client_id: {client_id}")
        self._frame_buffers[client_id] = FrameBuffer(max_size)

    def get_buffer(self, client_id) -> FrameBuffer:
        return self._frame_buffers[client_id]

    def clear_buffer(self, client_id: int):
        self._frame_buffers.pop(client_id, None)

    def add_frame(self, client_id: int, frame: Frame):
        self._frame_buffers[client_id].add_frame(frame)

    def get_frames(self, client_id: int, s_idx: int, e_idx: int) -> list[Frame]:
        return self._frame_buffers[client_id].get_frames(s_idx, e_idx)
