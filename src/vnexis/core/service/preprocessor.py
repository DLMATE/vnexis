import logging
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor

from vnexis.common.event import EventBus, EventHandler
from vnexis.core.dto import PreprocessResult, RawData, Target
from vnexis.core.event import Preprocessed, RawDataCollected, TargetCreated

logger = logging.getLogger(__name__)


class Preprocessor(EventHandler):
    def __init__(
        self,
        client_id: int,
        event_bus: EventBus,
    ):
        self._client_id = client_id
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Preprocessor"
        )

    def handle(self, event: RawDataCollected):
        if event.client_id != self._client_id:
            return
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


# class Preprocessor(EventHandler):
#     def __init__(
#         self,
#         client_id: int,
#         event_bus: EventBus,
#     ):
#         self._client_id = client_id
#         self._event_bus = event_bus

#         self._is_running: bool = True
#         self._executor = ThreadPoolExecutor(
#             max_workers=1, thread_name_prefix="Preprocessor"
#         )
#         self._thread = threading.Thread(target=self._process, daemon=True)
#         self._queue: deque[RawDataCollected] = deque(maxlen=1)
#         self._lock = threading.Lock()

#         self._thread.start()

#     def __del__(self):
#         self._is_running = False
#         self._thread.join()

#     def handle(self, event: RawDataCollected):
#         if event.client_id != self._client_id:
#             return
#         with self._lock:
#             self._queue.append(event)
#         # self._executor.submit(self._process, event)

#     @abstractmethod
#     def preprocess(self, raw_data: RawData) -> PreprocessResult:
#         pass

#     def _process(self):
#         while self._is_running:
#             try:
#                 with self._lock:
#                     if self._queue:
#                         event = self._queue.popleft()
#                     else:
#                         event = None
#                 if not event:
#                     time.sleep(0.01)
#                     continue
#                 result = self.preprocess(event.raw_data)
#                 self._event_bus.publish(
#                     Preprocessed(
#                         client_id=event.client_id,
#                         session_id=event.session_id,
#                         raw_data=event.raw_data,
#                         result=result,
#                     )
#                 )
#             except Exception as e:
#                 logger.error(f"Error: {e}")


class TargetCreator(EventHandler):
    def __init__(
        self,
        client_id: int,
        event_bus: EventBus,
    ):
        self._client_id = client_id
        self._event_bus = event_bus

        self._is_running: bool = False
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="TargetCreator"
        )

    def handle(self, event: Preprocessed):
        if event.client_id != self._client_id:
            return
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
