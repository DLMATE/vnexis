"""
비동기 데이터베이스 엔진과 세션 팩토리 생성 헬퍼.
- 모듈 공용(ivs, 향후 ai 등)
- 합성 루트(composition root)에서 한 번 호출해 만든 팩토리를
  Uow 구현체에 주입하는 것을 전제로 한다
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vnexis.core.config import Config


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """비동기 엔진을 생성한다.

    Args:
        database_url: 접속 URL. 생략하면 Config에서 가져온다.

    Returns:
        생성된 AsyncEngine. 애플리케이션 종료 시 dispose()를 호출해야 한다.
    """
    return create_async_engine(database_url or Config.get_database_url())


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """비동기 세션 팩토리를 생성한다.

    expire_on_commit=False인 이유:
        asyncio에서는 커밋 이후 속성에 접근할 때 일어나는 지연 재로딩이
        지원되지 않는다. 만료를 꺼서 커밋 뒤에도 객체를 안전하게 읽는다.

    Args:
        engine: 세션이 사용할 엔진

    Returns:
        AsyncSession 팩토리
    """
    return async_sessionmaker(engine, expire_on_commit=False)
