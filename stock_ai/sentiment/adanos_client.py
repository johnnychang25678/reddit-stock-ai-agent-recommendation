"""Lightweight client for the Adanos Sentiment API (https://api.adanos.org).

Only depends on httpx — no SDK install required. Fetches stock sentiment
data from Reddit (20+ subreddits), X/Twitter, and Polymarket.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class TickerSentiment:
    """Sentiment data for a single ticker from one platform."""
    ticker: str
    platform: str
    found: bool = False
    buzz_score: float | None = None
    sentiment_score: float | None = None
    trend: str | None = None  # "rising" | "falling" | "stable"
    mentions: int = 0
    bullish_pct: float | None = None
    bearish_pct: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendingTicker:
    """A ticker from the trending endpoint."""
    ticker: str
    company_name: str | None = None
    buzz_score: float | None = None
    sentiment_score: float | None = None
    trend: str | None = None


class AdanosClient:
    """Fetch stock sentiment from the Adanos API.

    Requires an API key. Get a free one (250 req/month) at https://api.adanos.org/docs

    Set via env var ``ADANOS_API_KEY`` or pass directly.
    """

    BASE_URL = "https://api.adanos.org"

    def __init__(self, api_key: str | None = None, timeout: float = 15.0):
        self.api_key = api_key or os.getenv("ADANOS_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Adanos API key required. Set ADANOS_API_KEY env var or pass api_key=."
            )
        self._http = httpx.Client(
            base_url=self.BASE_URL,
            headers={"X-API-Key": self.api_key},
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "AdanosClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get(self, path: str, **params: Any) -> dict | list | None:
        """Make a GET request, return JSON or None on error."""
        try:
            resp = self._http.get(path, params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"[AdanosClient] {path} failed: {e}")
            return None

    def get_stock_sentiment(
        self, ticker: str, *, platform: str = "reddit", days: int = 7
    ) -> TickerSentiment:
        """Get sentiment for a single ticker on a given platform.

        Args:
            ticker: Stock symbol (e.g. "TSLA").
            platform: "reddit", "x", or "polymarket".
            days: Lookback period (1-90).
        """
        path_map = {
            "reddit": f"/reddit/stocks/v1/stock/{ticker}",
            "x": f"/x/stocks/v1/stock/{ticker}",
            "polymarket": f"/polymarket/stocks/v1/stock/{ticker}",
        }
        path = path_map.get(platform)
        if not path:
            raise ValueError(f"Unknown platform: {platform}")

        data = self._get(path, days=days)
        if not data:
            return TickerSentiment(ticker=ticker, platform=platform)

        return TickerSentiment(
            ticker=ticker,
            platform=platform,
            found=data.get("found", True),
            buzz_score=data.get("buzz_score"),
            sentiment_score=data.get("sentiment_score"),
            trend=data.get("trend"),
            mentions=data.get("mentions", data.get("total_mentions", 0)) or data.get("trade_count", 0),
            bullish_pct=data.get("bullish_pct"),
            bearish_pct=data.get("bearish_pct"),
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "ticker",
                    "found",
                    "buzz_score",
                    "sentiment_score",
                    "trend",
                    "mentions",
                    "total_mentions",
                    "trade_count",
                    "bullish_pct",
                    "bearish_pct",
                }
            },
        )

    def get_trending(
        self, *, platform: str = "reddit", days: int = 7, limit: int = 10
    ) -> list[TrendingTicker]:
        """Get trending tickers from a platform.

        Args:
            platform: "reddit", "x", or "polymarket".
            days: Lookback period.
            limit: Max results.
        """
        path_map = {
            "reddit": "/reddit/stocks/v1/trending",
            "x": "/x/stocks/v1/trending",
            "polymarket": "/polymarket/stocks/v1/trending",
        }
        path = path_map.get(platform)
        if not path:
            raise ValueError(f"Unknown platform: {platform}")

        data = self._get(path, days=days, limit=limit)
        if not data or not isinstance(data, list):
            return []

        return [
            TrendingTicker(
                ticker=item.get("ticker", ""),
                company_name=item.get("company_name"),
                buzz_score=item.get("buzz_score"),
                sentiment_score=item.get("sentiment_score"),
                trend=item.get("trend"),
            )
            for item in data
        ]

    def get_multi_platform_sentiment(
        self,
        tickers: list[str],
        *,
        platforms: tuple[str, ...] = ("reddit", "x", "polymarket"),
        days: int = 7,
    ) -> dict[str, list[TickerSentiment]]:
        """Get sentiment for multiple tickers across multiple platforms.

        Returns:
            Dict mapping ticker -> list of TickerSentiment (one per platform).
        """
        result: dict[str, list[TickerSentiment]] = {}
        for ticker in tickers:
            sentiments = []
            for platform in platforms:
                sentiments.append(
                    self.get_stock_sentiment(ticker, platform=platform, days=days)
                )
            result[ticker] = sentiments
        return result
