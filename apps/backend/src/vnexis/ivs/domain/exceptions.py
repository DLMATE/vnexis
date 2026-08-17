from uuid import UUID

from vnexis.core.exceptions import DomainError


class IvsNotFoundError(DomainError):
    def __init__(self, ivs_id: UUID | None) -> None:
        self.ivs_id = ivs_id
        super().__init__(f"ID가 {ivs_id}인 IVS를 찾을 수 없음")
