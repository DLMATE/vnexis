# from .video_capture import VideoCapture
# from .key_frame_detector import KeyFrameDetector
# from .defect_detector import DefectDetector
# from .displayer import Displayer
# from common.event import EventBus
# from core.event import RawCollected, Preprocessed, TargetCreated
# from .event import FrameCaptured, KeyFrameDetectionDone, KeyFrameDetected
# import time
# import cv2


# def main():
#     event_bus = EventBus()

#     video_capture = VideoCapture(event_bus)
#     key_frame_detector = KeyFrameDetector(event_bus)
#     defect_detector = DefectDetector(event_bus)
#     displayer = Displayer(event_bus)

#     event_bus.subscribe(FrameCaptured, key_frame_detector)
#     event_bus.subscribe(KeyFrameDetectionDone, displayer)
#     event_bus.subscribe(KeyFrameDetected, defect_detector)

#     video_capture.connect()
#     video_capture.start()
#     displayer.show()

#     while displayer.is_running:
#         time.sleep(0.1)

#     video_capture.stop()
#     video_capture.disconnect()
#     cv2.destroyAllWindows()
