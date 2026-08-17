"""
IVS 바운디드 컨텍스트의 의존성 주입 컨테이너 (컴포지션 루트의 조립 부분).

- 엔진 → 세션 팩토리 → Uow → 유스 케이스 → 컨트롤러 순으로 의존성을 선언적으로 연결한다
- 설정(config)은 프로바이더 참조로만 넘겨 지연 해석되게 한다.
  클래스 정의 시점에 `config.foo()`처럼 즉시 호출하면 나중에 주입한 설정이
  반영되지 않으므로 절대 그렇게 하지 않는다
- 프로바이더는 호출해서 해석한다 (`container.ivs_controller()`).
  @inject / Provide[...] / container.wire()는 쓰지 않는다
"""

from dependency_injector import containers, providers

from vnexis.core.db.session import create_engine, create_session_factory
from vnexis.ivs.application.use_cases.ivs_use_cases import (
    CreateIvsUseCase,
    GetIvsUseCase,
    ListIvsUseCase,
    PendingIvsUseCase,
    StopIvsUseCase,
)
from vnexis.ivs.infrastructure.persistence.uow import SqlAlchemyUow
from vnexis.ivs.interfaces.controllers.ivs_controller import IvsController
from vnexis.ivs.interfaces.presenters.web import WebIvsPresenter


class IvsContainer(containers.DeclarativeContainer):
    """IVS 컨텍스트의 DI 컨테이너.

    사용 방식:
        container = IvsContainer()
        container.config.database_url.from_value(Config.get_database_url())
        controller = container.ivs_controller()

    모든 프로바이더가 Singleton인 이유:
        - 유스 케이스 / 컨트롤러 / 프레젠터는 무상태다
        - SqlAlchemyUow는 세션을 인스턴스별 ContextVar에 담으므로
          하나의 인스턴스를 동시 요청이 공유해도 안전하다
        - 엔진은 커넥션 풀을 가지므로 프로세스당 하나여야 한다
    """

    # strict=True: 설정을 주입하지 않은 채 프로바이더를 해석하면 즉시 오류가 난다.
    #   이게 없으면 database_url이 None으로 해석되고 create_engine이 기본값으로
    #   조용히 폴백해서, 배선 실수가 "엉뚱한 DB를 쓰는데 잘 도는 것처럼 보이는"
    #   상태가 된다.
    config = providers.Configuration(strict=True)

    # ── 인프라 ──
    engine = providers.Singleton(create_engine, database_url=config.database_url)
    session_factory = providers.Singleton(create_session_factory, engine=engine)
    uow = providers.Singleton(SqlAlchemyUow, session_factory=session_factory)

    # ── 인터페이스 ──
    presenter = providers.Singleton(WebIvsPresenter)

    # ── 유스 케이스 ──
    create_use_case = providers.Singleton(CreateIvsUseCase, uow=uow)
    get_use_case = providers.Singleton(GetIvsUseCase, uow=uow)
    list_use_case = providers.Singleton(ListIvsUseCase, uow=uow)
    pending_use_case = providers.Singleton(PendingIvsUseCase, uow=uow)
    stop_use_case = providers.Singleton(StopIvsUseCase, uow=uow)

    # ── 컨트롤러 ──
    ivs_controller = providers.Singleton(
        IvsController,
        create_use_case=create_use_case,
        get_use_case=get_use_case,
        list_use_case=list_use_case,
        pending_use_case=pending_use_case,
        stop_use_case=stop_use_case,
        presenter=presenter,
    )
