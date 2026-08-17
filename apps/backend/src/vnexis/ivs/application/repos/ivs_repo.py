from abc import ABC, abstractmethod
from uuid import UUID

from vnexis.ivs.domain.entities.ivs import Ivs


class IvsRepository(ABC):
    @abstractmethod
    async def create(self, ivs: Ivs) -> Ivs:
        pass

    @abstractmethod
    async def get(self, ivs_id: UUID) -> Ivs:
        pass

    @abstractmethod
    async def list(self) -> list[Ivs]:
        pass

    @abstractmethod
    async def save(self, ivs: Ivs) -> None:
        pass
