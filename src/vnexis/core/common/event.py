from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

E = TypeVar("E", bound="Event")


@dataclass(kw_only=True, frozen=True)
class Event:
    timestamp: datetime = field(default_factory=datetime.now)


class EventHandler(ABC, Generic[E]):
    logger = logging.getLogger(__name__)

    def handle(self, event: E):
        self.process(event)

    @abstractmethod
    def process(self, event: E):
        pass


class AsyncEventHandler(EventHandler[E]):
    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=f"{self.__class__.__name__}"
        )

    def __del__(self):
        self._executor.shutdown()
        self.logger.info(f"Shutdown {self.__class__.__name__}")

    def handle(self, event: E):
        self._executor.submit(self.process, event)

    @abstractmethod
    def process(self, event: E):
        pass


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: type[Event], event_handler: EventHandler):
        self._subscribers[event.__name__].append(event_handler)

    def publish(self, event: Event):
        for event_handler in self._subscribers[event.__class__.__name__]:
            event_handler.handle(event)


global event_bus
event_bus = EventBus()


def get_glboal_event_bus():
    return event_bus
