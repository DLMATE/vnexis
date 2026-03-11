import logging
from abc import ABC


class Listener(ABC):
    logger = logging.getLogger(__name__)


class FrameCapturedListener(Listener):
    def on_captured():
        pass


class DefectDetectedListener(Listener):
    def on_capture_frame():
        pass
