"""
도메인 엔터티(Ivs) ↔ 영속화 모델(IvsModel) 변환 매퍼.
- 이 모듈이 두 표현 사이의 유일한 접점이며, 덕분에 도메인은 SQLAlchemy를 모른다
- 값 객체(AiModel)의 평탄화/복원도 여기서만 일어난다
"""

from vnexis.ivs.domain.entities.ivs import Ivs
from vnexis.ivs.domain.value_objects import AiModel, IvsStatus
from vnexis.ivs.infrastructure.persistence.models import IvsModel


def to_entity(model: IvsModel) -> Ivs:
    """ORM 모델을 도메인 엔터티로 변환한다.

    Args:
        model: 조회된 ORM 모델

    Returns:
        복원된 도메인 엔터티
    """
    ivs = Ivs(
        name=model.name,
        status=IvsStatus(model.status),
        stream_url=model.stream_url,
        track_model=AiModel(
            path=model.track_model_path,
            confidence=model.track_model_confidence,
            threshold=model.track_model_threshold,
        ),
        defect_model=AiModel(
            path=model.defect_model_path,
            confidence=model.defect_model_confidence,
            threshold=model.defect_model_threshold,
        ),
    )
    # Entity.id는 init=False라 생성자로 넘길 수 없다.
    #   저장된 식별자를 유지하기 위해 생성 후 명시적으로 대입한다.
    ivs.id = model.id
    return ivs


def to_model(entity: Ivs) -> IvsModel:
    """도메인 엔터티로부터 새 ORM 모델을 만든다 (INSERT용).

    Args:
        entity: 저장할 도메인 엔터티

    Returns:
        세션에 추가할 새 ORM 모델
    """
    return IvsModel(
        id=entity.id,
        name=entity.name,
        status=entity.status.value,
        stream_url=entity.stream_url,
        track_model_path=entity.track_model.path,
        track_model_confidence=entity.track_model.confidence,
        track_model_threshold=entity.track_model.threshold,
        defect_model_path=entity.defect_model.path,
        defect_model_confidence=entity.defect_model.confidence,
        defect_model_threshold=entity.defect_model.threshold,
    )


def apply_to_model(entity: Ivs, model: IvsModel) -> None:
    """기존 ORM 모델에 엔터티의 현재 상태를 반영한다 (UPDATE용).

    식별자(id)는 갱신하지 않는다.

    Args:
        entity: 변경된 도메인 엔터티
        model: 갱신 대상 ORM 모델 (세션에 붙어 있어야 한다)
    """
    model.name = entity.name
    model.status = entity.status.value
    model.stream_url = entity.stream_url
    model.track_model_path = entity.track_model.path
    model.track_model_confidence = entity.track_model.confidence
    model.track_model_threshold = entity.track_model.threshold
    model.defect_model_path = entity.defect_model.path
    model.defect_model_confidence = entity.defect_model.confidence
    model.defect_model_threshold = entity.defect_model.threshold
