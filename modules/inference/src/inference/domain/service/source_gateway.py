from abc import ABC, abstractmethod


class SourceGateway(ABC):
    @abstractmethod
    def capture_process(self):
        pass
