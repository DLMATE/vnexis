from dataclasses import dataclass
from typing import Generic, TypeVar

import av
import numpy as np


@dataclass(frozen=True)
class RawData: ...


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Metadata: ...


# @dataclass(frozen=True)
# class Target:
#     frame: Frame
#     metadata: Metadata

TRawData = TypeVar("TRawData", bound=RawData)
TMetadata = TypeVar("TMetadata", bound=Metadata)


# @dataclass(frozen=True)
# class PreprocessResult(Generic[TMetadata]):
#     frame: Frame
#     metadata: TMetadata


@dataclass(frozen=True)
class DetectResult: ...


TDetectResult = TypeVar("TDetectResult", bound=DetectResult)


@dataclass(frozen=True)
class Target(Generic[TRawData, TMetadata, TDetectResult]):
    client_id: int
    session_id: int
    source_type: str
    path: str
    raw_data: TRawData
    # preprocess_result: PreprocessResult[TMetadata] | None = None
    # target: TTarget | None = None
    detect_result: TDetectResult | None = None

    # def replace_raw_data(self, raw_data: TRawData) -> "Target":
    #     return Target(
    #         client_id=self.client_id,
    #         session_id=self.session_id,
    #         source_type=self.source_type,
    #         path=self.path,
    #         raw_data=raw_data,
    #         preprocess_result=self.preprocess_result,
    #         detect_result=self.detect_result,
    #         postprocess_result=self.postprocess_result,
    #     )
