from abc import ABC, abstractmethod

from vnexis.ivs.application.repos.ivs_repo import IvsRepository


class Uow(ABC):
    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass

    @property
    @abstractmethod
    def ivs_repo(self) -> IvsRepository:
        pass
