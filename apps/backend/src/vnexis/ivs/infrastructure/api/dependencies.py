"""
FastAPI 의존성 프로바이더.

- 컨테이너는 앱 수명주기(lifespan)에서 만들어져 app.state에 놓인다.
  라우터는 Depends로 그것을 꺼내 프로바이더를 호출해 해석한다
- 이 파일이 프레임워크(FastAPI)와 컨테이너를 잇는 유일한 이음새다
"""

from fastapi import Request

from vnexis.ivs.infrastructure.configuration.container import IvsContainer
from vnexis.ivs.interfaces.controllers.ivs_controller import IvsController

# app.state에 컨테이너를 보관할 때 사용하는 키(속성명)
CONTAINER_ATTR = "ivs_container"


def get_ivs_container(request: Request) -> IvsContainer:
    """현재 앱에 등록된 IVS 컨테이너를 반환한다.

    Raises:
        RuntimeError: lifespan이 실행되지 않아 컨테이너가 없는 경우
    """
    container = getattr(request.app.state, CONTAINER_ATTR, None)
    if container is None:
        raise RuntimeError(
            "IVS 컨테이너가 초기화되지 않았습니다. "
            "앱을 lifespan과 함께 실행해야 합니다."
        )
    return container


async def get_ivs_controller(request: Request) -> IvsController:
    """요청 처리에 사용할 IVS 컨트롤러를 반환한다.

    컨트롤러는 Singleton 프로바이더이므로 매 요청마다 같은 인스턴스가 나온다.
    무상태이며, 내부 Uow가 ContextVar 기반이라 동시 요청에도 안전하다.

    `async def`인 이유 (중요 — `def`로 되돌리지 말 것):
        FastAPI는 동기 의존성을 스레드풀(AnyIO worker thread)에서 실행한다.
        그런데 dependency-injector의 `providers.Singleton`에는 생성 잠금이 없어
        (그래서 `ThreadSafeSingleton`이 따로 존재한다), 여러 스레드가 동시에
        미생성 프로바이더를 해석하면 인스턴스가 중복 생성될 수 있다.
        `async def`로 두면 해석이 이벤트 루프에서만 일어나 그 경합 자체가 없다.
        (수명주기에서 컨트롤러를 미리 해석하는 것과 함께 이중 방어)
    """
    return get_ivs_container(request).ivs_controller()
