from stock_ai.db.base import Base
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

class Test(Base):
    __tablename__ = "test_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    some_flag: Mapped[bool] = mapped_column(Boolean, default=True)
