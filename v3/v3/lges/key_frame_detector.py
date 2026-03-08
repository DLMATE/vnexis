from core.preprocessor import Preprocessor
from core.dto import Metadata, Frame
from common.event import EventBus
from lges.event import FrameCaptured, KeyFrameDetectionDone, KeyFrameDetected
from concurrent.futures import ThreadPoolExecutor
import random
import logging


logger = logging.getLogger(__name__)


class KeyFrameDetector(Preprocessor[FrameCaptured]):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="KeyFrameDetector"
        )

    def handle(self, event: FrameCaptured):
        self._executor.submit(self._process, event)

    def _process(self, event: FrameCaptured):
        try:
            # frame = event.frame.data
            data = event.frame.data.decode()
            if len(data) != 1:
                raise Exception(f"frame data size is not 1. size: {len(data)}")
            frame = Frame(idx=event.frame.idx, data=data[0].to_ndarray(format="bgr24"))

            done_event = KeyFrameDetectionDone(
                session_id=event.session_id, frame=frame, metadata=Metadata()
            )
            self._event_bus.publish(done_event)

            if frame.idx < 150:
                if frame.idx % 10 == 0:
                    is_triggered = True
                else:
                    is_triggered = False
            else:
                is_triggered = random.random() <= 0.1
            if is_triggered:
                # logger.info("[KeyFrameDetector] KeyFrame 검출됨")
                detected_event = KeyFrameDetected(
                    session_id=event.session_id, frame=frame, metadata=Metadata()
                )
                self._event_bus.publish(detected_event)
        except Exception as e:
            logger.error(f"[KeyFrameDetector] Error. {e}", exc_info=True)
