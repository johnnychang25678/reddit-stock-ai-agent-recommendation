from typing import Literal
from pydantic import BaseModel

class StockRecommendation(BaseModel):
    ticker: str
    reason: str
    confidence: Literal["high", "medium", "low"]

class StockRecommendations(BaseModel):
    recommendations: list[StockRecommendation]
