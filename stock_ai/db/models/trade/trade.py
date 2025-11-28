"""Database model for Trade."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from stock_ai.db.base import Base


class Trade(Base):
    """Historical trade log.

    Records every BUY, SELL, HOLD, and DO_NOTHING decision for performance analysis.
    """

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to Portfolio.id
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # BUY, SELL, HOLD, DO_NOTHING
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 for HOLD or DO_NOTHING
    price: Mapped[float] = mapped_column(Float, nullable=False)  # Per share price (SELL or BUY)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)  # quantity * price
    reason: Mapped[str] = mapped_column(String, nullable=False)  # Agent's decision reason
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For SELL trades only
    final_recommendation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK to FinalRecommendation.id if BUY
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
