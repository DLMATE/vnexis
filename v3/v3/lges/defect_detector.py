from core.detector import Detector
from common.event import EventBus
from lges.event import KeyFrameDetected
from core.event import DetectionDone, DefectDetected
from concurrent.futures import ThreadPoolExecutor
import random
import logging
from .frame_buffer import FrameClipper


logger = logging.getLogger(__name__)


class DefectDetector(Detector[KeyFrameDetected]):
    def __init__(self, event_bus: EventBus, frame_clipper: FrameClipper):
        super().__init__(event_bus)
        self._frame_clipper = frame_clipper
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="DefectDetector"
        )

    def handle(self, event: KeyFrameDetected):
        self._executor.submit(self._process, event)

    def _process(self, event: KeyFrameDetected):
        try:
            is_defected = random.random() <= 0.1
            done_event = DetectionDone(
                session_id=event.session_id, is_defect=is_defected
            )
            self._event_bus.publish(done_event)

            if is_defected:
                logger.info("[DefectDetector] 불량 검출됨")
                detected_event = DefectDetected(
                    session_id=event.session_id, frame=event.frame, result={}
                )
                self._frame_clipper.request_clip(event.frame.idx)
                self._event_bus.publish(detected_event)
        except Exception as e:
            logger.error(e)
