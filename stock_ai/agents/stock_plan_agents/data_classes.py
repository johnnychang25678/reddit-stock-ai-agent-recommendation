from dataclasses import dataclass
import stock_ai.agents.stock_plan_agents.pydantic_models
import stock_ai.db.models.portfolio_plan

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

    @classmethod
    def from_orm(cls, orm_obj: "stock_ai.db.models.portfolio_plan.PortfolioPlan") -> "TradePlan":
        return cls(
            ticker=orm_obj.ticker,
            entry_price=orm_obj.entry_price,
            stop_loss=orm_obj.stop_loss,
            take_profits=orm_obj.take_profits,
            time_horizon_days=orm_obj.time_horizon_days,
            risk_reward=orm_obj.risk_reward,
            rationale=orm_obj.rationale,
        )