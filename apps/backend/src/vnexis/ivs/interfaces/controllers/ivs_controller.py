"""
인터페이스 어댑터 계층의 IVS 컨트롤러 모듈.

컨트롤러의 책임:
1. 외부 소스(웹 등)로부터 입력을 받는다
2. 해당 입력을 유스 케이스가 요구하는 형식(DTO)으로 변환한다
3. 적절한 유스 케이스를 실행한다
4. 결과를 인터페이스에 적합한 뷰 모델로 변환한다
5. 발생하는 오류를 처리하고 포맷한다

비동기 처리:
- IVS의 모든 유스 케이스는 `async def execute(...)`이므로
  모든 핸들러는 `async def`이며 유스 케이스를 await한다
- 이벤트 루프는 이 계층에서 시작하지 않는다 (asyncio.run/get_event_loop 사용 금지).
  웹 프레임워크가 핸들러를 await한다

구조화된 로깅 적용:
- 모든 핸들러 메서드에 요청/성공/실패 시점 로깅
- extra["context"]에 비즈니스 컨텍스트 포함하여 추적 가능
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from vnexis.core.view_models import OperationResult
from vnexis.ivs.application.dtos.ivs_dtos import CreateIvsRequest
from vnexis.ivs.application.use_cases.ivs_use_cases import (
    CreateIvsUseCase,
    GetIvsUseCase,
    ListIvsUseCase,
    PendingIvsUseCase,
    StopIvsUseCase,
)
from vnexis.ivs.domain.value_objects import AiModel
from vnexis.ivs.interfaces.presenters.base import IvsPresenter
from vnexis.ivs.interfaces.view_models.ivs_vm import IvsViewModel

logger = logging.getLogger(__name__)


@dataclass
class IvsController:
    """
    클린 아키텍처 패턴을 구현하는 IVS 관련 작업 컨트롤러.

    이 컨트롤러는 주요 클린 아키텍처 원칙을 보여준다:
    - 컨트롤러는 인터페이스 어댑터 계층에 존재한다
    - 유스 케이스에 대해 안쪽으로 의존한다 (의존성 규칙)
    - 계층 간 데이터 변환을 처리한다
    - 인터페이스 관심사를 비즈니스 로직으로부터 격리한다

    이 구현의 이점:
    - 비즈니스 로직이 유스 케이스에서 보호된다
    - 핵심 로직을 변경하지 않고 새 인터페이스를 추가할 수 있다
    - 의존성 주입을 통해 테스트가 단순화된다
    - 프레젠테이션 관심사가 적절히 분리된다

    Attributes:
        create_use_case: IVS 생성 유스 케이스
        get_use_case: IVS 조회 유스 케이스
        list_use_case: IVS 목록 조회 유스 케이스
        pending_use_case: IVS 시작 준비(pending) 전이 유스 케이스
        stop_use_case: IVS 중지 전이 유스 케이스
        presenter: 인터페이스를 위한 IVS 데이터 포맷팅 처리
    """

    # 의존성 주입을 통해 제공되는 유스 케이스 및 프레젠터
    create_use_case: CreateIvsUseCase
    get_use_case: GetIvsUseCase
    list_use_case: ListIvsUseCase
    pending_use_case: PendingIvsUseCase
    stop_use_case: StopIvsUseCase
    presenter: IvsPresenter

    async def handle_create(
        self,
        name: str,
        stream_url: str,
        track_model_path: str,
        track_model_confidence: float,
        track_model_threshold: float,
        defect_model_path: str,
        defect_model_confidence: float,
        defect_model_threshold: float,
    ) -> OperationResult[IvsViewModel]:
        """
        모든 인터페이스에서의 IVS 생성 요청을 처리한다.

        이 메서드는 다음과 같이 클린 아키텍처를 따른다:
        1. 원시 타입을 받아들인다 (인터페이스 비의존적)
        2. 데이터를 유스 케이스 형식으로 변환한다
        3. 유스 케이스를 통해 비즈니스 로직을 실행한다
        4. 결과를 인터페이스에 적합한 형식으로 변환한다

        Args:
            name: IVS 이름
            stream_url: 입력 스트림 URL
            track_model_path: 추적 모델 경로
            track_model_confidence: 추적 모델 신뢰도 (0.0 ~ 1.0)
            track_model_threshold: 추적 모델 임계값 (0.0 ~ 1.0)
            defect_model_path: 결함 검출 모델 경로
            defect_model_confidence: 결함 검출 모델 신뢰도 (0.0 ~ 1.0)
            defect_model_threshold: 결함 검출 모델 임계값 (0.0 ~ 1.0)

        Returns:
            다음 중 하나를 포함하는 OperationResult:
            - 성공: 인터페이스용으로 포맷된 IvsViewModel
            - 실패: 인터페이스용으로 포맷된 오류 정보
        """
        try:
            logger.info(
                "Handling IVS creation request",
                extra={
                    "context": {
                        "name": name,
                        "stream_url": stream_url,
                        "track_model_path": track_model_path,
                        "defect_model_path": defect_model_path,
                    }
                },
            )
            request = CreateIvsRequest(
                name=name,
                stream_url=stream_url,
                track_model=self._build_ai_model(
                    track_model_path, track_model_confidence, track_model_threshold
                ),
                defect_model=self._build_ai_model(
                    defect_model_path, defect_model_confidence, defect_model_threshold
                ),
            )
            result = await self.create_use_case.execute(request)

            if result.is_success:
                view_model = self.presenter.present_ivs(result.value)
                logger.info(
                    "IVS creation handled successfully",
                    extra={"context": {"ivs_id": result.value.id}},
                )
                return OperationResult.succeed(view_model)

            logger.error(
                "IVS creation failed",
                extra={
                    "context": {
                        "name": name,
                        "error": result.error.message,
                        "error_code": str(result.error.code.name),
                    }
                },
            )
            error_vm = self.presenter.present_error(
                result.error.message, str(result.error.code.name)
            )
            return OperationResult.fail(error_vm.message, error_vm.code)

        except ValueError as e:
            logger.error(
                "Validation error in IVS creation",
                extra={"context": {"name": name, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "VALIDATION_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)
        except Exception as e:
            logger.exception(
                "Unexpected error in IVS creation",
                extra={"context": {"name": name, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "UNEXPECTED_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)

    async def handle_get(self, ivs_id: str) -> OperationResult[IvsViewModel]:
        """
        IVS 조회 요청을 처리한다.

        Args:
            ivs_id: IVS의 고유 식별자

        Returns:
            다음 중 하나를 포함하는 OperationResult:
            - 성공: IVS 상세 정보가 포함된 IvsViewModel
            - 실패: 오류 정보
        """
        try:
            logger.info(
                "Handling IVS retrieval request",
                extra={"context": {"ivs_id": ivs_id}},
            )
            result = await self.get_use_case.execute(self._parse_ivs_id(ivs_id))

            if result.is_success:
                view_model = self.presenter.present_ivs(result.value)
                logger.info(
                    "IVS retrieval handled successfully",
                    extra={"context": {"ivs_id": ivs_id}},
                )
                return OperationResult.succeed(view_model)

            logger.error(
                "IVS retrieval failed",
                extra={
                    "context": {
                        "ivs_id": ivs_id,
                        "error": result.error.message,
                        "error_code": str(result.error.code.name),
                    }
                },
            )
            error_vm = self.presenter.present_error(
                result.error.message, str(result.error.code.name)
            )
            return OperationResult.fail(error_vm.message, error_vm.code)

        except ValueError as e:
            logger.error(
                "Validation error in IVS retrieval",
                extra={"context": {"ivs_id": ivs_id, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "VALIDATION_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)
        except Exception as e:
            logger.exception(
                "Unexpected error in IVS retrieval",
                extra={"context": {"ivs_id": ivs_id, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "UNEXPECTED_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)

    async def handle_list(self) -> OperationResult[list[IvsViewModel]]:
        """
        IVS 목록 요청을 처리한다.

        Returns:
            다음 중 하나를 포함하는 OperationResult:
            - 성공: IvsViewModel 객체 목록 (빈 목록도 성공이다)
            - 실패: 오류 정보
        """
        try:
            logger.info("Handling IVS list request")
            result = await self.list_use_case.execute()

            if result.is_success:
                view_models = [self.presenter.present_ivs(ivs) for ivs in result.value]
                logger.info(
                    "IVS list handled successfully",
                    extra={"context": {"count": len(view_models)}},
                )
                return OperationResult.succeed(view_models)

            logger.error(
                "IVS list failed",
                extra={
                    "context": {
                        "error": result.error.message,
                        "error_code": str(result.error.code.name),
                    }
                },
            )
            error_vm = self.presenter.present_error(
                result.error.message, str(result.error.code.name)
            )
            return OperationResult.fail(error_vm.message, error_vm.code)

        except Exception as e:
            logger.exception(
                "Unexpected error in IVS list", extra={"context": {"error": str(e)}}
            )
            error_vm = self.presenter.present_error(str(e), "UNEXPECTED_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)

    async def handle_pending(self, ivs_id: str) -> OperationResult[IvsViewModel]:
        """
        IVS 시작 준비(pending) 전이 요청을 처리한다.

        Args:
            ivs_id: IVS의 고유 식별자

        Returns:
            다음 중 하나를 포함하는 OperationResult:
            - 성공: 전이된 상태가 반영된 IvsViewModel
            - 실패: 오류 정보
        """
        try:
            logger.info(
                "Handling IVS pending request",
                extra={"context": {"ivs_id": ivs_id}},
            )
            result = await self.pending_use_case.execute(self._parse_ivs_id(ivs_id))

            if result.is_success:
                view_model = self.presenter.present_ivs(result.value)
                logger.info(
                    "IVS pending handled successfully",
                    extra={"context": {"ivs_id": ivs_id}},
                )
                return OperationResult.succeed(view_model)

            logger.error(
                "IVS pending failed",
                extra={
                    "context": {
                        "ivs_id": ivs_id,
                        "error": result.error.message,
                        "error_code": str(result.error.code.name),
                    }
                },
            )
            error_vm = self.presenter.present_error(
                result.error.message, str(result.error.code.name)
            )
            return OperationResult.fail(error_vm.message, error_vm.code)

        except ValueError as e:
            logger.error(
                "Validation error in IVS pending",
                extra={"context": {"ivs_id": ivs_id, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "VALIDATION_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)
        except Exception as e:
            logger.exception(
                "Unexpected error in IVS pending",
                extra={"context": {"ivs_id": ivs_id, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "UNEXPECTED_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)

    async def handle_stop(self, ivs_id: str) -> OperationResult[IvsViewModel]:
        """
        IVS 중지 요청을 처리한다.

        Args:
            ivs_id: IVS의 고유 식별자

        Returns:
            다음 중 하나를 포함하는 OperationResult:
            - 성공: 전이된 상태가 반영된 IvsViewModel
            - 실패: 오류 정보
        """
        try:
            logger.info(
                "Handling IVS stop request",
                extra={"context": {"ivs_id": ivs_id}},
            )
            result = await self.stop_use_case.execute(self._parse_ivs_id(ivs_id))

            if result.is_success:
                view_model = self.presenter.present_ivs(result.value)
                logger.info(
                    "IVS stop handled successfully",
                    extra={"context": {"ivs_id": ivs_id}},
                )
                return OperationResult.succeed(view_model)

            logger.error(
                "IVS stop failed",
                extra={
                    "context": {
                        "ivs_id": ivs_id,
                        "error": result.error.message,
                        "error_code": str(result.error.code.name),
                    }
                },
            )
            error_vm = self.presenter.present_error(
                result.error.message, str(result.error.code.name)
            )
            return OperationResult.fail(error_vm.message, error_vm.code)

        except ValueError as e:
            logger.error(
                "Validation error in IVS stop",
                extra={"context": {"ivs_id": ivs_id, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "VALIDATION_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)
        except Exception as e:
            logger.exception(
                "Unexpected error in IVS stop",
                extra={"context": {"ivs_id": ivs_id, "error": str(e)}},
            )
            error_vm = self.presenter.present_error(str(e), "UNEXPECTED_ERROR")
            return OperationResult.fail(error_vm.message, error_vm.code)

    def _build_ai_model(
        self, path: str, confidence: float, threshold: float
    ) -> AiModel:
        """원시 타입을 도메인 값 객체로 변환한다.

        잘못된 값은 ValueError로 전파되어 핸들러에서 VALIDATION_ERROR로 변환된다.

        Args:
            path: 모델 파일 경로
            confidence: 신뢰도 (0.0 ~ 1.0)
            threshold: 임계값 (0.0 ~ 1.0)

        Returns:
            검증·변환된 AiModel 값 객체

        Raises:
            ValueError: 경로가 비어 있거나 신뢰도/임계값이 숫자가 아니거나 범위를 벗어난 경우
        """
        normalized_path = (path or "").strip()
        if not normalized_path:
            raise ValueError("모델 경로는 필수입니다")

        # float("abc")는 ValueError를 발생시켜 핸들러의 except ValueError로 흘러간다
        confidence_value = float(confidence)
        threshold_value = float(threshold)

        if not 0.0 <= confidence_value <= 1.0:
            raise ValueError("신뢰도는 0.0 이상 1.0 이하여야 합니다")
        if not 0.0 <= threshold_value <= 1.0:
            raise ValueError("임계값은 0.0 이상 1.0 이하여야 합니다")

        return AiModel(
            path=normalized_path,
            confidence=confidence_value,
            threshold=threshold_value,
        )

    def _parse_ivs_id(self, ivs_id: str) -> str:
        """IVS ID 형식을 검증하고 정규화된 문자열을 반환한다.

        유스 케이스가 `execute(ivs_id: str)`를 받고 내부에서 UUID로 변환하므로
        UUID가 아니라 문자열을 반환한다. 이 메서드의 목적은 잘못된 ID에 대해
        CPython의 영문 메시지가 아니라 한국어 오류 메시지를 노출하는 것이다.

        Args:
            ivs_id: 검증할 IVS 식별자 문자열

        Returns:
            공백이 제거된 IVS 식별자 문자열

        Raises:
            ValueError: ID가 비어 있거나 UUID 형식이 아닌 경우
        """
        normalized = (ivs_id or "").strip()
        if not normalized:
            raise ValueError("IVS ID는 필수입니다")
        try:
            UUID(normalized)
        except ValueError as e:
            raise ValueError("잘못된 IVS ID 형식입니다") from e
        return normalized
