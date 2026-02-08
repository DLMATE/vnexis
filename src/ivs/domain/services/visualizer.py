from abc import ABC, abstractmethod

import cv2

from ivs.domain.entities.detection import DetectionResult, Frame, T


class Visualizer(T, ABC):
    @abstractmethod
    def visualize(self, frame: Frame, detection_result: DetectionResult[T]) -> cv2.Mat:
        pass
