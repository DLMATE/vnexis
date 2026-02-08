from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(kw_only=True, frozen=True)
class Event:
    timestamp: datetime = field(default_factory=datetime.now)


class EventHandler(ABC):
    @abstractmethod
    def handle(self, event: Event):
        pass


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: type[Event], event_handler: EventHandler):
        self._subscribers[event.__name__].append(event_handler)

    def publish(self, event: Event):
        # print(f"event type: {event_type}")
        # print(f"subscribers: {self._subscribers[event_type]}")

        for event_handler in self._subscribers[event.__class__.__name__]:
            event_handler.handle(event)


event_bus = EventBus()
