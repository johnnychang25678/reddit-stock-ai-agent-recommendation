from datetime import datetime
from stock_ai.db.base import Base

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, Float, DateTime

class RedditFilteredPost(Base):
    __tablename__ = "reddit_filtered_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    reddit_id: Mapped[str] = mapped_column(String, nullable=True)
    flair: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    selftext: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer)
    num_comments: Mapped[int] = mapped_column(Integer)
    upvote_ratio: Mapped[float] = mapped_column(Float)
    created: Mapped[datetime] = mapped_column(DateTime)
    url: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)