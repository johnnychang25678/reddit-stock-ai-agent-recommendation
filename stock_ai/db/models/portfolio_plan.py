from datetime import datetime
from stock_ai.db.base import Base

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, Float, JSON

class PortfolioPlan(Base):
    __tablename__ = "portfolio_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profits: Mapped[list[float]] = mapped_column(JSON)
    time_horizon_days: Mapped[int] = mapped_column(Integer)
    risk_reward: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)