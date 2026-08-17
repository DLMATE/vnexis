# 도메인 계층의 엔터티 기본 클래스
# - 모든 엔터티의 공통 속성(ID)과 동일성 비교 로직을 정의
# - 엔터티는 고유한 식별자(ID)로 구분되는 도메인 객체
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Entity:
    """모든 도메인 엔터티의 기본 클래스.

    하위 클래스는 반드시 `@dataclass(eq=False)`로 선언해야 한다.
    dataclass 기본값(eq=True)으로 선언하면 하위 클래스에 __eq__가 새로 생성되어
    아래 ID 기반 동일성이 가려지고, 동시에 __hash__가 None으로 설정되어
    엔터티가 unhashable이 된다.
    """

    # 'id' 필드에 대해 고유 UUID를 자동 생성;
    #   __init__ 메서드에서 제외됨 (하위 클래스의 필수 필드보다 앞에 와도 무해)
    id: UUID = field(default_factory=uuid4, init=False)

    # 엔터티의 동일성은 ID로만 판단 (값 객체와의 핵심 차이점)
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.id == other.id

    # 해시값도 ID 기반 (딕셔너리/세트에서 사용 가능)
    def __hash__(self) -> int:
        return hash(self.id)
