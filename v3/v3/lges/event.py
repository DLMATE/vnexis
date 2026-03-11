from common.event import Event
from core.event import RawCollected, Preprocessed, TargetCreated
from core.dto import Frame
from dataclasses import dataclass


@dataclass(kw_only=True, frozen=True)
class FrameCaptured(RawCollected):
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetectionDone(Preprocessed): ...


@dataclass(kw_only=True, frozen=True)
class KeyFrameDetected(TargetCreated): ...


@dataclass(kw_only=True, frozen=True)
class FrameBuffered(Event):
    frame: Frame


@dataclass(kw_only=True, frozen=True)
class PendingDone(Event):
    key_idx: int
    frames: list[Frame]


@dataclass(kw_only=True, frozen=True)
class DefectImageSaved(Event):
    session_id: int


@dataclass(kw_only=True, frozen=True)
class VideoSaved(Event):
    session_id: int
