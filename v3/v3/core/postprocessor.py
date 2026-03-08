from common.event import Event, EventHandler, EventBus, event_bus
import cv2
import threading
from collections import defaultdict
import time
import logging
from core.event import DefectDetected, DetectionDone
from typing import TypeVar, Generic
from abc import abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=[DefectDetected, DetectionDone])


class Postprocessor(EventHandler, Generic[T]):
    @abstractmethod
    def handle(self, event: T):
        pass
