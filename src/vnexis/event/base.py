from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, Literal, TypeVar

TEvent = TypeVar("TEvent", bound="Event")
# TDomainEvent = TypeVar("TDomainEvent", bound="DomainEvent")


@dataclass(kw_only=True, frozen=True)
class Event:
    timestamp: datetime = field(default_factory=datetime.now)


class EventHandler(ABC, Generic[TEvent]):
    logger = logging.getLogger(__name__)
    publishes: list[type[Event]] = []

    def handle(self, event: TEvent):
        try:
            self._run(event)
        except Exception:
            self.logger.exception(
                f"[{self.__class__.__name__}] Error processing {type(event).__name__}"
            )

    @abstractmethod
    def process(self, event: TEvent):
        pass

    def _run(self, event: TEvent):
        self.process(event)


class AsyncEventHandler(EventHandler[TEvent]):
    def __init__(
        self, max_workers: int = 1, type: Literal["thread", "process"] = "thread"
    ):
        if type == "thread":
            self._executor = ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix=f"{self.__class__.__name__}"
            )
        else:
            self._executor = ProcessPoolExecutor(max_workers=max_workers)

    def __del__(self):
        self._executor.shutdown(wait=True)
        try:
            self.logger.info(f"Shutdown {self.__class__.__name__}")
        except Exception:
            print(f"Shutdown {self.__class__.__name__}")

    def handle(self, event: TEvent):
        try:
            self._executor.submit(super().handle, event)
        except RuntimeError:
            pass

    @abstractmethod
    def process(self, event: TEvent):
        pass


class EventBus:
    def __init__(self, name: str = "global"):
        self.name = name
        self._subscribers: dict[int | None, dict[str, list[EventHandler]]] = (
            defaultdict(lambda: defaultdict(list))
        )

    def subscribe(
        self,
        event: type[Event],
        event_handler: EventHandler,
        session_id: int | None = None,
    ):
        if event_handler not in self._subscribers[session_id][event.__name__]:
            self._subscribers[session_id][event.__name__].append(event_handler)

    def publish(self, event: Event, session_id: int | None = None):
        for cls in type(event).__mro__:
            # session-scoped subscribers
            if session_id is not None:
                for event_handler in self._subscribers[session_id].get(
                    cls.__name__, []
                ):
                    event_handler.handle(event)
            # global subscribers
            for event_handler in self._subscribers[None].get(cls.__name__, []):
                event_handler.handle(event)


global event_bus
event_bus = EventBus()


def get_glboal_event_bus():
    return event_bus


# @dataclass(kw_only=True, frozen=True)
# class DomainEvent(Event):
#     session_id: int


# @dataclass(kw_only=True, frozen=True)
# class EventHandled(DomainEvent):
#     name: str
#     duration: float


# class DomainHandlerMixin(Generic[TDomainEvent]):
#     def __init__(
#         self, event_bus: EventBus = event_bus, session_id: int | None = None
#     ) -> None:
#         self._event_bus = event_bus
#         self._session_id = session_id

#     def _run(self, event: TDomainEvent):
#         s = time.perf_counter()
#         super()._run(event)
#         e = time.perf_counter()
#         self._event_bus.publish(
#             EventHandled(
#                 session_id=event.session_id,
#                 name=self.__class__.__name__,
#                 duration=e - s,
#             )
#         )

#     @property
#     def event_bus(self) -> EventBus:
#         return self._event_bus


# class DomainEventHandler(DomainHandlerMixin[TDomainEvent], EventHandler[TDomainEvent]):
#     pass


# class DomainEventHandler(
#     DomainHandlerMixin[TDomainEvent], AsyncEventHandler[TDomainEvent]
# ):
#     pass


# ── Flow Diagram ──────────────────────────────────────────


def _handler_display_name(handler) -> str:
    name = handler.__class__.__name__
    session_id = getattr(handler, "_session_id", None)
    if session_id is not None:
        name = f"{name}[{session_id}]"
    return name


def _find_subscribers(
    bus: EventBus,
    event_name: str,
    session_id: int | None,
) -> list[EventHandler]:
    subs: list[EventHandler] = []
    if session_id is not None:
        subs.extend(bus._subscribers.get(session_id, {}).get(event_name, []))
    subs.extend(bus._subscribers.get(None, {}).get(event_name, []))
    return subs


