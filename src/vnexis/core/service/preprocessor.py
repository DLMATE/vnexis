import logging
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.entity.raw_data import RawData
from vnexis.core.entity.target import Target
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
    def preprocess(self, raw_data: RawData) -> tuple[Any, Target]:
        pass

    def _process(self, event: RawDataCollected):
        try:
            result, target = self.preprocess(event.raw_data)
            if not target:
                self._event_bus.publish(
                    TargetCreated(
                        client_id=event.client_id,
                        session_id=event.session_id,
                        target=target,
                    )
                )
            self._event_bus.publish(
                Preprocessed(
                    client_id=event.client_id,
                    session_id=event.session_id,
                    result=result,
                )
            )
        except Exception as e:
            logger.error(f"Error: {e}")
