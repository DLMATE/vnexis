# 애플리케이션 계층의 공통 작업 결과 DTO
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DeletionOutcome:
    """삭제 작업의 결과를 나타내는 DTO.
    - 삭제된 엔터티의 ID를 포함하여 결과 확인 가능
    """

    entity_id: UUID

    def __str__(self) -> str:
        return f"ID가 {self.entity_id}인 엔터티가 성공적으로 삭제됨"