def _print_items(items: list, prefix: str, visited: set, lines: list[str]):
    for j, item in enumerate(items):
        is_last = j == len(items) - 1
        connector = "└──→" if is_last else "├──→"
        cont = "      " if is_last else "│     "

        if item[0] == "handler":
            sub = item[1]
            sub_name = _handler_display_name(sub)
            if id(sub) in visited:
                lines.append(f"{prefix}{connector} {sub_name} (...)")
                continue
            visited.add(id(sub))
            lines.append(f"{prefix}{connector} {sub_name}")
            _print_publishes(sub, prefix + cont, visited, lines)

        elif item[0] == "extends":
            parent_type = item[1]
            parent_subs = item[2]
            ext_connector = "└──↳" if is_last else "├──↳"
            lines.append(f"{prefix}{ext_connector} (extends {parent_type.__name__})")
            ext_items = [("handler", s) for s in parent_subs]
            _print_items(ext_items, prefix + cont, visited, lines)


def _print_publishes(handler, prefix: str, visited: set, lines: list[str]):
    bus: EventBus | None = getattr(handler, "_event_bus", None)
    events: list[type[Event]] = getattr(handler, "publishes", [])
    if not bus or not events:
        return

    session_id: int | None = getattr(handler, "_session_id", None)

    for i, event_type in enumerate(events):
        is_last = i == len(events) - 1
        connector = "└──→" if is_last else "├──→"
        cont = "      " if is_last else "│     "

        lines.append(f"{prefix}{connector} [{event_type.__name__}]")

        items: list = []

        # Direct subscribers (session-scoped + global)
        direct = _find_subscribers(bus, event_type.__name__, session_id)
        for sub in direct:
            items.append(("handler", sub))

        # MRO parent events with subscribers (extends)
        for cls in event_type.__mro__[1:]:
            if cls is object or cls is Event or not issubclass(cls, Event):
                continue
            parent_subs = [
                s
                for s in _find_subscribers(bus, cls.__name__, session_id)
                if s not in direct
            ]
            if parent_subs:
                items.append(("extends", cls, parent_subs))

        _print_items(items, prefix + cont, visited, lines)


def print_full_flow(*roots) -> str:
    """Print the full event flow diagram starting from root handlers.

    Args:
        *roots: Root handlers (e.g. RawDataCollector instances) that start the flow.

    Returns:
        The flow diagram as a string.
    """
    lines: list[str] = []
    visited: set = set()

    for root in roots:
        name = _handler_display_name(root)
        header = f"── {name} "
        lines.append(header + "─" * max(0, 60 - len(header)))

        visited.add(id(root))
        _print_publishes(root, "    ", visited, lines)
        lines.append("")

    result = "\n".join(lines)
    import io
    import sys

    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(result)
    return result


# ── Mermaid Flow Diagram ─────────────────────────────────


def _mermaid_node_id(handler) -> str:
    return f"h{id(handler) % 0xFFFFFF:06x}"


def _mermaid_node_label(handler) -> str:
    name = handler.__class__.__name__
    session_id = getattr(handler, "_session_id", None)
    if session_id is not None:
        name = f"{name} {session_id}"
    return name


def _collect_graph(
    handler,
    bus: EventBus | None,
    session_id: int | None,
    nodes: dict,
    edges: list,
    visited: set,
):
    handler_id = id(handler)
    if handler_id in visited:
        return
    visited.add(handler_id)

    nodes[handler_id] = handler

    if bus is None:
        bus = getattr(handler, "_event_bus", None)
    if session_id is None:
        session_id = getattr(handler, "_session_id", None)

    events: list[type[Event]] = getattr(handler, "publishes", [])
    if not bus or not events:
        return

    for event_type in events:
        # Direct subscribers
        direct = _find_subscribers(bus, event_type.__name__, session_id)
        for sub in direct:
            edges.append((handler, event_type.__name__, sub, None))
            sub_bus = getattr(sub, "_event_bus", bus)
            sub_sid = getattr(sub, "_session_id", None)
            _collect_graph(sub, sub_bus, sub_sid, nodes, edges, visited)

        # MRO extends
        for cls in event_type.__mro__[1:]:
            if cls is object or cls is Event or not issubclass(cls, Event):
                continue
            parent_subs = [
                s
                for s in _find_subscribers(bus, cls.__name__, session_id)
                if s not in direct
            ]
            for sub in parent_subs:
                edges.append((handler, event_type.__name__, sub, cls.__name__))
                sub_bus = getattr(sub, "_event_bus", bus)
                sub_sid = getattr(sub, "_session_id", None)
                _collect_graph(sub, sub_bus, sub_sid, nodes, edges, visited)


