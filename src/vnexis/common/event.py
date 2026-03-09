from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar

E = TypeVar("E", bound="Event")


@dataclass(kw_only=True, frozen=True)
class Event:
    timestamp: datetime = field(default_factory=datetime.now)


class EventHandler(ABC):
    def __init__(self, event_bus: "EventBus" | None = None):
        self._event_bus = event_bus

    @abstractmethod
    def handle(self, event: Event):
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
