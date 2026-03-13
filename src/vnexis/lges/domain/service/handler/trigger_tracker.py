from collections import deque
from enum import Enum

import numpy as np

from vnexis.core.domain.service.handler import DomainEventHandler
from vnexis.lges.domain.event import KeyFrameDetected, KeyFrameDetectionDone


class TriggerTracker(DomainEventHandler[KeyFrameDetectionDone]):
    """
    트리거 상태를 탐지하는 트래커
    """

    class State(Enum):
        UNKNOWN = 0
        UPSTABLE = 1
        DOWNSTABLE = 2
        UP = 3
        DOWN = 4

    def __init__(
        self,
        session_id: int,
        num_watch: int = 10,
        margin: int = 1,
        num_capture: int = 10,
    ):
        """
        트리거 트래커 초기화
        Args:
            num_watch (int): 트래커 모니터링 횟수
            margin (int): 트래커 상태 변화 허용 범위
            num_capture (int): 트리거 후 캡쳐 프레임 개수
        """
        super().__init__(session_id)
        self.num_watch = num_watch
        self.margin = margin
        self.num_capture = num_capture

        self.clear()

    def process(self, event: KeyFrameDetectionDone) -> None:
        for box, label in zip(event.boxes, event.labels):
            if int(label) == 1:
                x1, y1, x2, y2 = map(int, box)
                value = y1
                break
        if value is None:
            return None
        is_target = self.update(value)
        if not is_target:
            return None

        self.logger.warning(
            f"[TriggerTracker] Trigger! Created Target. frame_idx: {event.raw_data.frame.idx}"
        )
        self._event_bus.publish(
            KeyFrameDetected(
                session_id=self.session_id,
                raw_data=event.raw_data,
                frame=event.raw_data.frame,
                metadata=event.raw_data.metadata,
            )
        )

    def increase_capture_count(self) -> tuple[bool, bool]:
        self.capture_count += 1
        if self.capture_count > self.num_capture:
            self.capture_flag = False
            self.capture_count = 0
            self.capture_end_flag = True
        else:
            self.capture_end_flag = False
        return self.capture_flag, self.capture_end_flag

    def update(self, value: int) -> bool:
        if self.prev_tracking_value == -1:
            self.prev_tracking_value = value
            return False

        diff = value - self.prev_tracking_value
        self.prev_tracking_value = value
        self.tracking_diffs.append(diff)

        if len(self.tracking_diffs) < self.num_watch:
            return False

        self._update_state()
        self._update_flag()
        return self.capture_flag

    def get_mean_diff(self) -> float:
        return np.mean(self.tracking_diffs) if len(self.tracking_diffs) > 0 else 0

    def clear(self) -> None:
        self.state = self.State.UNKNOWN
        self.prev_state = self.State.UNKNOWN
        self.prev_tracking_value = -1
        self.tracking_diffs: deque[float] = deque(maxlen=self.num_watch)

        self.capture_count = 0
        self.capture_flag = False
        self.capture_end_flag = False

    def _update_state(self) -> None:
        self.prev_state = self.state
        mean_diff = np.mean(self.tracking_diffs)
        if abs(mean_diff) < self.margin:
            match self.state:
                case self.State.UP:
                    self.state = self.State.UPSTABLE
                case self.State.DOWN:
                    self.state = self.State.DOWNSTABLE
        else:
            self.state = self.State.UP if mean_diff < 0 else self.State.DOWN

    def _update_flag(self) -> None:
        if self.state == self.State.DOWNSTABLE and self.prev_state == self.State.DOWN:
            self.capture_flag = True
            self.capture_count = 1
        else:
            self.capture_flag = False
