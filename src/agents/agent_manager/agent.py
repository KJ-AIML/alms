from functools import lru_cache
from typing import Any

from langgraph.prebuilt import create_react_agent

from src.config.settings import settings
from src.agents.prompts.sample_agent_prompt import get_prompt_sample_agent
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
    prompt_sample_agent = get_prompt_sample_agent()

    return create_react_agent(
        openai_basic_model,
        tools=[],
        prompt=prompt_sample_agent,
    )
