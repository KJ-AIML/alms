from fastapi import APIRouter, Depends, status

from src.api.endpoints.v1.schemas.base import AppResponse
from src.api.endpoints.v1.dependencies import get_sample_usecase
from src.api.endpoints.v1.schemas.sample import SampleQueryRequest, SampleQueryResponse
from src.config.logs_config import get_logger
from src.execution.usecases.sample_usecase import SampleUseCase

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/sample-di",
    response_model=AppResponse[SampleQueryResponse],
    status_code=status.HTTP_200_OK,
)
async def sample_di_endpoint(
    request: SampleQueryRequest, usecase: SampleUseCase = Depends(get_sample_usecase)
):
    """
    Sample endpoint demonstrating Dependency Injection flow:
    Endpoint -> UseCase -> Action -> Agent
    """
    logger.info(f"Received sample DI request: {request.query}")

    response_content = await usecase.execute(request.query)

    return AppResponse(
        success=True,
        data=SampleQueryResponse(response=response_content),
    )
