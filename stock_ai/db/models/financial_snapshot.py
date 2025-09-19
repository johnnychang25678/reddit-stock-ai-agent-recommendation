from datetime import datetime
from stock_ai.db.base import Base

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, Float

class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    price: Mapped[float] = mapped_column(Float)
    sma20: Mapped[float] = mapped_column(Float)
    sma50: Mapped[float] = mapped_column(Float)
    sma200: Mapped[float] = mapped_column(Float)
    atr14: Mapped[float] = mapped_column(Float)
    high_52w: Mapped[float] = mapped_column(Float)
    low_52w: Mapped[float] = mapped_column(Float)
    rsi14: Mapped[float] = mapped_column(Float)
    asof: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)