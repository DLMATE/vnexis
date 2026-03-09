import cv2

from vnexis.core.service.detector import Detector


class FaultFrameDetector(Detector):
    def detect(self, target):
        cv2.imwrite(f"{target.frame.idx}.png", target.frame.data)
        return None
