import uuid

from vnexis.event import Event, EventBus, EventHandler


class Stream:
    def __init__(self, event_bus: EventBus | None = None):
        self._session_id: uuid.UUID = uuid.uuid4()

        if event_bus is None:
            self._event_bus = EventBus()
        else:
            self._event_bus = event_bus

    def add_handler(self, event: type[Event], handler: EventHandler):
        self._event_bus.subscribe(event, handler)


class Batch:
    def __init__(self, event_bus: EventBus | None = None):
        self._session_id: uuid.UUID = uuid.uuid4()

        if event_bus is None:
            self._event_bus = EventBus()
        else:
            self._event_bus = event_bus

    def add_handler(self, event: type[Event], handler: EventHandler):
        self._event_bus.subscribe(event, handler)
