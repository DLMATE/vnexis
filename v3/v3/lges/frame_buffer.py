from common.event import EventBus, EventHandler
from core.dto import Frame
from lges.event import FrameCaptured, FrameBuffered, PendingDone
from collections import deque
import threading
from dataclasses import dataclass, field
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


# class FrameBuffer(EventHandler):
#     def __init__(self, event_bus: EventBus, max_size: int = 30 * 10):
#         super().__init__(event_bus)
#         self._queue: deque[Frame] = deque(maxlen=max_size)
#         self._lock = threading.Lock()

#     def handle(self, event: FrameCaptured):
#         with self._lock:
#             self._queue.append(event.frame)
#         self._event_bus.publish(FrameBuffered(frame=event.frame))

#     def get_frames(self, s_idx: int, e_idx: int) -> list[Frame]:
#         with self._lock:
#             return [f for f in self._queue if s_idx <= f.idx <= e_idx]


# @dataclass
# class PendingClip:
#     key_idx: int
#     frames: list = field(default_factory=list)
#     max_count: int = 0

#     def add_frame(self, frame: Any):
#         self.frames.append(frame)

#     def is_complete(self) -> bool:
#         return len(self.frames) >= self.max_count


# class FrameClipper(EventHandler):
#     def __init__(
#         self,
#         event_bus: EventBus,
#         frame_buffer: FrameBuffer,
#         fps: int = 30,
#         save_seconds: int = 10,
#     ):
#         super().__init__(event_bus)
#         self._frame_buffer = frame_buffer
#         self._fps = fps
#         self._save_seconds = save_seconds
#         self._keep_count = self._fps * self._save_seconds
#         self._pending_clips: list[PendingClip] = []
#         self._lock = threading.Lock()

#     def handle(self, event: FrameBuffered):
#         try:
#             with self._lock:
#                 for clip in self._pending_clips:
#                     clip.add_frame(event.frame)
#                 completed = [c for c in self._pending_clips if c.is_complete()]
#                 for clip in completed:
#                     self._pending_clips.remove(clip)
#             for clip in completed:
#                 logger.info(f"[FrameClipper] clip completed: {clip.key_idx}")
#                 self._event_bus.publish(
#                     PendingDone(key_idx=clip.key_idx, frames=clip.frames)
#                 )
#         except Exception as e:
#             logger.error(e)

#     def request_clip(self, frame_idx: int):
#         logger.info(f"[FrameClipper] request clip: {frame_idx}")
#         s_idx = max(frame_idx - self._keep_count // 2, 0)
#         e_idx = frame_idx + self._keep_count // 2
#         with self._lock:
#             frames = self._frame_buffer.get_frames(s_idx, e_idx)
#             pending_clip = PendingClip(
#                 key_idx=frame_idx,
#                 frames=frames,
#                 max_count=e_idx - s_idx + 1,
#             )
#             self._pending_clips.append(pending_clip)


class FrameBuffer:
    def __init__(self, max_size: int = 30 * 10):
        self._queue: deque[Frame] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add_frame(self, event: FrameCaptured):
        with self._lock:
            self._queue.append(event.frame)

    def get_frames(self, s_idx: int, e_idx: int) -> list[Frame]:
        with self._lock:
            return [f for f in self._queue if s_idx <= f.idx <= e_idx]


class FrameBufferHandler(EventHandler):
    def __init__(self, event_bus: EventBus, frame_buffer: FrameBuffer):
        super().__init__(event_bus)
        self._frame_buffer = frame_buffer

    def handle(self, event: FrameCaptured):
        self._frame_buffer.add_frame(event)
        self._event_bus.publish(FrameBuffered(frame=event.frame))


@dataclass
class PendingClip:
    key_idx: int
    frames: list = field(default_factory=list)
    max_count: int = 0

    def add_frame(self, frame: Any):
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

    def request_clip(self, frame_idx: int):
        s_idx = max(frame_idx - self._keep_count // 2, 0)
        e_idx = frame_idx + self._keep_count // 2
        with self._lock:
            frames = self._frame_buffer.get_frames(s_idx, e_idx)
            pending_clip = PendingClip(
                key_idx=frame_idx,
                frames=frames,
                max_count=e_idx - s_idx + 1,
            )
            self._pending_clips.append(pending_clip)
            logger.info(
                f"[FrameClipper] request clip: {frame_idx}, s_idx: {s_idx}, e_idx: {e_idx}, max_count: {pending_clip.max_count}, cur_count: {len(pending_clip.frames)}"
            )


class FrameClipperHandler(EventHandler):
    def __init__(self, event_bus: EventBus, frame_clipper: FrameClipper):
        super().__init__(event_bus)
        self._frame_clipper = frame_clipper

    def handle(self, event: FrameBuffered):
        completed = self._frame_clipper.clipping(event.frame)
        for clip in completed:
            logger.info(f"[FrameClipper] clip completed: {clip.key_idx}")
            self._event_bus.publish(
                PendingDone(key_idx=clip.key_idx, frames=clip.frames)
            )
