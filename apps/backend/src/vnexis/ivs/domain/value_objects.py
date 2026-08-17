from dataclasses import dataclass
from enum import Enum


class IvsStatus(str, Enum):
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"


@dataclass
class AiModel:
    path: str
    confidence: float
    threshold: float
