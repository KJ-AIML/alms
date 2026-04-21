from fastapi import Depends

from src.agents.agent_manager.agent import create_sample_agent
from src.core.exceptions import AppException
from src.execution.actions.sample_action import SampleAction
from src.execution.usecases.sample_usecase import SampleUseCase


def get_sample_agent():
    try:
        return create_sample_agent()
    except ValueError as exc:
        raise AppException(
            message=str(exc),
            status_code=503,
            error_code="AGENT_UNAVAILABLE",
        ) from exc


def get_sample_action(agent=Depends(get_sample_agent)) -> SampleAction:
    return SampleAction(agent=agent)


def get_sample_usecase(action=Depends(get_sample_action)) -> SampleUseCase:
    return SampleUseCase(action=action)
