"""Format Adanos sentiment data into text blocks for AI agent prompts."""

from __future__ import annotations

import re
from typing import Any

from stock_ai.sentiment.adanos_client import AdanosClient, TickerSentiment, TrendingTicker


# Common words that look like tickers but aren't
_TICKER_EXCLUDE = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN",
    "HER", "WAS", "ONE", "OUR", "OUT", "HAS", "HIS", "HOW", "ITS",
    "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GET",
    "LET", "SAY", "SHE", "TOO", "USE", "WHY", "GPU", "CEO", "IPO",
    "ETF", "ATH", "OEM", "FDA", "SEC", "IMO", "FOMO", "YOLO", "DD",
    "WSB", "EPS", "FCF", "TAM", "ATR", "RSI", "SMA", "USA", "NEWS",
}

_TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b")


def extract_tickers_from_text(texts: list[str]) -> list[str]:
    """Extract likely ticker symbols from text strings.

    Supports $TSLA-style cashtags and bare uppercase symbols.
    Excludes common abbreviations (FDA, CEO, WSB, etc.).
    """
    tickers: set[str] = set()
    for text in texts:
        for m in _TICKER_PATTERN.finditer(text):
            ticker = m.group(1) or m.group(2)
            if ticker not in _TICKER_EXCLUDE:
                tickers.add(ticker)
    return sorted(tickers)


def _fmt_sentiment(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score > 0.15:
        return f"bullish ({score:+.2f})"
    if score < -0.15:
        return f"bearish ({score:+.2f})"
    return f"neutral ({score:+.2f})"


def _fmt_trend(trend: str | None) -> str:
    return trend if trend else "N/A"


def _format_ticker_sentiment(sentiments: list[TickerSentiment]) -> str:
    """Format multi-platform sentiment for one ticker."""
    if not sentiments:
        return ""
    ticker = sentiments[0].ticker
    lines = [f"  {ticker}:"]
    for s in sentiments:
        if not s.found:
            lines.append(f"    {s.platform}: no data")
            continue
        parts = [
            f"buzz={s.buzz_score}/100",
            f"sentiment={_fmt_sentiment(s.sentiment_score)}",
            f"trend={_fmt_trend(s.trend)}",
            f"mentions={s.mentions}",
        ]
        if s.bullish_pct is not None:
            parts.append(f"bullish={s.bullish_pct}%")
        if s.bearish_pct is not None:
            parts.append(f"bearish={s.bearish_pct}%")
        lines.append(f"    {s.platform}: {', '.join(parts)}")
    return "\n".join(lines)


class SentimentEnricher:
    """Builds sentiment context blocks for AI agent prompts.

    Usage::

        enricher = SentimentEnricher(adanos_client)
        context = enricher.build_context(["TSLA", "NVDA"], days=7)
        # Inject `context` into your agent's user prompt
    """

    def __init__(self, client: AdanosClient):
        self.client = client

    def build_context(
        self,
        tickers: list[str],
        *,
        days: int = 7,
        platforms: tuple[str, ...] = ("reddit", "x", "polymarket"),
        include_trending: bool = True,
        trending_limit: int = 10,
    ) -> str:
        """Build a sentiment context block for injection into an LLM prompt.

        Args:
            tickers: Stock symbols to look up.
            days: Lookback period (1-90).
            platforms: Which platforms to query.
            include_trending: Whether to append trending overview.
            trending_limit: Max trending tickers per platform.

        Returns:
            Formatted text block ready for LLM prompt injection.
        """
        sections: list[str] = []
        sections.append(f"# Adanos Cross-Platform Sentiment Data (last {days} days)")
        sections.append(
            "Source: https://api.adanos.org — algorithmic sentiment from "
            "VADER + RoBERTa ensemble across 20+ subreddits, X/Twitter, and Polymarket."
        )
        sections.append("")

        # Per-ticker multi-platform data
        if tickers:
            multi = self.client.get_multi_platform_sentiment(
                tickers, platforms=platforms, days=days
            )
            sections.append("## Ticker Sentiment")
            for ticker in tickers:
                sentiments = multi.get(ticker, [])
                block = _format_ticker_sentiment(sentiments)
                if block:
                    sections.append(block)
            sections.append("")

        # Trending overview
        if include_trending:
            sections.append("## Trending Stocks (by buzz score)")
            for platform in platforms:
                trending = self.client.get_trending(
                    platform=platform, days=days, limit=trending_limit
                )
                if trending:
                    sections.append(f"  {platform}:")
                    for t in trending:
                        sections.append(
                            f"    {t.ticker}: buzz={t.buzz_score}, "
                            f"sentiment={_fmt_sentiment(t.sentiment_score)}, "
                            f"trend={_fmt_trend(t.trend)}"
                        )
                else:
                    sections.append(f"  {platform}: no trending data")
            sections.append("")

        return "\n".join(sections)

    def build_picker_context(
        self,
        tickers: list[str],
        *,
        days: int = 7,
        platforms: tuple[str, ...] = ("reddit", "x", "polymarket"),
    ) -> str:
        """Build a compact context block for the StockPickerAgent.

        Focuses on cross-platform agreement/divergence signals.
        """
        multi = self.client.get_multi_platform_sentiment(
            tickers, platforms=platforms, days=days
        )

        sections: list[str] = []
        sections.append("# Cross-Platform Sentiment Signals (Adanos API)")
        sections.append("")

        for ticker in tickers:
            sentiments = multi.get(ticker, [])
            found_platforms = [s for s in sentiments if s.found]

            if not found_platforms:
                sections.append(f"  {ticker}: no sentiment data available")
                continue

            # Calculate agreement
            scores = [s.sentiment_score for s in found_platforms if s.sentiment_score is not None]
            buzz_scores = [s.buzz_score for s in found_platforms if s.buzz_score is not None]

            avg_sentiment = sum(scores) / len(scores) if scores else None
            max_buzz = max(buzz_scores) if buzz_scores else None
            trends = [s.trend for s in found_platforms if s.trend]

            # Check for divergence
            has_bullish = any(s > 0.15 for s in scores)
            has_bearish = any(s < -0.15 for s in scores)
            divergent = has_bullish and has_bearish

            parts = []
            if avg_sentiment is not None:
                parts.append(f"avg_sentiment={_fmt_sentiment(avg_sentiment)}")
            if max_buzz is not None:
                parts.append(f"peak_buzz={max_buzz}/100")
            if trends:
                parts.append(f"trends={'/'.join(trends)}")
            parts.append(f"platforms_with_data={len(found_platforms)}/{len(sentiments)}")
            if divergent:
                parts.append("DIVERGENT_SIGNALS")

            sections.append(f"  {ticker}: {', '.join(parts)}")

        sections.append("")
        sections.append(
            "Note: High buzz + rising trend + cross-platform bullish agreement = strongest signal. "
            "Divergent signals across platforms warrant extra scrutiny."
        )
        return "\n".join(sections)