def generate_mermaid_flow(*roots) -> str:
    """Generate a Mermaid flowchart from root handlers.

    Session-specific handlers are grouped into subgraphs.
    Global handlers (session_id=None) are placed in the common area.

    Args:
        *roots: Root handlers that start the flow.

    Returns:
        Mermaid flowchart string.
    """
    nodes: dict = {}
    edges: list = []
    visited: set = set()

    for root in roots:
        bus = getattr(root, "_event_bus", None)
        sid = getattr(root, "_session_id", None)
        _collect_graph(root, bus, sid, nodes, edges, visited)

    # Classify nodes by session_id
    sessions: dict[int, list] = defaultdict(list)
    globals_list: list = []
    for handler in nodes.values():
        sid = getattr(handler, "_session_id", None)
        if sid is not None:
            sessions[sid].append(handler)
        else:
            globals_list.append(handler)

    # Build event nodes: group edges by (source_id, event_label)
    # Each group becomes an event node ([EventName])
    edge_groups: dict[tuple[str, str], dict] = {}
    edge_order: list[tuple[str, str]] = []
    for src, event_name, dst, extends in edges:
        src_id = _mermaid_node_id(src)
        dst_id = _mermaid_node_id(dst)
        label = f"{event_name} : {extends}" if extends else event_name
        key = (src_id, label)
        if key not in edge_groups:
            src_sid = getattr(src, "_session_id", None)
            edge_groups[key] = {"src": src, "src_sid": src_sid, "dsts": []}
            edge_order.append(key)
        edge_groups[key]["dsts"].append(dst_id)

    # Assign event node IDs and classify by session
    event_nodes: list[tuple[str, str, int | None]] = []  # (ev_id, label, session_id)
    ev_counter = 0
    ev_map: dict[tuple[str, str], str] = {}
    for key in edge_order:
        ev_id = f"ev{ev_counter}"
        ev_counter += 1
        ev_map[key] = ev_id
        group = edge_groups[key]
        event_nodes.append((ev_id, key[1], group["src_sid"]))

    # Classify event nodes by session
    session_event_nodes: dict[int, list[tuple[str, str]]] = defaultdict(list)
    global_event_nodes: list[tuple[str, str]] = []
    for ev_id, label, sid in event_nodes:
        if sid is not None:
            session_event_nodes[sid].append((ev_id, label))
        else:
            global_event_nodes.append((ev_id, label))

    lines = ["graph TD"]

    # Global handlers + global event nodes first
    if globals_list or global_event_nodes:
        for handler in globals_list:
            nid = _mermaid_node_id(handler)
            label = _mermaid_node_label(handler)
            lines.append(f"    {nid}[{label}]")
        for ev_id, label in global_event_nodes:
            lines.append(f"    {ev_id}([{label}])")
        lines.append("")

    # Session subgraphs (handlers + session event nodes)
    for sid in sorted(sessions.keys()):
        lines.append(f'    subgraph "Session {sid}"')
        for handler in sessions[sid]:
            nid = _mermaid_node_id(handler)
            label = _mermaid_node_label(handler)
            lines.append(f"        {nid}[{label}]")
        for ev_id, label in session_event_nodes.get(sid, []):
            lines.append(f"        {ev_id}([{label}])")
        lines.append("    end")

    # Edges: source --> event_node --> targets
    lines.append("")
    for key in edge_order:
        src_id = key[0]
        ev_id = ev_map[key]
        group = edge_groups[key]
        lines.append(f"    {src_id} --> {ev_id}")
        for dst_id in group["dsts"]:
            lines.append(f"    {ev_id} --> {dst_id}")

    return "\n".join(lines)


def save_mermaid_flow(*roots, path: str = "flow.md") -> str:
    """Generate and save a Mermaid flowchart to a markdown file.

    Args:
        *roots: Root handlers that start the flow.
        path: Output file path (default: "flow.md").

    Returns:
        The generated Mermaid string.
    """
    import os
    from pathlib import Path

    mermaid = generate_mermaid_flow(*roots)
    content = f"# Event Flow\n\n```mermaid\n{mermaid}\n```\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
    return mermaid
