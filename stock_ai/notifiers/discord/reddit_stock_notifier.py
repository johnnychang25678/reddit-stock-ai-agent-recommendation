
from stock_ai.notifiers.discord.discord_client import DiscordClient
from stock_ai.notifiers.discord.embed_builder import build_embed
import time
import os
from textwrap import dedent


def _format_rec_detail(rec: dict) -> str:
    """Format a single recommendation block for Discord Markdown.

    Expected keys in rec:
      - ticker: str
      - reason: str
      - confidence: str | None  # "high", "medium", "low"
      - reddit_post_url: str | None
    """
    ticker = rec.get("ticker") or "?"
    reason = (rec.get("reason") or "").strip()

    lines = [f"### {ticker}"]
    if reason:
        lines.append(f"- Rationale: {reason}")

    return "\n".join(lines)

def send_stock_recommendations_to_discord(recs: list[dict]):
    webhook_urls = os.getenv("DISCORD_WEBHOOK_URL_TEST", "")
    if not webhook_urls:
        print("DISCORD_WEBHOOK_URL_TEST not set, skipping Discord notification")
        return
    webhook_urls_list = [url.strip() for url in webhook_urls.split(",") if url.strip()]
    for url in webhook_urls_list:
        discord_client = DiscordClient(url)
        week_str = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7*24*3600))
        details = "\n".join(_format_rec_detail(rec) for rec in recs) if recs else "(No recommendations)"
        # Build without leading whitespace so Discord doesn't render as a code block
        header_line = f"## Reddit Stock AI Recommendations for week of {week_str}"
        tickers_line = ", ".join(rec["ticker"] for rec in recs)
        content = "\n".join([
            header_line,
            "",
            tickers_line,
            "### Details",
            details,
        ]).strip()

        discord_client.send_message(content)
    