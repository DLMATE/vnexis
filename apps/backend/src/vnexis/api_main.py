"""
HTTP API의 진입점 (컴포지션 루트).

- 여기서만 의존성을 조립한다. 안쪽 계층은 무엇이 자신을 조립했는지 모른다
- 바운디드 컨텍스트가 늘어나면 컨테이너와 include_router를 여기에 추가한다

실행:
    uv run --package vnexis uvicorn vnexis.api_main:app --reload
    또는  uv run --package vnexis python -m vnexis.api_main
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from vnexis.core.config import Config
from vnexis.ivs.infrastructure.api.dependencies import CONTAINER_ATTR
from vnexis.ivs.infrastructure.api.routers.ivs_router import router as ivs_router
from vnexis.ivs.infrastructure.configuration.container import IvsContainer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명주기 동안 컨테이너와 DB 엔진을 관리한다."""
    container = IvsContainer()
    container.config.database_url.from_value(Config.get_database_url())

    # 그래프의 말단(컨트롤러)을 미리 해석해 두면 엔진·세션팩토리·Uow·유스케이스가
    #   전부 함께 생성된다. 두 가지 효과가 있다:
    #   1) 잘못된 database_url 등 배선 오류가 첫 요청이 아니라 기동 시점에 드러난다
    #   2) providers.Singleton에는 생성 잠금이 없어서, 요청이 몰린 상태에서 처음
    #      해석되면 중복 생성 경합이 날 수 있다. 미리 만들어 두면 그 창이 닫힌다
    container.ivs_controller()
    engine = container.engine()  # 종료 시 dispose할 대상을 지역 변수로 확정한다
    setattr(app.state, CONTAINER_ATTR, container)
    logger.info(
        "Application started", extra={"context": {"database_url": str(engine.url)}}
    )

    yield

    await engine.dispose()
    logger.info("Application stopped")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성하고 라우터를 등록한다."""
    app = FastAPI(
        title="Vnexis API",
        description="IVS(지능형 영상 감시) 관리 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """컨트롤러 바깥(의존성 해석 등)에서 터진 예외를 JSON 봉투로 통일한다.

        이 핸들러가 없으면 Starlette가 text/plain "Internal Server Error"를
        반환해서, 다른 모든 오류가 JSON인 것과 형식이 어긋난다.
        """
        logger.exception(
            "Unhandled error outside controller",
            extra={"context": {"path": request.url.path}},
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "UNEXPECTED_ERROR",
                    "message": "서버 내부 오류가 발생했습니다",
                }
            },
        )

    # include_router만 쓴다. mount()는 하위 앱의 lifespan을 실행하지 않고
    #   request.app.state 접근도 끊기므로 컨텍스트를 추가할 때도 include_router를 쓸 것
    app.include_router(ivs_router)
    return app


app = create_app()


def main() -> None:
    """개발용 서버를 실행한다."""
    import uvicorn

    uvicorn.run("vnexis.api_main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
