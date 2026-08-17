"""
웹 UI용 데이터 포맷팅을 위한 웹 전용 프레젠터.
- IvsPresenter 추상 클래스의 웹 구현
- JSON 응답 및 HTML 템플릿에서 사용하기 적합한 형식으로 데이터 포맷팅
- 도메인 열거형/값 객체를 표시 문자열로 바꾸는 유일한 지점
"""

from pathlib import PurePath

from vnexis.core.view_models import ErrorViewModel
from vnexis.ivs.application.dtos.ivs_dtos import IvsResponse
from vnexis.ivs.domain.value_objects import AiModel, IvsStatus
from vnexis.ivs.interfaces.presenters.base import IvsPresenter
from vnexis.ivs.interfaces.view_models.ivs_vm import AiModelViewModel, IvsViewModel


class WebIvsPresenter(IvsPresenter):
    """웹 전용 IVS 프레젠터."""

    # 상태별 한국어 표시 문자열
    _STATUS_DISPLAY: dict[IvsStatus, str] = {
        IvsStatus.IDLE: "대기 중",
        IvsStatus.PENDING: "시작 준비 중",
        IvsStatus.RUNNING: "실행 중",
        IvsStatus.STOPPING: "중지 중",
    }

    def present_ivs(self, ivs_response: IvsResponse) -> IvsViewModel:
        """웹 표시용으로 IVS를 포맷한다."""
        return IvsViewModel(
            id=ivs_response.id,
            name=ivs_response.name,
            stream_url=ivs_response.stream_url,
            status=ivs_response.status.value,
            status_display=self._format_status(ivs_response.status),
            track_model=self._present_ai_model(ivs_response.track_model),
            defect_model=self._present_ai_model(ivs_response.defect_model),
        )

    def present_error(self, error_msg: str, code: str | None = None) -> ErrorViewModel:
        """웹 표시용으로 오류를 포맷한다."""
        return ErrorViewModel(message=error_msg, code=code or "ERROR")

    def _format_status(self, status: IvsStatus) -> str:
        """웹 표시용으로 상태를 포맷한다."""
        return self._STATUS_DISPLAY.get(status, status.value)

    def _present_ai_model(self, model: AiModel) -> AiModelViewModel:
        """웹 표시용으로 AI 모델 설정을 포맷한다."""
        file_name = PurePath(model.path).name or model.path
        confidence_display = f"{model.confidence:.2f}"
        threshold_display = f"{model.threshold:.2f}"
        return AiModelViewModel(
            path=model.path,
            confidence_display=confidence_display,
            threshold_display=threshold_display,
            summary=(
                f"{file_name} "
                f"(신뢰도 {confidence_display} / 임계값 {threshold_display})"
            ),
        )
