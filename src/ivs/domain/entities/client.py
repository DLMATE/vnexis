from dataclasses import dataclass


@dataclass
class Client:
    id: int
    stream_url: str
