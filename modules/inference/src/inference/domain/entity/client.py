from dataclasses import dataclass

from inference.domain.value_object import Source


@dataclass
class Client:
    id: int
    source: Source

    def start_capture(self, source_gateway):
        pass
