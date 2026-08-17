# 프레젠터 추상 기본 클래스 모듈
# - 프레젠터: DTO(응답 데이터)를 뷰 모델(표시 데이터)로 변환하는 역할
# - 추상 클래스로 정의하여 각 인터페이스별 구체적 구현 강제
# - 의존성 역전 원칙: 컨트롤러가 추상 프레젠터에 의존
from abc import ABC, abstractmethod

from vnexis.core.view_models import ErrorViewModel
from vnexis.ivs.application.dtos.ivs_dtos import IvsResponse
from vnexis.ivs.interfaces.view_models.ivs_vm import IvsViewModel


class IvsPresenter(ABC):
    """IVS 관련 출력을 위한 추상 기본 프레젠터.
    - Web 등 각 인터페이스에서 이 클래스를 상속하여 구현
    - 목록 변환용 메서드는 두지 않는다. 컨트롤러가 present_ivs를 반복 적용한다
    - AiModel 변환은 자기 컨트롤러가 없는 값 객체이므로
      구체 프레젠터의 private 헬퍼로 둔다
    """

    @abstractmethod
    def present_ivs(self, ivs_response: IvsResponse) -> IvsViewModel:
        """IVS 응답을 뷰 모델로 변환한다."""
        pass

    @abstractmethod
    def present_error(self, error_msg: str, code: str | None = None) -> ErrorViewModel:
        """오류 메시지를 표시용으로 포맷한다."""
        pass
