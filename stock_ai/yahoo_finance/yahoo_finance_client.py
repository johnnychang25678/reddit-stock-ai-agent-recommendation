import yfinance as yf
from datetime import datetime, timedelta, timezone
import pandas as pd
import math
from stock_ai.yahoo_finance.types import StockSnapshot

class YahooFinanceClient:
    def _atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculates the Average True Range (ATR) for a given DataFrame.
        ATR is for measuring market volatility. For example an ATR of $1.50 means
        that the stock typically moves $1.50 per day.
        """
        h, l, c = df["High"], df["Low"], df["Close"]
        prev_close = c.shift(1)
        tr = pd.concat([
            (h - l).abs(),
            (h - prev_close).abs(),
            (l - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        return float(atr) if pd.notna(atr) else float("nan")

    def get_yf_snapshot(self, ticker: str, days: int = 365) -> StockSnapshot:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        hist = yf.Ticker(ticker).history(start=start, end=end, interval="1d", auto_adjust=False)
        if hist.empty:
            return StockSnapshot(
                ticker=ticker,
                error="No historical data found",
                price=float("nan"),
                sma20=float("nan"),
                sma50=float("nan"),
                sma200=float("nan"),
                atr14=float("nan"),
                high_52w=float("nan"),
                low_52w=float("nan"),
                rsi14=float("nan"),
                asof=end.isoformat(),
            )

        atr14 = self._atr(hist, 14)

        # current price
        close = float(hist["Close"].iloc[-1])
        # simple moving averages
        sma20 = float(hist["Close"].rolling(20).mean().iloc[-1])
        sma50 = float(hist["Close"].rolling(50).mean().iloc[-1])
        sma200 = float(hist["Close"].rolling(200).mean().iloc[-1])
        # 52 week high/low
        high_52w = float(hist["High"].rolling(252, min_periods=1).max().iloc[-1])
        low_52w  = float(hist["Low"].rolling(252, min_periods=1).min().iloc[-1])

        # RSI: Relative Strength Index
        # - It’s a momentum oscillator created by J. Welles Wilder.
        # - It measures the speed and magnitude of recent price changes to spot when a stock might be overbought or oversold.
        # - Values range between 0 and 100.
        # >70 -> stock is considered overbought (price run-up may be stretched).
        # <30 -> stock is considered oversold (price selloff may be stretched).
        # 50 -> neutral, no clear momentum bias.

        delta = hist["Close"].diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = (-delta.clip(upper=0)).rolling(14).mean()
        rs = up / (down.replace(0, float("nan")))
        rsi14 = 100 - (100 / (1 + rs))
        rsi_val = float(rsi14.iloc[-1]) if not math.isnan(rsi14.iloc[-1]) else float("nan")

        ROUND_DIGITS = 2

        return StockSnapshot(
            ticker=ticker,
            price=self._round(close, ROUND_DIGITS),
            sma20=self._round(sma20, ROUND_DIGITS),
            sma50=self._round(sma50, ROUND_DIGITS),
            sma200=self._round(sma200, ROUND_DIGITS),
            atr14=self._round(atr14, ROUND_DIGITS),
            high_52w=self._round(high_52w, ROUND_DIGITS),
            low_52w=self._round(low_52w, ROUND_DIGITS),
            rsi14=self._round(rsi_val, ROUND_DIGITS),
            asof=end.isoformat(),
        )

    def _round(self, value: float, ndigits: int = 2) -> float:
        """Rounds a float to a specified number of decimal places."""
        if math.isnan(value):
            return float("nan")
        return round(value, ndigits)

    def get_current_price(self, ticker: str) -> float:
        """Get the current/latest price for a ticker.
        
        Returns the most recent price available:
        - During market hours: may include intraday price
        - After hours: returns last close price
        """
        try:
            stock = yf.Ticker(ticker)
            # Try to get real-time price first
            info = stock.info
            
            # Priority order for getting current price
            current_price = (
                info.get("currentPrice") or 
                info.get("regularMarketPrice") or
                info.get("previousClose")
            )
            
            if current_price is None or math.isnan(float(current_price)):
                return float("nan")
                
            return round(float(current_price), 2)
        except Exception as e:
            print(f"Error fetching current price for {ticker}: {e}")
            return float("nan")

# Example usage:
# cl = YahooFinanceClient()
# price = cl.get_current_price("^GSPC")
# print(price)