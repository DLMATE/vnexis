from common.event import EventBus
import logging
from core.dto import Source
from abc import abstractmethod

logger = logging.getLogger(__name__)


class Collector:
    def __init__(self, source: Source, event_bus: EventBus):
        self._source = source
        self._event_bus = event_bus

    def __del__(self):
        self.disconnect()

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
