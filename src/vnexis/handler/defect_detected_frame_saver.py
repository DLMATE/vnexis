import logging
import os
from pathlib import Path
from typing import Literal

import cv2

from vnexis.event import DefectDetected, EventBus
from vnexis.handler.handler import DefectDetectedHandler

logger = logging.getLogger(__name__)


class DefectDetectedFrameSaver(DefectDetectedHandler):
    def __init__(
        self,
        save_dir: Path,
        event_bus: EventBus | None = None,
        session_id: int | None = None,
        max_workers: int = 1,
        type: Literal["thread", "process"] = "thread",
    ):
        super().__init__(event_bus, session_id, max_workers, type)
        self.save_dir = save_dir

    def process(self, event: DefectDetected):
        path = self.save_dir / str(event.session_id) / f"{event.frame.idx}.png"
        os.makedirs(path.parent, exist_ok=True)
        cv2.imwrite(path, event.frame.data)
