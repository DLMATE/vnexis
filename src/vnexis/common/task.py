from abc import ABC, abstractmethod
from typing import Any

from .event import Event


class Task(ABC):
    def __init__(self):
        self._events: list[Event] = []

    @abstractmethod
    def execute(self, data: Any, context: dict):
        pass
