import logging
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.dto import DetectResult, Target
from vnexis.core.event import (
    DefectDetected,
    DetectionDone,
    TargetCreated,
)

logger = logging.getLogger(__name__)


class Detector(EventHandler):
    def __init__(
        self,
        client_id: int,
        event_bus: EventBus,
    ):
        self._client_id = client_id
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Detector"
        )

    def handle(self, event: TargetCreated):
        if event.client_id != self._client_id:
            return
        self._executor.submit(self._process, event)

    @abstractmethod
    def detect(self, target: Target) -> tuple[bool, DetectResult]:
        pass

    def _process(self, event: TargetCreated):
        try:
            is_defect, detect_result = self.detect(event.target)
            self._event_bus.publish(
                DetectionDone(
                    client_id=event.client_id,
                    session_id=event.session_id,
                    raw_data=event.raw_data,
                    preprocess_result=event.preprocess_result,
                    target=event.target,
                    detect_result=detect_result,
                )
            )
            if is_defect:
                self._event_bus.publish(
                    DefectDetected(
                        client_id=event.client_id,
                        session_id=event.session_id,
                        raw_data=event.raw_data,
                        preprocess_result=event.preprocess_result,
                        target=event.target,
                        detect_result=detect_result,
                    )
                )

        except Exception as e:
            logger.error(f"Error: {e}")
