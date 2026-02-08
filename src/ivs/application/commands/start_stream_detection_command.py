from dataclasses import dataclass

from ivs.application.interfaces.frame_reader import FrameReaderResistry


@dataclass
class StartStreamDetectionCommand:
    client_id: int
    stream_url: str


class StartStreamDetectionCommandExecutor:
    def __init__(self, frame_reader_registry: FrameReaderResistry):
        self._frame_reader_registry = frame_reader_registry

    def execute(self, command: StartStreamDetectionCommand):
        frame_reader = self._frame_reader_registry.register(
            command.client_id, command.stream_url
        )
        frame_reader.start()
