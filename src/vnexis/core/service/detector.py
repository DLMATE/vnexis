import logging
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.entity.target import DetectResult, Target
from vnexis.core.event import (
    DefectDetected,
    DetectionDone,
    Postprocessed,
    PostprocessResult,
    TargetCreated,
)

logger = logging.getLogger(__name__)


class Detector(EventHandler):
    def __init__(
        self,
        event_bus: EventBus,
    ):
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Detector"
        )

    def handle(self, event: TargetCreated):
        self._executor.submit(self._process, event)

    @abstractmethod
    def detect(self, target: Target) -> tuple[bool, DetectResult]:
        pass

    def _process(self, event: TargetCreated):
        try:
            detect_result = self.detect(event.target)
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
        except Exception as e:
            logger.error(f"Error: {e}")


class Postprocessor(EventHandler):
    def __init__(
        self,
        event_bus: EventBus,
    ):
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Postprocessor"
        )

    def handle(self, event: DetectionDone):
        self._executor.submit(self._process, event)

    @abstractmethod
    def postprocess(self, event: DetectionDone) -> tuple[bool, PostprocessResult]:
        pass

    def _process(self, event: DetectionDone):
        try:
            is_defect, postprocess_result = self.postprocess(event)
            self._event_bus.publish(
                Postprocessed(
                    client_id=event.client_id,
                    session_id=event.session_id,
                    raw_data=event.raw_data,
                    preprocess_result=event.preprocess_result,
                    target=event.target,
                    detect_result=event.detect_result,
                    postprocess_result=postprocess_result,
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
                        detect_result=event.detect_result,
                        postprocess_result=postprocess_result,
                    )
                )
        except Exception as e:
            logger.error(f"Error: {e}")
