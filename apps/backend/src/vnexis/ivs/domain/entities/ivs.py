import logging
from dataclasses import dataclass

from vnexis.core.entity import Entity
from vnexis.ivs.domain.value_objects import AiModel, IvsStatus

logger = logging.getLogger(__name__)


# eq=False: Entity의 ID 기반 __eq__/__hash__를 상속받기 위함
#   (dataclass 기본값 eq=True는 __eq__를 재생성하고 __hash__를 None으로 만든다)
@dataclass(eq=False)
class Ivs(Entity):
    name: str
    status: IvsStatus
    stream_url: str
    track_model: AiModel
    defect_model: AiModel

    @classmethod
    def create(
        cls, name: str, stream_url: str, track_model: AiModel, defect_model: AiModel
    ) -> "Ivs":
        return cls(
            name=name,
            status=IvsStatus.IDLE,
            stream_url=stream_url,
            track_model=track_model,
            defect_model=defect_model,
        )

    def mark_pending(self):
        logger.info(
            "Marking IVS as pending",
            extra={
                "context": {
                    "ivs_id": str(self.id),
                    "ivs_name": self.name,
                    "ivs_stream_url": self.stream_url,
                }
            },
        )
        self.status = IvsStatus.PENDING

    def mark_stopping(self):
        logger.info(
            "Marking IVS as stopping",
            extra={
                "context": {
                    "ivs_id": str(self.id),
                    "ivs_name": self.name,
                    "ivs_stream_url": self.stream_url,
                }
            },
        )
        self.status = IvsStatus.STOPPING
