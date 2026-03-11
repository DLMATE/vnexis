from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import cv2


logger = logging.getLogger(__name__)


@dataclass
class Source:
    """
    수집할 데이터의 경로
    """

    path: str


@dataclass
class Frame:
    """
    프레임 데이터
    """

    idx: int
    data: np.ndarray | cv2.Mat


@dataclass
class Metadata:
    """
    메타데이터
    """

    pass
