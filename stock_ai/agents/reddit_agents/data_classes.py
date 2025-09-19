
from dataclasses import dataclass
import stock_ai.agents.reddit_agents.pydantic_models 


@dataclass
class StockRecommendation:
    ticker: str
    reason: str
    confidence: str  # "high", "medium", "low"
    reddit_post_url: str | None

    @classmethod
    def from_pydantic(cls, pydantic_obj: stock_ai.agents.reddit_agents.pydantic_models.StockRecommendation) -> "StockRecommendation":
        return cls(
            ticker=pydantic_obj.ticker,
            reason=pydantic_obj.reason,
            confidence=pydantic_obj.confidence,
            reddit_post_url=pydantic_obj.reddit_post_url,
        )
