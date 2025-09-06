from dataclasses import dataclass

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