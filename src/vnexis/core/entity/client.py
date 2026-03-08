from dataclasses import dataclass
from typing import Literal


@dataclass
class Source:
    media_type: Literal["image", "video"]
    source_type: Literal["rtsp", "file", "nas", "camera", "db"]
    path: str


@dataclass
class Client:
    id: int
    source: Source

    def connect(self):
        pass

    def disconnect(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass
