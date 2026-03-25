import logging
import time
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar

from vnexis.event import (
    AsyncEventHandler,
    DefectDetected,
    DetectionDone,
    DomainEvent,
    EventBus,
    EventHandled,
    FrameBuffered,
    FramePendingDone,
    Preprocessed,
    RawDataCollected,
)
from vnexis.vo import TDetectResult, TMetadata, TRawData

logger = logging.getLogger(__name__)

TDomainEvent = TypeVar("TDomainEvent", bound=DomainEvent)


class DomainEventHandler(AsyncEventHandler[TDomainEvent]):
    def __init__(
        self,
        event_bus: EventBus | None = None,
        session_id: int | None = None,
        max_workers: int = 1,
        type: Literal["thread", "process"] = "thread",
    ):
        self._session_id = session_id
        self._event_bus = event_bus

        super().__init__(max_workers=max_workers, type=type)

    def handle(self, event: TDomainEvent):
        # if self._session_id is not None and event.session_id != self._session_id:
        #     return
        super().handle(event)

    @abstractmethod
    def process(self, event: TDomainEvent) -> None:
        pass

    def _run(self, event: TDomainEvent):
        s = time.perf_counter()
        super()._run(event)
        e = time.perf_counter()
        self._event_bus.publish(
            EventHandled(
                session_id=event.session_id,
                name=self.__class__.__name__,
                duration=e - s,
            )
        )

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @event_bus.setter
    def event_bus(self, event_bus: EventBus):
        self._event_bus = event_bus


class RawDataCollectedHandler(DomainEventHandler[RawDataCollected], Generic[TRawData]):
    pass


class PreprocessedHandler(
    DomainEventHandler[Preprocessed], Generic[TRawData, TMetadata]
):
    pass


class DetectionDoneHandler(
    DomainEventHandler[DetectionDone],
    Generic[TRawData, TMetadata, TDetectResult],
):
    pass


class DefectDetectedHandler(
    DomainEventHandler[DefectDetected],
    Generic[TRawData, TMetadata, TDetectResult],
):
    pass


class FrameCapturedHandler(DomainEventHandler[RawDataCollected]):
    pass


class FrameBufferedHandler(DomainEventHandler[FrameBuffered]):
    pass


class FramePendingDoneHandler(DomainEventHandler[FramePendingDone]):
    pass


@dataclass
class _Stats:
    count: int = 0
    total: float = 0.0
    min: float = field(default=float("inf"))
    max: float = 0.0
    _durations: list[float] = field(default_factory=list)

    def update(self, duration: float):
        self.count += 1
        self.total += duration
        self._durations.append(duration)
        if duration < self.min:
            self.min = duration
        if duration > self.max:
            self.max = duration

    def percentile(self, p: float) -> float:
        if not self._durations:
            return 0.0
        sorted_d = sorted(self._durations)
        idx = (len(sorted_d) - 1) * p / 100
        lo = int(idx)
        hi = min(lo + 1, len(sorted_d) - 1)
        frac = idx - lo
        return sorted_d[lo] * (1 - frac) + sorted_d[hi] * frac

    @property
    def median(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def std(self) -> float:
        if len(self._durations) < 2:
            return 0.0
        avg = self.total / self.count
        variance = sum((d - avg) ** 2 for d in self._durations) / (self.count - 1)
        return variance ** 0.5


class StatisticsManager(AsyncEventHandler[EventHandled]):
    def __init__(self):
        super().__init__(max_workers=1, type="thread")
        self._statistics: dict[str, dict[int | None, _Stats]] = defaultdict(
            lambda: defaultdict(_Stats)
        )

    def process(self, event: EventHandled) -> None:
        self._statistics[event.name][event.session_id].update(event.duration)

    def _run(self, event: TDomainEvent):
        return super()._run(event)

    def save(self, path: str = "statistics.json") -> None:
        import json
        import os
        from pathlib import Path

        os.makedirs(os.path.dirname(path), exist_ok=True)

        result = {}
        for handler_name, sessions in self._statistics.items():
            result[handler_name] = {}
            for session_id, stats in sessions.items():
                key = str(session_id) if session_id is not None else "global"
                avg = stats.total / stats.count if stats.count else 0
                result[handler_name][key] = {
                    "count": stats.count,
                    "total_sec": round(stats.total, 6),
                    "avg_sec": round(avg, 6),
                    "std_sec": round(stats.std, 6),
                    "median_sec": round(stats.median, 6),
                    "p95_sec": round(stats.p95, 6),
                    "p99_sec": round(stats.p99, 6),
                    "min_sec": round(stats.min, 6) if stats.count else 0,
                    "max_sec": round(stats.max, 6),
                }
                logger.info(
                    f"[Statistics] {handler_name}(session={key}) | "
                    f"count: {stats.count} | "
                    f"avg: {avg * 1000:.2f} ms | "
                    f"std: {stats.std * 1000:.2f} ms | "
                    f"median: {stats.median * 1000:.2f} ms | "
                    f"p95: {stats.p95 * 1000:.2f} ms | "
                    f"p99: {stats.p99 * 1000:.2f} ms | "
                    f"min: {stats.min * 1000:.2f} ms | "
                    f"max: {stats.max * 1000:.2f} ms"
                )
        Path(path).write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
