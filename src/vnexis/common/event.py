from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar

E = TypeVar("E", bound="Event")


@dataclass(kw_only=True, frozen=True)
class Event:
    timestamp: datetime = field(default_factory=datetime.now)


class EventHandler(ABC):
    logger = logging.getLogger(__name__)

    @abstractmethod
    def handle(self, event: Event):
        pass


class AsyncEventHandler(EventHandler):
    def __init__(self, event_bus: "EventBus" | None = None, max_workers: int = 1):
        self._event_bus = event_bus
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=f"{self.__class__.__name__}"
        )

    def __del__(self):
        self._executor.shutdown()
        self.logger.info(f"Shutdown {self.__class__.__name__}")

    def handle(self, event: Event):
        self._executor.submit(self._handle_in_background, event)

    @abstractmethod
    def _handle_in_background(self, event: Event):
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
