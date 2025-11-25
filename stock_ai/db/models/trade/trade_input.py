"""Database model for Trade Inputs."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from stock_ai.db.base import Base


class TradeInput(Base):
    """Prepared inputs for trade decision agent.

    Stores recommendations, prices, positions, and portfolio state
    for a specific trading run.
    """

    __tablename__ = "trade_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    has_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, nullable=False)
    portfolio_cash: Mapped[float] = mapped_column(Float, nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of recommendations
    prices_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON object of ticker -> price
    positions_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of current positions
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
