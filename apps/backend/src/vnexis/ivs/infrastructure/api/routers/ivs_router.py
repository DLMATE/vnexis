"""
IVS HTTP 라우터 (프레임워크 계층).

라우터의 책임은 HTTP 관심사로만 제한된다:
1. 요청 본문/경로 변수를 파싱·검증한다 (Pydantic)
2. 그것을 컨트롤러가 받는 원시 타입으로 풀어서 넘긴다
3. 컨트롤러의 OperationResult를 상태 코드로 번역한다

비즈니스 판단은 하지 않는다. 상태 전이 가능 여부 같은 규칙은 도메인의 몫이다.
"""

from fastapi import APIRouter, Depends, status

from vnexis.ivs.infrastructure.api.dependencies import get_ivs_controller
from vnexis.ivs.infrastructure.api.errors import raise_http_error
from vnexis.ivs.infrastructure.api.schemas import CreateIvsPayload
from vnexis.ivs.interfaces.controllers.ivs_controller import IvsController
from vnexis.ivs.interfaces.view_models.ivs_vm import IvsViewModel

router = APIRouter(prefix="/ivs", tags=["ivs"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="IVS 생성")
async def create_ivs(
    payload: CreateIvsPayload,
    controller: IvsController = Depends(get_ivs_controller),
) -> IvsViewModel:
    """새 IVS를 등록한다."""
    result = await controller.handle_create(
        name=payload.name,
        stream_url=payload.stream_url,
        track_model_path=payload.track_model.path,
        track_model_confidence=payload.track_model.confidence,
        track_model_threshold=payload.track_model.threshold,
        defect_model_path=payload.defect_model.path,
        defect_model_confidence=payload.defect_model.confidence,
        defect_model_threshold=payload.defect_model.threshold,
    )
    if not result.is_success:
        raise_http_error(result)
    return result.success


@router.get("", summary="IVS 목록 조회")
async def list_ivs(
    controller: IvsController = Depends(get_ivs_controller),
) -> list[IvsViewModel]:
    """등록된 모든 IVS를 조회한다."""
    result = await controller.handle_list()
    if not result.is_success:
        raise_http_error(result)
    return result.success


@router.get("/{ivs_id}", summary="IVS 상세 조회")
async def get_ivs(
    ivs_id: str,
    controller: IvsController = Depends(get_ivs_controller),
) -> IvsViewModel:
    """ID로 IVS를 조회한다."""
    result = await controller.handle_get(ivs_id)
    if not result.is_success:
        raise_http_error(result)
    return result.success


@router.post("/{ivs_id}/start", summary="IVS 시작 요청")
async def start_ivs(
    ivs_id: str,
    controller: IvsController = Depends(get_ivs_controller),
) -> IvsViewModel:
    """IVS를 시작 준비(pending) 상태로 전이시킨다."""
    result = await controller.handle_pending(ivs_id)
    if not result.is_success:
        raise_http_error(result)
    return result.success


@router.post("/{ivs_id}/stop", summary="IVS 중지 요청")
async def stop_ivs(
    ivs_id: str,
    controller: IvsController = Depends(get_ivs_controller),
) -> IvsViewModel:
    """IVS를 중지(stopping) 상태로 전이시킨다."""
    result = await controller.handle_stop(ivs_id)
    if not result.is_success:
        raise_http_error(result)
    return result.success
