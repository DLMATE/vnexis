from dataclasses import dataclass

import av
import numpy as np


@dataclass
class RawData: ...


@dataclass
class Frame:
    idx: int
    raw: str | bytes | np.ndarray | av.Packet
    data: bytes | np.ndarray

    # @property
    # def data(self):
    #     if self._data is not None:
    #         if isinstance(self.raw, str):
    #             self._data = cv2.imread(self._data)
    #         if isinstance(self.raw, (bytes, np.ndarray)):
    #             self._data = self.raw
    #         if isinstance(self.raw, av.Packet):
    #             data = self.raw.decode()
    #             if len(data) != 1:
    #                 raise Exception(f"frame data size is not 1. size: {len(data)}")
    #             self._data = data[0].to_ndarray(format="bgr24")
    #     return self._data

    @property
    def width(self):
        return self.data.shape[1]

    @property
    def height(self):
        return self.data.shape[0]


@dataclass
class Metadata: ...


@dataclass
class Target:
    frame: Frame
    metadata: Metadata


@dataclass
class PreprocessResult: ...


@dataclass
class DetectResult: ...


@dataclass
class PostprocessResult: ...
