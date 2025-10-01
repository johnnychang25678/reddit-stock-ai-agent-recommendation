from datetime import datetime
from stock_ai.db.base import Base

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, Float, DateTime

class RunMetaData(Base):
    __tablename__ = "run_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)