"""
도메인 계층의 예외 클래스 모듈.
- 도메인 모델에 특화된 오류 조건을 표현하는 예외 계층 구조
- 외부 계층(application, infrastructure)에서 이 예외를 잡아 적절히 처리
- 도메인 예외를 통해 비즈니스 규칙 위반을 명확하게 전달
"""


class DomainError(Exception):
    """도메인 특화 오류의 기본 클래스.
    - 모든 도메인 예외의 공통 부모 클래스
    """


class ValidationError(DomainError):
    """도메인 검증 규칙이 위반되었을 때 발생한다."""


class BusinessRuleViolation(DomainError):
    """비즈니스 규칙이 위반되었을 때 발생한다."""
