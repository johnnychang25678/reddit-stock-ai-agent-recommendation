from typing import Any
from abc import ABC, abstractmethod
from openai import OpenAI

class BaseAgent(ABC):
    """Abstract base class for AI agents that use OpenAI client.
    Sub-classes must implement system_prompt, user_prompt, and act methods.
    """
    COMMON_PROMPTS: dict[str, str] = {
        "AGENTIC_BALANCE": """# Agentic Balance:
- Proceed autonomously to generate recommendations; in all cases, do not stop to request clarification even if critical decision information is missing. Continue based on the best available data and your established criteria."""
    }

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
    def act(self, context: Any, **kwargs) -> Any:
        # use kwargs to create params for eval
        pass

    @abstractmethod
    def evaluate(self, result: Any, **kwargs) -> Any:
        """
        To evaluate the result of act.
        Open to implementation, can either fix the result, or run a while loop until satisfactory
        """
        pass
