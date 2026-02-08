from ivs.application.interfaces.frame_reader import FrameReader, FrameReaderResistry
from ivs.common.event import event_bus

from .cv2_frame_reader import Cv2StreamFrameReader


class MemFrameReaderResistry(FrameReaderResistry):
    def __init__(self):
        self._frame_readers: dict[int, FrameReader] = dict()

    def get(self, client_id: int) -> FrameReader | None:
        if not self.is_registered(client_id):
            raise Exception("등록된 리더기가 없습니다.")
        return self._frame_readers[client_id]

    def is_registered(self, client_id: int) -> bool:
        return client_id in self._frame_readers.keys()

    def register(self, client_id: int, path: str):
        if self.is_registered(client_id):
            raise Exception("이미 등록되어 있습니다.")
        self._frame_readers[client_id] = Cv2StreamFrameReader(
            path, client_id, event_bus
        )
        return self._frame_readers[client_id]

    def unregister(self, client_id: int):
        if not self.is_registered(client_id):
            return
        frame_reader = self._frame_readers.pop(client_id)
        del frame_reader
