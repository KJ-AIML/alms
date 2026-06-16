from src.providers.ai.base import AIModelProvider
from src.providers.ai.langchain_model_loader import LangchainModelLoader


def get_ai_provider() -> AIModelProvider:
    # ponytail: single provider; add google/anthropic branches here when MODEL_PROVIDER != "openai"
    return LangchainModelLoader()
