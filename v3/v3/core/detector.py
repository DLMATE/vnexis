import logging
from typing import TypeVar, Generic
from abc import abstractmethod

from core.event import TargetCreated
from common.event import EventHandler


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=TargetCreated)


class Detector(EventHandler, Generic[T]):
    @abstractmethod
    def handle(self, event: T):
        pass
