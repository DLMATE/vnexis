import time
from typing import Sequence

import numpy as np
import onnxruntime as ort

from lges.event import FaultFrameDetected, FaultFrameDetectionDone
from lges.vo import (
    DetectionResultDto,
    FaultFrameDetectResult,
    LgesMetadata,
)
from vnexis.event import EventBus, Preprocessed
from vnexis.handler import PreprocessedHandler
from vnexis.utils import resize_image
from vnexis.vo import Frame


class FaultFrameDetector(PreprocessedHandler[Frame, LgesMetadata]):
    publishes = [FaultFrameDetectionDone, FaultFrameDetected]

    def __init__(
        self,
        model_path: str,
        session_id: int | None = None,
        event_bus: EventBus | None = None,
        thresholds: list[float] = [],
        default_threshold: float = 0.7,
    ):
        super().__init__(event_bus, session_id)

        self._model_path = model_path
        self._thresholds = thresholds
        self._idx = 0

        ort.set_default_logger_severity(3)
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 1
        session_options.inter_op_num_threads = 1
        providers = ["CUDAExecutionProvider"]
        self.session = ort.InferenceSession(
            model_path,
            providers=providers,
            sess_options=session_options,
        )

        print(f"providers: {self.session.get_providers()}")

        metadata = self.session.get_modelmeta().custom_metadata_map
        self.class_names = metadata["names"].split(",")
        self.num_classes = len(self.class_names)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

        if not self._thresholds:
            self._thresholds = [default_threshold] * self.num_classes

        self.img_size = self.session.get_inputs()[0].shape[2:]

    def process(self, event: Preprocessed[Frame, LgesMetadata]) -> None:
        try:
            s_time = time.perf_counter()
            img = self._preprocess(event.raw_data)
            outputs = self.session.run(self.output_names, {self.input_name: img})
            detection_result = self._postprocess(outputs)
            e_time = time.perf_counter()
            is_defect = len(detection_result.boxes) > 0
            self.logger.info(
                f"[FaultFrameDetector] {event.frame.idx} - is_defect: {is_defect}"
            )
            self._event_bus.publish(
                FaultFrameDetectionDone(
                    session_id=event.session_id,
                    raw_data=event.raw_data,
                    frame=event.frame,
                    metadata=event.metadata,
                    detect_result=FaultFrameDetectResult(
                        detection_result=detection_result,
                        time=e_time - s_time,
                    ),
                )
            )
            if is_defect:
                self._event_bus.publish(
                    FaultFrameDetected(
                        session_id=event.session_id,
                        raw_data=event.raw_data,
                        frame=event.frame,
                        metadata=event.metadata,
                        detect_result=FaultFrameDetectResult(
                            detection_result=detection_result,
                            time=e_time - s_time,
                        ),
                    )
                )
        except Exception as e:
            self.logger.exception(f"Error: {e}")

    def _preprocess(self, frame: Frame) -> np.ndarray:
        if frame.data.shape[:2] != self.img_size:
            img = resize_image(frame.data, self.img_size, keep_aspect_ratio=True)
        else:
            img = frame.data.copy()
        img = img.transpose(2, 0, 1)[None].astype(np.float16)
        return img

    def _postprocess(self, outputs: Sequence[np.ndarray]) -> DetectionResultDto:
        outputs_dict = {
            name: output for name, output in zip(self.output_names, outputs)
        }
        boxes = outputs_dict.get("boxes", np.empty((0, 4)))
        labels = outputs_dict.get("labels", np.empty(0))
        scores = outputs_dict.get("scores", np.empty(0))
        masks = outputs_dict.get(
            "masks", np.empty((0, self.img_size[0] // 4, self.img_size[1] // 4))
        )

        if len(scores) > 0:
            filter = scores > np.array(self._thresholds)[labels.astype(int)]
            boxes = boxes[filter]
            labels = labels[filter]
            scores = scores[filter]
            if len(masks) > 0:
                masks = masks[filter]

        return DetectionResultDto(
            boxes=boxes,
            labels=labels,
            scores=scores,
            masks=masks,
            img_size=self.img_size,
        )
