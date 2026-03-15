"""Tests for the Adanos sentiment enricher and client data structures."""

import pytest
from unittest.mock import MagicMock, patch

from stock_ai.sentiment.adanos_client import AdanosClient, TickerSentiment, TrendingTicker
from stock_ai.sentiment.enricher import (
    SentimentEnricher,
    _fmt_sentiment,
    _fmt_trend,
    _format_ticker_sentiment,
)


# --- Formatting helpers ---

class TestFmtSentiment:
    def test_bullish(self):
        assert "bullish" in _fmt_sentiment(0.25)

    def test_bearish(self):
        assert "bearish" in _fmt_sentiment(-0.30)

    def test_neutral(self):
        assert "neutral" in _fmt_sentiment(0.05)

    def test_none(self):
        assert _fmt_sentiment(None) == "N/A"

    def test_boundary_positive(self):
        assert "neutral" in _fmt_sentiment(0.15)

    def test_boundary_negative(self):
        assert "neutral" in _fmt_sentiment(-0.15)


class TestFmtTrend:
    def test_rising(self):
        assert _fmt_trend("rising") == "rising"

    def test_none(self):
        assert _fmt_trend(None) == "N/A"


# --- TickerSentiment formatting ---

class TestFormatTickerSentiment:
    def test_with_data(self):
        sentiments = [
            TickerSentiment(
                ticker="TSLA", platform="reddit", found=True,
                buzz_score=72, sentiment_score=0.23, trend="rising",
                mentions=342, bullish_pct=61, bearish_pct=22,
            ),
            TickerSentiment(
                ticker="TSLA", platform="x", found=True,
                buzz_score=68, sentiment_score=0.18, trend="rising",
                mentions=1205, bullish_pct=58, bearish_pct=25,
            ),
        ]
        result = _format_ticker_sentiment(sentiments)
        assert "TSLA:" in result
        assert "reddit:" in result
        assert "buzz=72/100" in result
        assert "x:" in result

    def test_not_found(self):
        sentiments = [
            TickerSentiment(ticker="XYZ", platform="reddit", found=False),
        ]
        result = _format_ticker_sentiment(sentiments)
        assert "no data" in result

    def test_empty(self):
        assert _format_ticker_sentiment([]) == ""


# --- SentimentEnricher ---

class TestSentimentEnricher:
    def _mock_client(self):
        client = MagicMock(spec=AdanosClient)
        client.get_multi_platform_sentiment.return_value = {
            "TSLA": [
                TickerSentiment(
                    ticker="TSLA", platform="reddit", found=True,
                    buzz_score=72, sentiment_score=0.23, trend="rising",
                    mentions=342, bullish_pct=61, bearish_pct=22,
                ),
                TickerSentiment(
                    ticker="TSLA", platform="x", found=True,
                    buzz_score=68, sentiment_score=0.18, trend="rising",
                    mentions=1205, bullish_pct=58, bearish_pct=25,
                ),
            ],
        }
        client.get_trending.return_value = [
            TrendingTicker(
                ticker="TSLA", company_name="Tesla Inc",
                buzz_score=72, sentiment_score=0.23, trend="rising",
            ),
            TrendingTicker(
                ticker="NVDA", company_name="NVIDIA Corp",
                buzz_score=68, sentiment_score=0.31, trend="stable",
            ),
        ]
        return client

    def test_build_context(self):
        enricher = SentimentEnricher(self._mock_client())
        ctx = enricher.build_context(["TSLA"], days=7, platforms=("reddit", "x"))
        assert "Adanos Cross-Platform Sentiment Data" in ctx
        assert "TSLA" in ctx
        assert "buzz=72/100" in ctx
        assert "Trending Stocks" in ctx

    def test_build_context_no_trending(self):
        enricher = SentimentEnricher(self._mock_client())
        ctx = enricher.build_context(["TSLA"], days=7, include_trending=False)
        assert "Trending Stocks" not in ctx
        assert "TSLA" in ctx

    def test_build_picker_context(self):
        enricher = SentimentEnricher(self._mock_client())
        ctx = enricher.build_picker_context(["TSLA"], days=7, platforms=("reddit", "x"))
        assert "Cross-Platform Sentiment Signals" in ctx
        assert "TSLA" in ctx
        assert "avg_sentiment" in ctx

    def test_build_picker_context_divergent(self):
        """When platforms disagree, flag DIVERGENT_SIGNALS."""
        client = MagicMock(spec=AdanosClient)
        client.get_multi_platform_sentiment.return_value = {
            "AAPL": [
                TickerSentiment(
                    ticker="AAPL", platform="reddit", found=True,
                    buzz_score=60, sentiment_score=0.30, trend="rising",
                    mentions=100, bullish_pct=70, bearish_pct=15,
                ),
                TickerSentiment(
                    ticker="AAPL", platform="x", found=True,
                    buzz_score=55, sentiment_score=-0.25, trend="falling",
                    mentions=200, bullish_pct=30, bearish_pct=55,
                ),
            ],
        }
        enricher = SentimentEnricher(client)
        ctx = enricher.build_picker_context(["AAPL"], platforms=("reddit", "x"))
        assert "DIVERGENT_SIGNALS" in ctx

    def test_build_picker_context_no_data(self):
        client = MagicMock(spec=AdanosClient)
        client.get_multi_platform_sentiment.return_value = {
            "XYZ": [
                TickerSentiment(ticker="XYZ", platform="reddit", found=False),
            ],
        }
        enricher = SentimentEnricher(client)
        ctx = enricher.build_picker_context(["XYZ"], platforms=("reddit",))
        assert "no sentiment data" in ctx


