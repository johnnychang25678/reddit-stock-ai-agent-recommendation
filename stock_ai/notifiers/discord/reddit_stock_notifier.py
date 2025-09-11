
from stock_ai.notifiers.discord.discord_client import DiscordClient
from stock_ai.notifiers.discord.embed_builder import build_embed
import time
import os
from textwrap import dedent

def send_stock_recommendations_to_discord(rec: dict):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL_TEST", "")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL_TEST not set, skipping Discord notification")
        return
    discord_client = DiscordClient(webhook_url)
    week_str = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7*24*3600))
    content = dedent(f"""
    ## Stock AI Recommendations for week of {week_str}

    ### Methodology:
    1. Scrape recent posts from r/wallstreetbets with flairs: News, DD, YOLO.
    2. Filter posts by upvotes and engagement to retain high-quality content.
    3. Use AI agents to analyze posts by flair:
       - News Agent: Extracts stock mentions and sentiment from news posts.
       - DD Agent: Provides high-conviction buy ideas from due diligence posts.
       - YOLO Agent: Identifies speculative, high-risk/reward ideas from YOLO posts.
    4. Merge and deduplicate recommendations from all agents.
    5. Fetch latest stock data and technical indicators for recommended tickers.
    6. Use a Portfolio Planner Agent to create trading plans with entry, stop, targets, and risk/reward.
    7. Compile final recommendations with analysis, snapshot, and trading strategy.

    ### Legend for Trading Strategy fields:
    - Entry: The price at which the trader enters the position.
    - Stop: The price at which the trader will exit the position to prevent further losses.
    - Targets: The prices at which the trader plans to take profits.
    - Horizon: The time frame for the trade.
    - R/R: The risk-to-reward ratio of the trade (e.g., 1.5 means potential reward is 1.5× the risk).
    """).strip()

    discord_client.send_message(content)
    for ticker, info in rec.items():
        embed = build_embed(ticker, info)
        discord_client.send_embed(embed)
        time.sleep(0.5)
    