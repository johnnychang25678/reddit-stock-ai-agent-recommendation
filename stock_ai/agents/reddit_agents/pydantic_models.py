from typing import Literal
from pydantic import BaseModel

class StockRecommendation(BaseModel):
    ticker: str
    reason: str
    confidence: Literal["high", "medium", "low"]
    reddit_post_url: str | None = None  # This field currently hallucinates in some cases, no solution now

class StockRecommendations(BaseModel):
    recommendations: list[StockRecommendation]
