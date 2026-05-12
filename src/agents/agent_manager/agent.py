from functools import lru_cache
from typing import Any

from langgraph.prebuilt import create_react_agent

from src.agents.prompts.prompt_manager import prompt_manager
from src.config.settings import settings
from src.providers.ai.langchain_model_loader import LangchainModelLoader


def _validate_sample_agent_settings() -> None:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be configured before using the sample agent.")

    if not settings.OPENAI_MODEL_BASIC:
        raise ValueError(
            "OPENAI_MODEL_BASIC must be configured before using the sample agent."
        )


@lru_cache(maxsize=1)
def create_sample_agent() -> Any:
    """Build the sample agent lazily so non-agent routes do not depend on AI setup."""
    _validate_sample_agent_settings()

    loader = LangchainModelLoader()
    openai_basic_model = loader.init_model_openai_basic()

    return create_react_agent(
        openai_basic_model,
        tools=[],
        prompt=prompt_manager.sample_agent,
    )
