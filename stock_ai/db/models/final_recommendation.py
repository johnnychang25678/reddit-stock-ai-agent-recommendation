from datetime import datetime
from stock_ai.db.base import Base

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime

class FinalRecommendation(Base):
    __tablename__ = "final_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    reason: Mapped[str] = mapped_column(Text)  # reason for the recommendation (
    confidence: Mapped[str] = mapped_column(String)  # "high" | "medium" | "low"
    reddit_post_url: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)