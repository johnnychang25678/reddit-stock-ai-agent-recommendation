from abc import ABC, abstractmethod
from openai import OpenAI
from stock_ai.reddit.types import RedditPost
from stock_ai.agents.pydantic_models import StockRecommendations
import json
import time
import os

class BaseAgent(ABC):
    """Abstract base class for agents that analyze Reddit posts and provide stock recommendations.
    Sub-classes implement system_prompt and user_prompt methods.
    Shared act method to interact with OpenAI API and handle responses.
    """
    def __init__(self, open_ai_client: OpenAI):
        super().__init__()
        self.open_ai_client = open_ai_client


    @property
    @abstractmethod
    def system_prompt(self) -> str:
        pass

    @abstractmethod
    def user_prompt(self, posts: list[RedditPost]) -> str:
        pass

    def act(self, posts: list[RedditPost]) -> StockRecommendations:
        agent_cls_name = self.__class__.__name__
        print(f"{agent_cls_name} acting on posts...")
        user_prompt = self.user_prompt(posts)
        start = time.perf_counter()
        resp = self.open_ai_client.responses.parse(
            model="gpt-5",
            instructions=self.system_prompt,
            input=user_prompt,
            text_format=StockRecommendations,
            reasoning={"effort": "medium"},
        )
        end = time.perf_counter()
        print(f"NewsAgent act() completed in {end - start:.2f} seconds.")

        print("Raw response:", resp)

        result = resp.output_parsed

        # write system promt, user prompt, and response to a single file for debugging
        os.makedirs("debug", exist_ok=True)
        with open(f"debug/{agent_cls_name.lower()}_debug_{int(time.time())}.txt", "w", encoding="utf-8") as f:
            f.write("SYSTEM PROMPT:\n")
            f.write(self.system_prompt)
            f.write("\n\nUSER PROMPT:\n")
            f.write(user_prompt)
            f.write("\n\nRESPONSE:\n")
            # Convert Pydantic model to dict for JSON serialization
            result_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
            f.write(json.dumps(result_dict, ensure_ascii=False, indent=2))

            # write raw response too
            f.write("\n\nRAW RESPONSE:\n")
            f.write(str(resp))

        return resp.output_parsed
