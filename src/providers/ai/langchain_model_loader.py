import os
from typing import Any, ClassVar, Dict, Optional

from langchain.chat_models import init_chat_model

from src.config.settings import settings
from src.providers.ai.base import AIModelProvider


class LangchainModelLoader(AIModelProvider):
    _instance: ClassVar[Optional["LangchainModelLoader"]] = None

    def __new__(cls) -> "LangchainModelLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.models: Dict[str, Any] = {}
        self._setup_api_keys()
        self._initialized = True

    def _setup_api_keys(self) -> None:
        if settings.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

    def _get_openai_config(self, **kwargs: Any) -> Dict[str, Any]:
        config = {"temperature": kwargs.pop("temperature", 0.0)}
        config["api_key"] = kwargs.pop("api_key", settings.OPENAI_API_KEY)
        config.update(kwargs)
        return config

    def init_model_openai_basic(self, temperature: float = 0.0, **kwargs: Any) -> Any:
        config = self._get_openai_config(temperature=temperature, **kwargs)
        model = init_chat_model(model=settings.OPENAI_MODEL_BASIC, **config)
        self.models["openai_basic"] = model
        return model

    def init_model_openai_reasoning(
        self, temperature: float = 0.0, **kwargs: Any
    ) -> Any:
        config = self._get_openai_config(temperature=temperature, **kwargs)
        model = init_chat_model(model=settings.OPENAI_MODEL_REASONING, **config)
        self.models["openai_reasoning"] = model
        return model

    def get_model(self, model_name: str) -> Optional[Any]:
        return self.models.get(model_name)

    def list_available_models(self) -> list[str]:
        return list(self.models.keys())

    def get_chat_model(self, tier: str = "basic", **kwargs: Any) -> Any:
        if tier == "reasoning":
            return self.init_model_openai_reasoning(**kwargs)
        return self.init_model_openai_basic(**kwargs)
