import threading
import time

import cv2

from ivs.application.interfaces.frame_reader import FrameReader
from ivs.common.event import EventBus
from ivs.domain.entities import Frame
from ivs.domain.events import FrameCapturedEvent


class Cv2StreamFrameReader(FrameReader):
    def __init__(self, path: str, client_id: int, event_bus: EventBus):
        super().__init__(path, client_id, event_bus)
        self._cap = cv2.VideoCapture(self._path)
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_delay = 1.0 / self._fps
        self._thread = threading.Thread(target=self.process, daemon=True)

    def process(self):
        print("Video 연결 중...")
        while not self._cap.isOpened():
            time.sleep(self._frame_delay)
        print("Video 연결 성공!")

        idx = 0
        while self._is_running:
            ret, frame = self._cap.read()
            if not ret:
                break
            frame = Frame(idx=idx, data=frame)
            # print(f"frame idx: {frame.idx}")
            # 리스너들을 비동기로 호출 (각 리스너가 내부적으로 비동기 처리)
            self._event_bus.publish(
                FrameCapturedEvent(client_id=self._client_id, frame=frame)
            )
            idx += 1
            time.sleep(self._frame_delay)

    def start(self):
        self._is_running = True
        self._thread.start()

    def stop(self):
        self._is_running = False
        self._thread.join()

    def __del__(self):
        self._cap.release()
