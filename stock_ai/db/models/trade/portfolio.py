"""Database model for Portfolio."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from stock_ai.db.base import Base


class Portfolio(Base):
    """Portfolio for simulated trading.

    Represents a trading account with cash and positions.
    """

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)  # cash + positions market value
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    last_update_run_id: Mapped[str] = mapped_column(String, nullable=False)  # YYYYMMDD of last trade
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
