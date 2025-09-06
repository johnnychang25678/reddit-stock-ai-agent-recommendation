from pydantic import BaseModel, Field

class TradePlan(BaseModel):
    ticker: str
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profits: list[float] = Field(..., min_items=1)  # e.g., [TP1, TP2]
    time_horizon_days: int = Field(..., ge=7, le=180)
    risk_reward: float = Field(..., gt=0)  # TP1-based or blended R:R
    rationale: str = Field(..., min_length=1, max_length=400)

class TradePlans(BaseModel):
    plans: list[TradePlan]
