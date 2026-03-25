import logging
import threading
from collections import deque
from dataclasses import dataclass, field

import av

from vnexis.event import EventBus, FrameCaptured, FramePendingDone
from vnexis.handler.handler import FrameCapturedHandler
from vnexis.vo import Frame

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


@dataclass
class PendingClip:
    key_frame_idx: int
    frames: list = field(default_factory=list)
    max_count: int = 0

    def add_frame(self, frame: Frame):
        self.frames.append(frame)

    def is_complete(self) -> bool:
        return len(self.frames) >= self.max_count


class FrameClipper:
    def __init__(
        self,
        frame_buffer: FrameBuffer,
        fps: int = 30,
        save_seconds: int = 10,
    ):
        self._frame_buffer = frame_buffer
        self._fps = fps
        self._save_seconds = save_seconds
        self._keep_count = self._fps * self._save_seconds
        self._pending_clips: list[PendingClip] = []
        self._lock = threading.Lock()
        self._av_input_stream: av.VideoStream | None = None

    def clipping(self, frame: Frame) -> list[PendingClip]:
        try:
            with self._lock:
                for clip in self._pending_clips:
                    clip.add_frame(frame)
                completed = [c for c in self._pending_clips if c.is_complete()]
                for clip in completed:
                    self._pending_clips.remove(clip)
            return completed
        except Exception as e:
            logger.error(e)

    def request_clip(self, session_id: int, key_frame_idx: int):
        s_idx = max(key_frame_idx - self._keep_count // 2, 0)
        e_idx = key_frame_idx + self._keep_count // 2
        with self._lock:
            frames = self._frame_buffer.get_frames(s_idx, e_idx)
            pending_clip = PendingClip(
                key_frame_idx=key_frame_idx,
                frames=frames,
                max_count=e_idx - s_idx + 1,
            )
            self._pending_clips.append(pending_clip)
            logger.info(
                f"[FrameClipper] Request clipping. session_id: {session_id}, key_frame_idx {key_frame_idx}, s_idx: {s_idx}, e_idx: {e_idx}, max_count: {pending_clip.max_count}, cur_count: {len(pending_clip.frames)}"
            )

    @property
    def av_input_stream(self) -> av.VideoStream | None:
        return self._av_input_stream

    @av_input_stream.setter
    def av_input_stream(self, av_input_stream: av.VideoStream):
        self._av_input_stream = av_input_stream


class FrameBufferManager(FrameCapturedHandler):
    publishes = [FramePendingDone]

    def __init__(self, event_bus: EventBus | None = None):
        super().__init__(event_bus, None)
        self._frame_buffers: dict[int, FrameBuffer] = dict()
        self._frame_clippers: dict[int, FrameClipper] = dict()

    def add_session(self, session_id: int) -> None:
        self._frame_buffers[session_id] = FrameBuffer()
        self._frame_clippers[session_id] = FrameClipper(self._frame_buffers[session_id])

    def process(self, event: FrameCaptured) -> None:
        frame_buffer = self._frame_buffers[event.session_id]
        frame_clipper = self._frame_clippers[event.session_id]

        frame_buffer.add_frame(event.frame)
        completed = frame_clipper.clipping(event.frame)
        for clip in completed:
            self.logger.info(f"[FrameClipper] clip completed: {clip.key_frame_idx}")
            self._event_bus.publish(
                FramePendingDone(
                    session_id=event.session_id,
                    key_frame_idx=clip.key_frame_idx,
                    frames=clip.frames,
                    av_input_stream=frame_clipper.av_input_stream,
                ),
                event.session_id,
            )

    def get_frame_clipper(self, session_id: int) -> FrameClipper:
        return self._frame_clippers[session_id]
