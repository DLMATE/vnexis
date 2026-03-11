import logging
import threading
from dataclasses import dataclass, field

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.dto import Frame
from vnexis.core.event import FrameBuffered, FramePendingDone
from vnexis.core.service.frame_buffer import FrameBuffer

logger = logging.getLogger(__name__)


@dataclass
class PendingClip:
    session_id: int
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
                session_id=session_id,
                key_frame_idx=key_frame_idx,
                frames=frames,
                max_count=e_idx - s_idx + 1,
            )
            self._pending_clips.append(pending_clip)
            logger.info(
                f"[FrameClipper] Request clipping. session_id: {session_id}, key_frame_idx {key_frame_idx}, s_idx: {s_idx}, e_idx: {e_idx}, max_count: {pending_clip.max_count}, cur_count: {len(pending_clip.frames)}"
            )


class FrameClipperManager:
    def __init__(self):
        self._frame_clippers: dict[int, FrameClipper] = {}

    def add_frame_clipper(
        self,
        client_id: int,
        frame_buffer: FrameBuffer,
        fps: int = 30,
        save_seconds: int = 10,
    ):
        self._frame_clippers[client_id] = FrameClipper(frame_buffer, fps, save_seconds)

    def remove_frame_clipper(self, client_id: int):
        self._frame_clippers.pop(client_id, None)

    def clipping(self, client_id: int, frame: Frame) -> list[PendingClip]:
        return self._frame_clippers[client_id].clipping(frame)

    def request_clip(self, client_id: int, session_id: int, key_frame_idx: int):
        self._frame_clippers[client_id].request_clip(session_id, key_frame_idx)


class FrameClipperHandler(EventHandler):
    def __init__(self, event_bus: EventBus, frame_clipper_manager: FrameClipperManager):
        super().__init__(event_bus)
        self._frame_clipper_manager = frame_clipper_manager

    def handle(self, event: FrameBuffered):
        completed = self._frame_clipper_manager.clipping(event.client_id, event.frame)
        for clip in completed:
            logger.info(f"[FrameClipper] clip completed: {clip.key_frame_idx}")
            self._event_bus.publish(
                FramePendingDone(
                    client_id=event.client_id,
                    session_id=clip.session_id,
                    key_frame_idx=clip.key_frame_idx,
                    frames=clip.frames,
                )
            )
