"""
SQLAlchemy 기반 IvsRepository 구현 (인프라스트럭처 계층).
- 리포지토리 인터페이스(추상 클래스)를 구현하여 의존성 역전 원칙(DIP) 적용
- 커밋은 하지 않는다. 트랜잭션 경계는 Uow가 소유한다
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vnexis.ivs.application.repos.ivs_repo import IvsRepository
from vnexis.ivs.domain.entities.ivs import Ivs
from vnexis.ivs.domain.exceptions import IvsNotFoundError
from vnexis.ivs.infrastructure.persistence.mappers import (
    apply_to_model,
    to_entity,
    to_model,
)
from vnexis.ivs.infrastructure.persistence.models import IvsModel

logger = logging.getLogger(__name__)


class SqlAlchemyIvsRepository(IvsRepository):
    """IvsRepository의 SQLAlchemy 구현.

    세션을 주입받아 사용하며 직접 커밋하지 않는다.
    한 세션은 하나의 Uow 진입(트랜잭션)에 대응한다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, ivs: Ivs) -> Ivs:
        """IVS를 새로 저장한다.

        flush로 INSERT를 미리 내보내 제약 위반을 커밋 전에 드러낸다.

        Args:
            ivs: 저장할 IVS 엔터티

        Returns:
            입력으로 받은 엔터티 (호출자가 트랜잭션 종료 후에도 읽을 수 있도록
            ORM에 붙지 않은 순수 도메인 객체를 그대로 돌려준다)
        """
        logger.debug("Inserting IVS row", extra={"context": {"ivs_id": str(ivs.id)}})
        self._session.add(to_model(ivs))
        await self._session.flush()
        return ivs

    async def get(self, ivs_id: UUID) -> Ivs:
        """ID로 IVS를 조회한다.

        Args:
            ivs_id: IVS의 고유 식별자

        Returns:
            요청된 IVS 엔터티

        Raises:
            IvsNotFoundError: 해당 ID의 IVS가 존재하지 않는 경우
        """
        model = await self._session.get(IvsModel, ivs_id)
        if model is None:
            raise IvsNotFoundError(ivs_id)
        return to_entity(model)

    async def list(self) -> list[Ivs]:
        """모든 IVS를 조회한다.

        Returns:
            이름 순으로 정렬된 IVS 엔터티 목록
        """
        result = await self._session.execute(select(IvsModel).order_by(IvsModel.name))
        return [to_entity(model) for model in result.scalars().all()]

    async def save(self, ivs: Ivs) -> None:
        """기존 IVS의 변경 사항을 반영한다.

        같은 세션 안에서 get()으로 가져온 엔터티라면 아래 조회는
        identity map에서 동일 인스턴스를 즉시 돌려주므로 추가 질의가 없다.

        Args:
            ivs: 변경된 IVS 엔터티

        Raises:
            IvsNotFoundError: 해당 ID의 행이 존재하지 않는 경우
        """
        model = await self._session.get(IvsModel, ivs.id)
        if model is None:
            raise IvsNotFoundError(ivs.id)
        apply_to_model(ivs, model)
