# 인프라스트럭처 계층의 영속화 모델 기본 클래스
# - 도메인 엔터티 기본 클래스(core/entity.py의 Entity)와 의도적으로 분리한다
# - 도메인은 SQLAlchemy를 전혀 알지 못하며, 두 표현 사이의 변환은 매퍼가 담당한다
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# 제약 조건 이름 규칙.
# SQLite는 ALTER TABLE 지원이 빈약해 Alembic이 batch 모드(테이블 재생성)로 동작하는데,
#   이름 없는 익명 제약 조건이 있으면 그 과정에서 마이그레이션이 실패한다.
#   규칙을 미리 고정해 두면 모든 제약 조건이 결정적인 이름을 갖는다.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """모든 영속화(ORM) 모델의 기본 클래스.

    Alembic의 autogenerate가 참조하는 메타데이터를 보유한다
    (`Base.metadata`). 새 모델을 추가하면 마이그레이션 env.py에서
    해당 모델 모듈을 import해야 메타데이터에 등록된다.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
