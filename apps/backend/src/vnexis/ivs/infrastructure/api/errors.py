"""
컨트롤러의 실패 결과를 HTTP 오류로 번역하는 모듈.

- 도메인/애플리케이션 오류를 HTTP 상태 코드로 매핑하는 책임은
  프레임워크 계층에 있다. 컨트롤러는 HTTP를 전혀 모른다
- 매핑 대상은 ErrorViewModel.code 문자열이다. 나올 수 있는 값은
  ErrorCode 열거형의 name(NOT_FOUND / VALIDATION_ERROR /
  BUSINESS_RULE_VIOLATION / UNAUTHORIZED / CONFLICT)과
  컨트롤러가 직접 넣는 UNEXPECTED_ERROR, 프레젠터 기본값 ERROR다
"""

import logging
from typing import NoReturn

from fastapi import HTTPException, status

from vnexis.core.view_models import OperationResult

logger = logging.getLogger(__name__)

# 5xx로 매핑되는 오류의 원본 메시지는 드라이버 예외 문자열(SQL 전문 포함)일 수
#   있으므로 그대로 노출하지 않고 이 고정 문구로 대체한다. 원본은 로그로 남긴다.
_INTERNAL_ERROR_MESSAGE = "서버 내부 오류가 발생했습니다"

# 알 수 없는 코드는 500으로 처리한다 (아래 _FALLBACK_STATUS)
_STATUS_BY_CODE: dict[str, int] = {
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    # Pydantic 본문 검증 실패가 이미 422를 쓰므로, 컨트롤러 단계의 검증 실패는
    #   400으로 구분한다 (예: 잘못된 UUID 형식)
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "BUSINESS_RULE_VIOLATION": status.HTTP_409_CONFLICT,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "UNEXPECTED_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}

_FALLBACK_STATUS = status.HTTP_500_INTERNAL_SERVER_ERROR


def status_for_code(code: str | None) -> int:
    """오류 코드 문자열에 대응하는 HTTP 상태 코드를 반환한다."""
    if code is None:
        return _FALLBACK_STATUS
    return _STATUS_BY_CODE.get(code, _FALLBACK_STATUS)


def raise_http_error(result: OperationResult) -> NoReturn:
    """실패한 OperationResult를 HTTPException으로 변환해 던진다.

    Args:
        result: 실패 상태의 OperationResult

    Raises:
        HTTPException: 매핑된 상태 코드와 오류 상세 정보
        ValueError: 성공 결과를 넘긴 경우 (OperationResult.error가 발생시킨다)
    """
    error = result.error
    status_code = status_for_code(error.code)

    message = error.message
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        # 원본은 로그로만 남기고 응답에는 내보내지 않는다
        logger.error(
            "Internal error surfaced to HTTP boundary",
            extra={"context": {"code": error.code, "error": error.message}},
        )
        message = _INTERNAL_ERROR_MESSAGE

    raise HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": message},
    )