# --- Workflow ticker extraction ---

class TestTickerExtraction:
    def test_extract_tickers(self):
        from stock_ai.sentiment.enricher import extract_tickers_from_text

        texts = ["NVDA earnings next week. Loading up on $TSLA calls too"]
        tickers = extract_tickers_from_text(texts)
        assert "NVDA" in tickers
        assert "TSLA" in tickers

    def test_excludes_common_words(self):
        from stock_ai.sentiment.enricher import extract_tickers_from_text

        texts = ["IMO the CEO said FDA will approve. WSB is all about YOLO on ATH"]
        tickers = extract_tickers_from_text(texts)
        assert "IMO" not in tickers
        assert "CEO" not in tickers
        assert "FDA" not in tickers
        assert "WSB" not in tickers
        assert "YOLO" not in tickers
        assert "ATH" not in tickers

    def test_empty(self):
        from stock_ai.sentiment.enricher import extract_tickers_from_text
        assert extract_tickers_from_text([]) == []

    def test_cashtag(self):
        from stock_ai.sentiment.enricher import extract_tickers_from_text
        tickers = extract_tickers_from_text(["$AAPL is looking good"])
        assert "AAPL" in tickers


# --- Agent sentiment_context passthrough ---

class TestAgentSentimentContext:
    def test_news_agent_includes_context(self):
        from stock_ai.agents.reddit_agents.news_agent import NewsAgent
        from stock_ai.reddit.types import RedditPost
        from datetime import datetime

        agent = NewsAgent(MagicMock(), sentiment_context="## Adanos Data\nTSLA: bullish")
        post = RedditPost(
            reddit_id="t1", title="Test", selftext="Content", score=10, num_comments=5,
            upvote_ratio=0.8, flair="News", created=datetime.now(), url="http://x.com",
        )
        prompt = agent.user_prompt([post])
        assert "Adanos Data" in prompt
        assert "TSLA: bullish" in prompt

    def test_news_agent_no_context(self):
        from stock_ai.agents.reddit_agents.news_agent import NewsAgent
        from stock_ai.reddit.types import RedditPost
        from datetime import datetime

        agent = NewsAgent(MagicMock(), sentiment_context="")
        post = RedditPost(
            reddit_id="t1", title="Test", selftext="Content", score=10, num_comments=5,
            upvote_ratio=0.8, flair="News", created=datetime.now(), url="http://x.com",
        )
        prompt = agent.user_prompt([post])
        assert "Adanos" not in prompt

    def test_picker_agent_includes_context(self):
        from stock_ai.agents.stock_plan_agents.stock_picker_agent import StockPickerAgent
        from stock_ai.agents.reddit_agents.data_classes import StockRecommendation

        agent = StockPickerAgent(MagicMock(), sentiment_context="## Sentiment\nTSLA: rising")
        rec = StockRecommendation(
            ticker="TSLA", reason="Strong earnings", confidence="high",
            reddit_post_url="http://x.com",
        )
        prompt = agent.user_prompt([rec])
        assert "Sentiment" in prompt
        assert "TSLA: rising" in prompt

    def test_picker_agent_no_context(self):
        from stock_ai.agents.stock_plan_agents.stock_picker_agent import StockPickerAgent
        from stock_ai.agents.reddit_agents.data_classes import StockRecommendation

        agent = StockPickerAgent(MagicMock(), sentiment_context="")
        rec = StockRecommendation(
            ticker="TSLA", reason="Strong earnings", confidence="high",
            reddit_post_url="http://x.com",
        )
        prompt = agent.user_prompt([rec])
        assert "Sentiment" not in prompt

    def test_dd_agent_includes_context(self):
        from stock_ai.agents.reddit_agents.dd_agent import DDAgent
        from stock_ai.reddit.types import RedditPost
        from datetime import datetime

        agent = DDAgent(MagicMock(), sentiment_context="## Data\nNVDA: stable")
        post = RedditPost(
            reddit_id="t2", title="Test", selftext="Content", score=10, num_comments=5,
            upvote_ratio=0.8, flair="DD", created=datetime.now(), url="http://x.com",
        )
        prompt = agent.user_prompt([post])
        assert "NVDA: stable" in prompt

    def test_yolo_agent_includes_context(self):
        from stock_ai.agents.reddit_agents.yolo_agent import YoloAgent
        from stock_ai.reddit.types import RedditPost
        from datetime import datetime

        agent = YoloAgent(MagicMock(), sentiment_context="## Data\nAMD: bearish")
        post = RedditPost(
            reddit_id="t3", title="Test", selftext="Content", score=10, num_comments=5,
            upvote_ratio=0.8, flair="YOLO", created=datetime.now(), url="http://x.com",
        )
        prompt = agent.user_prompt([post])
        assert "AMD: bearish" in prompt
