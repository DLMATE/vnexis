"""
HTTP 요청 본문 스키마 (프레임워크 경계 전용).

- Pydantic 모델은 이 계층에만 존재한다. 라우터가 이 모델을 컨트롤러의
  원시 타입 인자로 풀어서 넘기므로 Pydantic이 내부 계층으로 침투하지 않는다
- 응답에는 Pydantic 모델을 쓰지 않는다. 인터페이스 계층의 뷰 모델
  (IvsViewModel)을 그대로 반환한다
"""

from pydantic import BaseModel, Field


class AiModelPayload(BaseModel):
    """AI 모델 설정 요청 본문."""

    path: str = Field(min_length=1, max_length=500, description="모델 파일 경로")
    confidence: float = Field(ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")
    threshold: float = Field(ge=0.0, le=1.0, description="임계값 (0.0 ~ 1.0)")


class CreateIvsPayload(BaseModel):
    """IVS 생성 요청 본문."""

    name: str = Field(min_length=1, max_length=100, description="IVS 이름")
    stream_url: str = Field(
        min_length=1, max_length=500, description="입력 스트림 URL"
    )
    track_model: AiModelPayload = Field(description="추적 모델 설정")
    defect_model: AiModelPayload = Field(description="결함 검출 모델 설정")
