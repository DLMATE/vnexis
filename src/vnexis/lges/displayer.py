import logging
import threading
import time
from collections import deque

import cv2

from vnexis.common.event import EventHandler
from vnexis.common.utils import draw_text_using_idx, resize_boxes
from vnexis.core.event import Preprocessed
from vnexis.lges.entity import LgesPreprocessResult

logger = logging.getLogger(__name__)


class Displayer(EventHandler):
    def __init__(self, event_bus=None, width: int = 800, height: int = 600):
        super().__init__(event_bus)
        self._queue: deque[LgesPreprocessResult] = deque(maxlen=30 * 2)
        self._lock = threading.Lock()
        self._width = width
        self._height = height
        self._color = (0, 255, 0)  # 초록색
        self._thickness = 2

    def handle(self, event: Preprocessed):
        with self._lock:
            self._queue.append(event.result)

    def show(self):
        self._is_running = True
        start = time.perf_counter()
        while self._is_running:
            try:
                with self._lock:
                    qsize = len(self._queue)
                    if qsize > 0:
                        preprocess_result = self._queue.popleft()
                        end = time.perf_counter()
                    else:
                        preprocess_result = None
                        end = None
                if not preprocess_result:
                    # print("frame is none")
                    continue
                data = cv2.resize(
                    preprocess_result.frame.data, (self._width, self._height)
                )
                boxes = resize_boxes(
                    preprocess_result.key_frame_detection_result.boxes,
                    preprocess_result.key_frame_detection_result.img_size,
                    (preprocess_result.frame.height, preprocess_result.frame.width),
                    keep_aspect_ratio=True,
                    inverse=True,
                )
                boxes = resize_boxes(
                    boxes,
                    (preprocess_result.frame.height, preprocess_result.frame.width),
                    (self._height, self._width),
                    keep_aspect_ratio=False,
                    inverse=False,
                )
                labels = preprocess_result.key_frame_detection_result.labels
                scores = preprocess_result.key_frame_detection_result.scores
                for box, label, score in zip(boxes, labels, scores):
                    x1, y1, x2, y2 = map(int, box)
                    cv2.rectangle(data, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        data,
                        f"{label}: {score:.2f}",
                        (x1, y1),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )
                data = draw_text_using_idx(
                    data, f"idx: {preprocess_result.frame.idx}", 0, (0, 255, 0)
                )
                data = draw_text_using_idx(
                    data,
                    f"cell_id: {preprocess_result.metadata.cell_id}",
                    1,
                    (0, 255, 0),
                )
                data = draw_text_using_idx(
                    data, f"fps: {int(1 / (end - start))}", 2, (0, 255, 0)
                )
                data = draw_text_using_idx(data, f"qsize: {qsize}", 3, (0, 255, 0))
                cv2.imshow("display", data)
                key = cv2.waitKey(30)
                if key == 27:
                    self._is_running = False
                    break
                start = end
            except Exception as e:
                logger.error(f"[Displayer] Error: {e}")

    @property
    def is_running(self) -> bool:
        return self._is_running
