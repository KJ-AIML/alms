"""Dependency injection providers for v1 endpoints.

Agent/action imports are guarded so the module can be imported
when AI dependencies (langchain, langgraph, openai) are not installed.
"""

from fastapi import Depends

from src.config.logs_config import get_logger

logger = get_logger(__name__)

# --- Optional AI imports ---
_create_sample_agent = None
_SampleAction = None
_SampleUseCase = None

try:
    from src.agents.agent_manager.agent import create_sample_agent as _csa
    from src.execution.actions.sample_action import SampleAction as _SA
    from src.execution.usecases.sample_usecase import SampleUseCase as _SU

    _create_sample_agent = _csa
    _SampleAction = _SA
    _SampleUseCase = _SU
except ImportError:
    logger.info("AI dependencies not installed -- sample agent DI unavailable")

from src.core.exceptions import AppException


def get_sample_agent():
    if _create_sample_agent is None:
        raise AppException(
            message="AI dependencies are not installed. Install with: uv sync --extra ai",
            status_code=503,
            error_code="AGENT_UNAVAILABLE",
        )
    try:
        return _create_sample_agent()
    except ValueError as exc:
        raise AppException(
            message=str(exc),
            status_code=503,
            error_code="AGENT_UNAVAILABLE",
        ) from exc


def get_sample_action(agent=Depends(get_sample_agent)):
    if _SampleAction is None:
        raise AppException(
            message="AI dependencies are not installed.",
            status_code=503,
            error_code="AGENT_UNAVAILABLE",
        )
    return _SampleAction(agent=agent)


def get_sample_usecase(action=Depends(get_sample_action)):
    if _SampleUseCase is None:
        raise AppException(
            message="AI dependencies are not installed.",
            status_code=503,
            error_code="AGENT_UNAVAILABLE",
        )
    return _SampleUseCase(action=action)