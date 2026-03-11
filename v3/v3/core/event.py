from dataclasses import dataclass
from common.event import Event
from .dto import Frame, Metadata
from typing import Any


@dataclass(kw_only=True, frozen=True)
class RawCollected(Event):
    """수집된 원본 데이터"""

    session_id: int


@dataclass(kw_only=True, frozen=True)
class Preprocessed(Event):
    """전처리된 데이터"""

    session_id: int
    frame: Frame
    metadata: Metadata


@dataclass(kw_only=True, frozen=True)
class TargetCreated(Preprocessed):
    """
    타겟 데이터
    """

    session_id: int
    frame: Frame
    metadata: Metadata


@dataclass(kw_only=True, frozen=True)
class DetectionDone(Event):
    """
    추론 결과
    """

    session_id: int
    is_defect: bool


@dataclass(kw_only=True, frozen=True)
class DefectDetected(Event):
    """
    추론 결과
    """

    session_id: int
    frame: Frame
    result: dict[str, Any]
