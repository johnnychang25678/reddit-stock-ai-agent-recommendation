"""Database model for PerformanceSnapshot."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from stock_ai.db.base import Base


class PerformanceSnapshot(Base):
    """Weekly performance tracking snapshot.

    Captures portfolio metrics and benchmark comparison for historical analysis.
    """

    __tablename__ = "performance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to Portfolio.id
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Float, nullable=False)  # Cumulative P&L
    roi_percent: Mapped[float] = mapped_column(Float, nullable=False)  # Cumulative ROI

    # S&P 500 benchmark tracking (cumulative)
    sp500_initial_value: Mapped[float] = mapped_column(Float, nullable=False)  # When a portfolio is created
    sp500_current_value: Mapped[float] = mapped_column(Float, nullable=False)  # At this snapshot
    sp500_cumulative_return_percent: Mapped[float] = mapped_column(Float, nullable=False)
    alpha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # roi_percent - sp500_return

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
