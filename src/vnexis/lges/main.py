import logging
import time

import cv2

from vnexis.common.event import get_glboal_event_bus
from vnexis.core.event import (
    DefectDetected,
    FrameBuffered,
    FrameCaptured,
    FramePendingDone,
    Preprocessed,
    RawDataCollected,
    TargetCreated,
)
from vnexis.core.service.frame_buffer import FrameBufferHandler, FrameBufferManager
from vnexis.core.service.frame_clipper import FrameClipperHandler, FrameClipperManager

from .collector import AvSourceGateway
from .detector import FaultFrameDetector
from .displayer import Displayer
from .postprocessor import ImageSaver, VideoRequester, VideoSaver
from .preprocessor import KeyFrameDetector
from .target_creator import TriggerTracker

logging.basicConfig(level=logging.INFO)


def main():
    client_id = 0
    max_client = 4
    video_path = "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
    key_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    fault_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"
    event_bus = get_glboal_event_bus()

    frame_buffer_manager = FrameBufferManager()
    frame_buffer_handler = FrameBufferHandler(event_bus, frame_buffer_manager)

    frame_clipper_manager = FrameClipperManager()
    frame_clipper_manager.add_frame_clipper
    frame_clipper_handler = FrameClipperHandler(event_bus, frame_clipper_manager)

    image_saver = ImageSaver(event_bus)
    video_requester = VideoRequester(event_bus, frame_clipper_manager)
    video_saver = VideoSaver(event_bus)

    event_bus.subscribe(FrameCaptured, frame_buffer_handler)
    event_bus.subscribe(FrameBuffered, frame_clipper_handler)
    event_bus.subscribe(DefectDetected, image_saver)
    event_bus.subscribe(DefectDetected, video_requester)
    event_bus.subscribe(FramePendingDone, video_saver)

    collectors = []
    displayers = []
    for client_id in range(max_client):
        frame_buffer_manager.add_buffer(client_id)
        frame_clipper_manager.add_frame_clipper(
            client_id, frame_buffer_manager.get_buffer(client_id)
        )

        collector = AvSourceGateway(client_id, video_path, event_bus)
        key_frame_detector = KeyFrameDetector(
            client_id, key_frame_model_path, event_bus
        )
        trigger_tracker = TriggerTracker(client_id, event_bus)
        fault_frame_detector = FaultFrameDetector(
            client_id, fault_frame_model_path, event_bus, default_threshold=0.2
        )

        event_bus.subscribe(RawDataCollected, key_frame_detector)
        event_bus.subscribe(Preprocessed, trigger_tracker)

        event_bus.subscribe(TargetCreated, fault_frame_detector)

        collectors.append(collector)

    displayer = Displayer(0, event_bus)
    event_bus.subscribe(Preprocessed, displayer)
    displayers.append(displayer)

    for collector in collectors:
        collector.connect()
        video_saver.set_input_stream(collector.stream)
        collector.start()
    # for displayer in displayers:
    displayer.show()

    while displayer.is_running:
        time.sleep(0.1)

    for collector in collectors:
        collector.disconnect()
    cv2.destroyAllWindows()
    exit(0)


if __name__ == "__main__":
    main()
