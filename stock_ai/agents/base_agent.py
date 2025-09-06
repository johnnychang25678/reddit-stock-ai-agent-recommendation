from typing import Any
from abc import ABC, abstractmethod
from openai import OpenAI

class BaseAgent(ABC):
    """Abstract base class for AI agents that use OpenAI client.
    Sub-classes must implement system_prompt, user_prompt, and act methods.
    """

    def __init__(self, open_ai_client: OpenAI):
        super().__init__()
        self.open_ai_client = open_ai_client


    @property
    @abstractmethod
    def system_prompt(self) -> str:
        pass

    @abstractmethod
    def user_prompt(self, context: Any) -> str:
        pass

    @abstractmethod
    def act(self, context: Any) -> Any:
        pass
