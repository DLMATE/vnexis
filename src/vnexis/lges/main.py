import logging
import time

import cv2

from vnexis.common.event import get_glboal_event_bus
from vnexis.core.event import Preprocessed, RawDataCollected, TargetCreated

from .collector import AvSourceGateway
from .detector import FaultFrameDetector
from .displayer import Displayer
from .preprocessor import KeyFrameDetector
from .target_creator import TriggerTracker

logging.basicConfig(level=logging.WARNING)


def main():
    client_id = 0
    video_path = "C:/rtm/dev/lges-demo/5s, no 14 pallete.mp4"
    model_path = "C:/rtm/dev/lges-demo/trigger_yolonas_s_v1.0.onnx"
    event_bus = get_glboal_event_bus()

    collector = AvSourceGateway(client_id, video_path, event_bus)
    key_frame_detector = KeyFrameDetector(client_id, model_path, event_bus)
    displayer = Displayer(event_bus)
    trigger_tracker = TriggerTracker(event_bus)
    fault_frame_detector = FaultFrameDetector(event_bus)

    event_bus.subscribe(RawDataCollected, key_frame_detector)
    event_bus.subscribe(Preprocessed, trigger_tracker)
    event_bus.subscribe(Preprocessed, displayer)
    event_bus.subscribe(TargetCreated, fault_frame_detector)

    collector.connect()
    collector.start()
    displayer.show()

    while displayer.is_running:
        time.sleep(0.1)

    collector.disconnect()
    cv2.destroyAllWindows()
    exit(0)


if __name__ == "__main__":
    main()
