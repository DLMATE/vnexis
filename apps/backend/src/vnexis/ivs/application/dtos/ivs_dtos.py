from dataclasses import dataclass
from typing import Self

from vnexis.ivs.domain.entities.ivs import Ivs
from vnexis.ivs.domain.value_objects import AiModel, IvsStatus


@dataclass
class CreateIvsRequest:
    name: str
    stream_url: str
    track_model: AiModel
    defect_model: AiModel


@dataclass
class IvsResponse:
    id: str
    name: str
    status: IvsStatus
    stream_url: str
    track_model: AiModel
    defect_model: AiModel

    @classmethod
    def from_entity(cls, entity: Ivs) -> Self:
        return cls(
            id=str(entity.id),  # 경계 횡단을 위한 기본 변환
            name=entity.name,
            status=entity.status,  # 표시 문자열 변환은 프레젠터 책임
            stream_url=entity.stream_url,
            track_model=entity.track_model,
            defect_model=entity.defect_model,
        )


@dataclass
class UpdateIvsRequest:
    name: str
    stream_url: str
    track_model: AiModel
    defect_model: AiModel
