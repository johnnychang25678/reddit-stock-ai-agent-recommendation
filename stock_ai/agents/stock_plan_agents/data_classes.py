from dataclasses import dataclass
import stock_ai.agents.stock_plan_agents.pydantic_models

@dataclass
class TradePlan:
    ticker: str
    entry_price: float
    stop_loss: float
    take_profits: list[float]  # e.g., [TP1, TP2]
    time_horizon_days: int  # e.g., 30
    risk_reward: float  # e.g., 2.5
    rationale: str

    @classmethod
    def from_pydantic(cls, pydantic_obj: stock_ai.agents.stock_plan_agents.pydantic_models.TradePlan) -> "TradePlan":
        return cls(
            ticker=pydantic_obj.ticker,
            entry_price=pydantic_obj.entry_price,
            stop_loss=pydantic_obj.stop_loss,
            take_profits=pydantic_obj.take_profits,
            time_horizon_days=pydantic_obj.time_horizon_days,
            risk_reward=pydantic_obj.risk_reward,
            rationale=pydantic_obj.rationale,
        )
