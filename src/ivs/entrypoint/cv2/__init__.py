import threading
import time
from collections import deque

import numpy as np
import onnxruntime as ort

import cv2
from ivs.application.commands import (
    StartStreamDetectionCommand,
    StartStreamDetectionCommandExecutor,
)
from ivs.common.event import EventHandler, event_bus
from ivs.common.utils import resize_boxes, resize_image
from ivs.domain.entities import Frame
from ivs.domain.entities.detection import SegmentDetectionData
from ivs.domain.events import DetectionDoneEvent, FrameCapturedEvent
from ivs.domain.services import Detector
from ivs.infra.frame_reader import MemFrameReaderResistry


class KeyFrameDetector:
    def __init__(self, model_path: str):
        ort.set_default_logger_severity(3)
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 1
        session_options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(
            model_path,
            providers=["CUDAExecutionProvider"],
            sess_options=session_options,
        )

        metadata = self._session.get_modelmeta().custom_metadata_map
        self._class_names = metadata["names"].split(",")
        self._num_classes = len(self._class_names)
        self._input_name = self._session.get_inputs()[0].name
        self._output_names = [o.name for o in self._session.get_outputs()]

        self._img_size = self._session.get_inputs()[0].shape[2:]

    def __call__(self, img: np.ndarray) -> dict:
        src_size = img.shape[:2]

        if src_size != self._img_size:
            input_img = resize_image(img, self._img_size, keep_aspect_ratio=True)
        else:
            input_img = img.copy()
        input_img = input_img.transpose((2, 0, 1))[None].astype(
            np.float16
        )  # HWC to CHW

        outputs = self._session.run(self._output_names, {self._input_name: input_img})
        outputs_dict = {
            name: output for name, output in zip(self._output_names, outputs)
        }
        result = {
            "boxes": outputs_dict.get("boxes", np.empty((0, 4))),
            "labels": outputs_dict.get("labels", np.empty(0)),
            "scores": outputs_dict.get("scores", np.empty(0)),
            "masks": outputs_dict.get(
                "masks", np.empty((0, self._img_size[0] // 4, self._img_size[1] // 4))
            ),
            "src_size": src_size,
            "dst_size": self._img_size,
        }
        return result


class Displayer(EventHandler):
    def __init__(self, client_id: int, width: int = 800, height: int = 600):
        self._client_id = client_id
        self._queue: deque[DetectionDoneEvent] = deque(maxlen=30 * 2)
        self._is_running = False
        self._thread = threading.Thread(target=self._process, daemon=True)
        self._lock = threading.Lock()
        self._width = width
        self._height = height
        self._color = (0, 255, 0)  # 초록색
        self._thickness = 2

    def handle(self, event: DetectionDoneEvent):
        if event.client_id != self._client_id:
            return
        with self._lock:
            self._queue.append(event)

    def _process(self):
        while self._is_running:
            with self._lock:
                if len(self._queue) > 0:
                    event = self._queue.popleft()
                else:
                    event = None
            if not event:
                # print("frame is none")
                continue
            # display_data = cv2.resize(
            #     event.frame.data,
            #     (self._width, self._height),
            #     interpolation=cv2.INTER_NEAREST,
            # )
            display_data = resize_image(
                event.frame.data, (self._height, self._width), keep_aspect_ratio=False
            )
            resized_boxes = resize_boxes(
                event.detection_result.data["boxes"],
                event.detection_result.data["dst_size"],
                event.detection_result.data["src_size"],
                True,
                True,
            )
            resized_boxes = resize_boxes(
                resized_boxes,
                event.detection_result.data["src_size"],
                (self._height, self._width),
                False,
                False,
            )
            print(f"resized_boxes: {resized_boxes}")

            for i in range(2):
                x1, y1, x2, y2 = map(int, resized_boxes[i])
                cv2.rectangle(
                    display_data, (x1, y1), (x2, y2), self._color, self._thickness
                )
            cv2.putText(
                display_data,
                f"Frame: {event.frame.idx}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow("display", display_data)
            key = cv2.waitKey(33)
            if key == 27:
                self._is_running = False
                break

            # if frame.idx % 100 == 0:
            #     e_100_time = time.perf_counter()
            #     print(f"100 frames time: {e_100_time - s_100_time}")
            #     s_100_time = e_100_time

    def show(self):
        self._is_running = True
        self._thread.start()

    def stop(self):
        self._is_running = False
        self._thread.join()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def __del__(self):
        cv2.destroyAllWindows()


def main():
    key_frame_detector = KeyFrameDetector(
        model_path="C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    )

    def detect_fn(img: np.ndarray) -> dict:
        return key_frame_detector(img)

    detector = Detector(detect_fn=detect_fn)
    event_bus.subscribe(FrameCapturedEvent, detector)

    displayer = Displayer(client_id=0, width=800, height=600)
    event_bus.subscribe(DetectionDoneEvent, displayer)

    frame_reader_registry = MemFrameReaderResistry()
    command_executor = StartStreamDetectionCommandExecutor(frame_reader_registry)

    command = StartStreamDetectionCommand(
        client_id=0,
        stream_url="C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4",
    )
    command_executor.execute(command)

    displayer.show()
    while displayer.is_running:
        time.sleep(0.1)

    frame_reader_registry.unregister(client_id=0)
    del displayer
