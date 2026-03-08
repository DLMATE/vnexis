from dataclasses import dataclass
from typing import Literal


@dataclass
class Source:
    type: Literal["image", "video"]
    path: str
