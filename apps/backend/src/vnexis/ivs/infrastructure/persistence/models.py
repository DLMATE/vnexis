"""
IVS 영속화(ORM) 모델.
- 도메인 엔터티(Ivs)와 분리된 저장 전용 표현
- 도메인이 SQLAlchemy에 의존하지 않도록 하기 위한 별도 모델이며,
  두 표현 사이의 변환은 mappers 모듈이 담당한다
"""

from uuid import UUID

from sqlalchemy import Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from vnexis.core.db.entity import Base


class IvsModel(Base):
    """IVS 테이블의 ORM 모델."""

    __tablename__ = "ivs"

    # Uuid는 백엔드 중립 제네릭 타입이다. 네이티브 UUID가 없는 SQLite에서는
    #   문자열로 저장되지만 파이썬 쪽에는 UUID 객체가 그대로 돌아온다.
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # IvsStatus는 str 기반 열거형이라 값(value)을 그대로 문자열로 저장한다.
    #   SQL 열거형 타입을 쓰지 않으므로 상태가 추가돼도 마이그레이션이 필요 없다.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    stream_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # AiModel 값 객체 2개를 각각 3개 컬럼으로 평탄화한다
    track_model_path: Mapped[str] = mapped_column(String(500), nullable=False)
    track_model_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    track_model_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    defect_model_path: Mapped[str] = mapped_column(String(500), nullable=False)
    defect_model_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    defect_model_threshold: Mapped[float] = mapped_column(Float, nullable=False)
