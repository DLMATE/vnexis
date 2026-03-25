import logging

from vnexis.event import AsyncEventHandler, DefectDetected
from vnexis.handler.frame_buffer import FrameBufferManager

logger = logging.getLogger(__name__)


class VideoRequester(AsyncEventHandler[DefectDetected]):
    def __init__(self, frame_buffer_manager: FrameBufferManager):
        super().__init__()
        self._frame_buffer_manager = frame_buffer_manager

    def process(self, event: DefectDetected):
        self._frame_buffer_manager.get_frame_clipper(event.session_id).request_clip(
            event.session_id, event.frame.idx
        )
