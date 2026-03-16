import logging
import os
from pathlib import Path

import cv2

from lges.event import FaultFrameDetected
from vnexis.event import AsyncEventHandler

logger = logging.getLogger(__name__)


class FaultFrameSaver(AsyncEventHandler[FaultFrameDetected]):
    def process(self, event: FaultFrameDetected):
        path = Path("output") / str(event.session_id) / f"{event.frame.idx}.png"
        os.makedirs(path.parent, exist_ok=True)
        cv2.imwrite(path, event.frame.data)
