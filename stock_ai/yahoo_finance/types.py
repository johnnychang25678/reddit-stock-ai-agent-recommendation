from dataclasses import dataclass

import stock_ai.db.models.financial_snapshot

@dataclass
class StockSnapshot:
    ticker: str
    price: float
    sma20: float
    sma50: float
    sma200: float
    atr14: float
    high_52w: float
    low_52w: float
    rsi14: float
    asof: str  # ISO format datetime string
    error : str | None = None  # Optional error field to indicate issues like "no_data"

    @classmethod
    def from_orm(cls, orm_obj: "stock_ai.db.models.financial_snapshot.FinancialSnapshot") -> "StockSnapshot":
        return cls(
            ticker=orm_obj.ticker,
            price=orm_obj.price,
            sma20=orm_obj.sma20,
            sma50=orm_obj.sma50,
            sma200=orm_obj.sma200,
            atr14=orm_obj.atr14,
            high_52w=orm_obj.high_52w,
            low_52w=orm_obj.low_52w,
            rsi14=orm_obj.rsi14,
            asof=orm_obj.asof,
        )