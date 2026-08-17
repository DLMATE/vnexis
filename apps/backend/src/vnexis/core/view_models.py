# 인터페이스 계층의 공통 뷰 모델 모듈
# - 뷰 모델: 프레젠테이션 계층에서 사용하는 데이터 구조 (표시용 데이터만 포함)
# - OperationResult: Either 패턴으로 성공/실패를 타입 안전하게 표현
# - core에 두어 여러 바운디드 컨텍스트(ivs, ai, ...)가 공유한다.
#   단, core는 절대 interfaces를 import하지 않는다 (역방향 의존 금지)
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ErrorViewModel:
    """선택적 오류 코드를 가진 오류를 나타낸다.

    Attributes:
        message: 사람이 읽을 수 있는 오류 메시지
        code: 프로그래밍적 오류 처리를 위한 선택적 오류 코드
    """

    message: str
    code: str | None = None


@dataclass
class OperationResult(Generic[T]):
    """값으로 성공하거나 오류로 실패할 수 있는 작업의 결과를 나타낸다.

    이 클래스는 Either 패턴을 구현하며, 결과는 성공 또는 실패 중 하나만
    될 수 있고 둘 다이거나 둘 다 아닐 수 없다. 이는 명시적 오류 처리와
    None 검사 방지에 도움이 된다. 또한 Mypy 및 기타 정적 타입 검사기로
    타입 검사를 가능하게 한다.

    is_success가 `self._success is not None`이므로 None을 성공 값으로
    담는 것은 구조적으로 불가능하다. 반환할 값이 없는 작업이라면
    DeletionOutcome 같은 결과 DTO를 페이로드로 사용해야 한다.

    Type Parameters:
        T: 성공 값의 타입

    Attributes:
        _success: 작업이 성공한 경우의 성공 값
        _error: 작업이 실패한 경우의 오류 세부 정보
    """

    _success: T | None = None
    _error: ErrorViewModel | None = None

    def __init__(
        self, success: T | None = None, error: ErrorViewModel | None = None
    ) -> None:
        """성공 값 또는 오류로 결과를 초기화한다.

        Args:
            success: 작업이 성공한 경우의 성공 값
            error: 작업이 실패한 경우의 오류 세부 정보

        Raises:
            ValueError: 성공과 오류가 둘 다 제공되지 않았거나 둘 다 제공된 경우
        """
        if (success is None and error is None) or (
            success is not None and error is not None
        ):
            raise ValueError("성공 또는 오류 중 하나만 제공해야 합니다")
        self._success = success
        self._error = error

    @property
    def is_success(self) -> bool:
        """작업이 성공했는지 여부를 나타낸다."""
        return self._success is not None

    @property
    def success(self) -> T:
        """성공 값을 반환한다.

        Raises:
            ValueError: 오류 결과에서 성공 값에 접근하는 경우
        """
        if self._success is None:
            raise ValueError("오류 결과에서 성공 값에 접근할 수 없습니다")
        return self._success

    @property
    def error(self) -> ErrorViewModel:
        """오류 세부 정보를 반환한다.

        Raises:
            ValueError: 성공 결과에서 오류 값에 접근하는 경우
        """
        if self._error is None:
            raise ValueError("성공 결과에서 오류 값에 접근할 수 없습니다")
        return self._error

    @classmethod
    def succeed(cls, value: T) -> "OperationResult[T]":
        """주어진 값으로 성공 결과를 생성한다.

        Args:
            value: 성공 값

        Returns:
            성공을 나타내는 새 OperationResult 인스턴스
        """
        return cls(success=value)

    @classmethod
    def fail(cls, message: str, code: str | None = None) -> "OperationResult[T]":
        """주어진 오류 메시지와 선택적 코드로 실패 결과를 생성한다.

        Args:
            message: 오류 메시지
            code: 선택적 오류 코드

        Returns:
            실패를 나타내는 새 OperationResult 인스턴스
        """
        return cls(error=ErrorViewModel(message, code))
