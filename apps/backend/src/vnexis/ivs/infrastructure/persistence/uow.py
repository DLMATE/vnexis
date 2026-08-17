"""
SQLAlchemy 기반 Unit of Work 구현 (인프라스트럭처 계층).

설계 배경 (이 세 가지가 구현을 결정한다):

1. Uow 인스턴스는 장수명이다.
   유스 케이스는 __init__에서 uow를 한 번 주입받고, 매 execute()마다
   `async with self.uow:`로 다시 진입한다.
   → 진입할 때마다 새 세션을 만들어야 한다. 세션을 재사용하면 이전 작업의
     식별 맵과 트랜잭션 상태가 다음 작업으로 새어 나간다.

2. AsyncSession은 태스크 간 공유가 불가능하다.
   SQLAlchemy 문서: "하나의 AsyncSession 인스턴스를 여러 asyncio 태스크가
   동시에 사용하는 것은 안전하지 않다 (태스크당 AsyncSession)."
   → 세션을 평범한 인스턴스 속성에 두면, 같은 Uow를 공유하는 동시 요청 두 개가
     서로의 세션을 덮어쓴다.
   → 세션을 ContextVar에 담는다. asyncio 태스크는 생성 시점에 컨텍스트를
     복사하므로 요청(=태스크)마다 자기 세션만 보게 된다. 순차 진입/이탈도
     그대로 안전하다.

3. 읽기 전용 유스 케이스(Get/List)는 commit()을 호출하지 않는다.
   → __aexit__는 커밋이 없어도 오류 없이 끝나야 한다. Session.rollback()은
     진행 중인 트랜잭션이 없으면 통과(pass-through)이므로 항상 롤백 후
     닫는 것이 안전하다.
"""

import logging
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vnexis.ivs.application.repos.ivs_repo import IvsRepository
from vnexis.ivs.application.repos.uow import Uow
from vnexis.ivs.infrastructure.persistence.ivs_repo import SqlAlchemyIvsRepository

logger = logging.getLogger(__name__)


class SqlAlchemyUow(Uow):
    """Uow의 SQLAlchemy 구현.

    사용 방식:
        async with uow:
            await uow.ivs_repo.create(ivs)
            await uow.commit()

    동시성:
        세션을 ContextVar에 담으므로 이 인스턴스 하나를 여러 요청이 동시에
        사용해도 안전하다. 각 asyncio 태스크가 자기 세션을 갖는다.
        같은 태스크 안에서의 중첩 진입만 RuntimeError로 막는데, 그 경우
        안쪽 블록의 __aexit__가 바깥 블록이 아직 쓰고 있는 세션을 닫아버리기
        때문이다.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        # 인스턴스마다 별도의 ContextVar를 만든다. 모듈 전역으로 두면
        #   Uow 인스턴스가 둘 이상일 때 서로의 세션을 덮어쓴다.
        self._current_session: ContextVar[AsyncSession | None] = ContextVar(
            f"vnexis_ivs_uow_session_{id(self)}", default=None
        )

    async def __aenter__(self) -> "SqlAlchemyUow":
        if self._current_session.get() is not None:
            raise RuntimeError(
                "Uow를 중첩해서 시작할 수 없습니다. "
                "`async with uow:` 블록 안에서 다시 진입하지 마세요."
            )
        # 세션 생성 자체에는 I/O가 없다. 실제 커넥션은 첫 질의에서 지연 획득된다.
        session = self._session_factory()
        self._current_session.set(session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        session = self._current_session.get()
        if session is None:
            return False

        try:
            if exc_type is not None:
                logger.warning(
                    "Rolling back transaction due to exception",
                    extra={"context": {"error_type": exc_type.__name__}},
                )
            # 커밋되지 않은 변경을 모두 폐기한다.
            #   - commit() 직후라면 진행 중인 트랜잭션이 없어 통과한다
            #   - 읽기 전용 유스 케이스에서도 오류 없이 동작한다
            await session.rollback()
        finally:
            await session.close()
            self._current_session.set(None)

        # 예외를 삼키지 않는다. 유스 케이스가 IvsNotFoundError 등을
        #   async with 바깥에서 잡기 때문에 반드시 전파되어야 한다.
        return False

    async def commit(self) -> None:
        """현재 트랜잭션을 커밋한다."""
        await self._require_session().commit()

    async def rollback(self) -> None:
        """현재 트랜잭션을 롤백한다."""
        await self._require_session().rollback()

    @property
    def ivs_repo(self) -> IvsRepository:
        """현재 세션에 묶인 IVS 리포지토리를 반환한다.

        리포지토리는 세션을 감싼 얇은 객체라 접근할 때마다 새로 만든다.
        캐시하면 블록마다 세션이 바뀔 때 이전 블록의 닫힌 세션을 붙들 위험이 있다.
        """
        return SqlAlchemyIvsRepository(self._require_session())

    def _require_session(self) -> AsyncSession:
        """진입 상태를 확인하고 현재 세션을 반환한다.

        Raises:
            RuntimeError: `async with` 블록 바깥에서 사용한 경우
        """
        session = self._current_session.get()
        if session is None:
            raise RuntimeError(
                "Uow에 진입하지 않았습니다. `async with uow:` 블록 안에서 사용하세요."
            )
        return session
