import logging
from uuid import UUID

from vnexis.core.exceptions import BusinessRuleViolation, ValidationError
from vnexis.core.result import Error, Result
from vnexis.ivs.application.dtos.ivs_dtos import CreateIvsRequest, IvsResponse
from vnexis.ivs.application.repos.uow import Uow
from vnexis.ivs.domain.entities.ivs import Ivs
from vnexis.ivs.domain.exceptions import IvsNotFoundError

logger = logging.getLogger(__name__)

# 예기치 못한 예외를 사용자에게 전달할 때 쓰는 고정 문구.
#   예외 원문에는 SQL 전문 같은 내부 정보가 들어 있어 그대로 노출할 수 없다.
_UNEXPECTED_MESSAGE = "IVS 처리 중 오류가 발생했습니다"


class CreateIvsUseCase:
    def __init__(self, uow: Uow):
        self.uow = uow

    async def execute(self, request: CreateIvsRequest) -> Result[IvsResponse]:
        try:
            logger.info("Creating new ivs", extra={"context": {"name": request.name}})
            ivs = Ivs.create(
                name=request.name,
                stream_url=request.stream_url,
                track_model=request.track_model,
                defect_model=request.defect_model,
            )
            async with self.uow:
                await self.uow.ivs_repo.create(ivs)
                await self.uow.commit()

            logger.info(
                "IVS created successfully",
                extra={"context": {"ivs_id": ivs.id, "name": ivs.name}},
            )
            return Result.success(IvsResponse.from_entity(ivs))
        except ValidationError as e:
            logger.error(
                "Validation error while creating IVS",
                extra={"context": {"error": str(e)}},
            )
            return Result.failure(Error.validation_error(str(e)))
        except BusinessRuleViolation as e:
            logger.error(
                "Business rule violation while creating IVS",
                extra={"context": {"error": str(e)}},
            )
            return Result.failure(Error.business_rule_violation(str(e)))


class GetIvsUseCase:
    def __init__(self, uow: Uow):
        self.uow = uow

    async def execute(self, ivs_id: str) -> Result[IvsResponse]:
        try:
            logger.info("Retrieving IVS details", extra={"context": {"ivs_id": ivs_id}})
            async with self.uow:
                ivs = await self.uow.ivs_repo.get(UUID(ivs_id))
            return Result.success(IvsResponse.from_entity(ivs))
        except IvsNotFoundError:
            logger.error(
                "Ivs not found",
                extra={"context": {"ivs_id": ivs_id}},
            )
            return Result.failure(Error.not_found("Ivs", ivs_id))


class ListIvsUseCase:
    def __init__(self, uow: Uow):
        self.uow = uow

    async def execute(self) -> Result[list[IvsResponse]]:
        try:
            logger.info("Retrieving all IVS")
            async with self.uow:
                ivs_list = await self.uow.ivs_repo.list()
            logger.info(
                "IVS retrieved successfully",
                extra={"context": {"count": len(ivs_list)}},
            )
            return Result.success([IvsResponse.from_entity(i) for i in ivs_list])
        except Exception as e:
            logger.error("Failed to retrieve IVS", extra={"context": {"error": str(e)}})
            # 예기치 못한 예외의 원문(str(e))은 로그에만 남긴다.
            #   드라이버 예외 문자열에는 SQL 전문이 들어 있어 그대로 상위로
            #   올리면 HTTP 응답 본문으로 유출된다.
            return Result.failure(Error.business_rule_violation(_UNEXPECTED_MESSAGE))


class PendingIvsUseCase:
    def __init__(self, uow: Uow):
        self.uow = uow

    async def execute(self, ivs_id: str) -> Result[IvsResponse]:
        try:
            logger.info("Pending IVS", extra={"context": {"ivs_id": ivs_id}})
            async with self.uow:
                ivs = await self.uow.ivs_repo.get(UUID(ivs_id))
                ivs.mark_pending()
                await self.uow.ivs_repo.save(ivs)
                await self.uow.commit()
            logger.info(
                "IVS pending successfully",
                extra={"context": {"ivs_id": ivs_id}},
            )
            return Result.success(IvsResponse.from_entity(ivs))
        except IvsNotFoundError:
            logger.error("Ivs not found", extra={"context": {"ivs_id": ivs_id}})
            return Result.failure(Error.not_found("Ivs", ivs_id))
        except Exception as e:
            logger.error(
                "Failed to retrieve pending IVS", extra={"context": {"error": str(e)}}
            )
            return Result.failure(Error.business_rule_violation(_UNEXPECTED_MESSAGE))


class StopIvsUseCase:
    def __init__(self, uow: Uow):
        self.uow = uow

    async def execute(self, ivs_id: str) -> Result[IvsResponse]:
        try:
            logger.info("Stopping IVS", extra={"context": {"ivs_id": ivs_id}})
            async with self.uow:
                ivs = await self.uow.ivs_repo.get(UUID(ivs_id))
                ivs.mark_stopping()
                await self.uow.ivs_repo.save(ivs)
                await self.uow.commit()
            logger.info(
                "IVS stopped successfully", extra={"context": {"ivs_id": ivs_id}}
            )
            return Result.success(IvsResponse.from_entity(ivs))
        except IvsNotFoundError:
            logger.error("Ivs not found", extra={"context": {"ivs_id": ivs_id}})
            return Result.failure(Error.not_found("Ivs", ivs_id))
        except Exception as e:
            logger.error("Failed to stop IVS", extra={"context": {"error": str(e)}})
            return Result.failure(Error.business_rule_violation(_UNEXPECTED_MESSAGE))
