from typing import Literal
from pydantic import BaseModel

class StockRecommendation(BaseModel):
    ticker: str
    reason: str
    confidence: Literal["high", "medium", "low"]
    reddit_post_url: str | None = None  # Optional field to reference the Reddit post url

class StockRecommendations(BaseModel):
    recommendations: list[StockRecommendation]
