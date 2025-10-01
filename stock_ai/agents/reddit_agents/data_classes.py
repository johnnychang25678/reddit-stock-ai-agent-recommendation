
from dataclasses import dataclass
import stock_ai.agents.reddit_agents.pydantic_models 
import stock_ai.db.models.dd_recommendation
import stock_ai.db.models.yolo_recommendation
import stock_ai.db.models.news_recommendation


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
    
    @classmethod
    def from_orm(cls, orm_obj: stock_ai.db.models.dd_recommendation.DdRecommendation | 
                 stock_ai.db.models.yolo_recommendation.YoloRecommendation | 
                 stock_ai.db.models.news_recommendation.NewsRecommendation) -> "StockRecommendation":
        return cls(
            ticker=orm_obj.ticker,
            reason=orm_obj.reason,
            confidence=orm_obj.confidence,
            reddit_post_url=orm_obj.reddit_post_url,
        )
