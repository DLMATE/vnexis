import logging

from lges.event import FaultFrameDetected
from vnexis.event import AsyncEventHandler
from vnexis.handler.frame_clipper import FrameClipperManager

logger = logging.getLogger(__name__)


class VideoRequester(AsyncEventHandler[FaultFrameDetected]):
    def __init__(self, frame_clipper_manager: FrameClipperManager):
        super().__init__()
        self._frame_clipper_manager = frame_clipper_manager

    def process(self, event: FaultFrameDetected):
        self._frame_clipper_manager.request_clip(event.session_id, event.frame.idx)
