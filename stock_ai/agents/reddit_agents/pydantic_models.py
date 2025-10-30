from typing import Literal
from pydantic import BaseModel, Field

class StockRecommendation(BaseModel):
    ticker: str
    decision: Literal["BUY", "REJECT"]
    reason: str = Field(..., description="Why you decided to BUY or REJECT this stock")
    confidence: Literal["high", "medium", "low"] | None = Field(None, description="Only set if decision is BUY")
    reddit_post_url: str | None = None

class StockRecommendations(BaseModel):
    recommendations: list[StockRecommendation]
