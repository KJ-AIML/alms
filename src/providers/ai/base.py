from abc import ABC, abstractmethod
from typing import Any


class AIModelProvider(ABC):
    @abstractmethod
    def get_chat_model(self, tier: str = "basic", **kwargs: Any) -> Any:
        """Return a configured chat model. tier: 'basic' or 'reasoning'."""
