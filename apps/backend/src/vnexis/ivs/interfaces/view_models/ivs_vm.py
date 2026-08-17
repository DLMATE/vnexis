# IVS 뷰 모델 모듈
# - 프레젠터가 생성하고 UI(Web)에서 소비하는 표시용 데이터 구조
# - 불변(frozen) 객체로 뷰 계층에서 데이터 변경 방지
from dataclasses import dataclass


@dataclass(frozen=True)
class AiModelViewModel:
    """AI 모델 설정의 뷰 전용 표현.
    - 도메인 값 객체(AiModel)와 분리된 표시 전용 데이터
    """

    path: str  # 원본 모델 경로 (식별자성 필드 - 수정 폼에서 재사용)
    confidence_display: str  # 포맷된 신뢰도 문자열
    threshold_display: str  # 포맷된 임계값 문자열
    summary: str  # 목록 표시용 한 줄 요약


@dataclass(frozen=True)
class IvsViewModel:
    """IVS의 뷰 전용 표현.
    - 도메인 엔터티와 분리된 표시 전용 데이터
    - 각 표시 필드는 이미 포맷된 문자열 (프레젠터가 변환)
    - AI 모델 설정은 중첩 뷰 모델로 표현
    """

    id: str
    name: str
    stream_url: str
    # 원시 상태값. UI가 시작/중지 버튼을 분기할 때 사용한다.
    #   한국어 표시 문자열(status_display)을 비교하게 만들지 않기 위한 필드
    status: str
    status_display: str  # 사람이 읽을 수 있는 상태
    track_model: AiModelViewModel
    defect_model: AiModelViewModel
