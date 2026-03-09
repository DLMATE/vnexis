import logging
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.entity.raw_data import RawData
from vnexis.core.entity.target import PreprocessResult, Target
from vnexis.core.event import Preprocessed, RawDataCollected, TargetCreated

logger = logging.getLogger(__name__)


class Preprocessor(EventHandler):
    def __init__(
        self,
        event_bus: EventBus,
    ):
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Preprocessor"
        )

    def handle(self, event: RawDataCollected):
        self._executor.submit(self._process, event)

    @abstractmethod
    def preprocess(self, raw_data: RawData) -> PreprocessResult:
        pass

    def _process(self, event: RawDataCollected):
        try:
            result = self.preprocess(event.raw_data)
            self._event_bus.publish(
                Preprocessed(
                    client_id=event.client_id,
                    session_id=event.session_id,
                    raw_data=event.raw_data,
                    result=result,
                )
            )
        except Exception as e:
            logger.error(f"Error: {e}")


class TargetCreator(EventHandler):
    def __init__(
        self,
        event_bus: EventBus,
    ):
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="TargetCreator"
        )

    def handle(self, event: RawDataCollected):
        self._executor.submit(self._process, event)

    @abstractmethod
    def create_target(
        self, raw_data: RawData, preprocess_result: PreprocessResult
    ) -> Target | None:
        pass

    def _process(self, event: Preprocessed):
        try:
            target = self.create_target(event.raw_data, event.result)
            if target:
                self._event_bus.publish(
                    TargetCreated(
                        client_id=event.client_id,
                        session_id=event.session_id,
                        raw_data=event.raw_data,
                        preprocess_result=event.result,
                        target=target,
                    )
                )
        except Exception as e:
            logger.error(f"Error: {e}")
