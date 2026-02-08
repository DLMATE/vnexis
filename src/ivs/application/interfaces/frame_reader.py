from abc import ABC, abstractmethod

from ivs.common.event import EventBus


class FrameReader(ABC):
    def __init__(self, path: str, client_id: int, event_bus: EventBus):
        self._path = path
        self._client_id = client_id
        self._event_bus = event_bus
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def __call__(self):
        pass

    @abstractmethod
    def process(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class FrameReaderResistry:
    @abstractmethod
    def register(self, client_id: int, path: str) -> FrameReader:
        pass

    @abstractmethod
    def unregister(self, client_id: int):
        pass

    @abstractmethod
    def is_registered(self, client_id: int) -> bool:
        pass

    @abstractmethod
    def get(self, client_id: int) -> FrameReader:
        pass
