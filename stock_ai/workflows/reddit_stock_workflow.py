import os, time, json
from openai import OpenAI
from stock_ai.reddit.reddit_scraper import RedditScraper
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from stock_ai.agents.reddit_agents.pydantic_models import StockRecommendations
from stock_ai.agents.reddit_agents.news_agent import NewsAgent
from stock_ai.agents.reddit_agents.dd_agent import DDAgent
from stock_ai.agents.reddit_agents.yolo_agent import YoloAgent
from stock_ai.yahoo_finance.yahoo_finance_client import YahooFinanceClient
from stock_ai.agents.stock_plan_agents.portfolio_planner_agent import PortfolioPlannerAgent
from stock_ai.workflows.workflow_base import Workflow, Step, Context
from stock_ai.notifiers.discord.discord_client import DiscordClient
from stock_ai.notifiers.discord.embed_builder import build_embed


def s_openai(ctx: Context) -> Context:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return {"openai": client}

def s_scrape(ctx: Context) -> Context:
    reddit_scraper = RedditScraper(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )
    flairs_want = {"News", "DD", "YOLO"}
    subreddit_name = "wallstreetbets"
    cut_off_days = 7

    posts = reddit_scraper.scrape(
        subreddit_name, flairs_want, 
        skip_empty_selftext=True, cut_off_days=cut_off_days)

    return {"posts": posts}

def s_filter(ctx: Context) -> Context:
    filtered = AfterScrapeFilter()(ctx["posts"])
    return {"filtered": filtered}

def a_news(ctx: Context) -> Context:
    agent = NewsAgent(ctx["openai"])
    recs = agent.act(ctx["filtered"].get("News", []))
    return {"news_recs": recs}

def a_dd(ctx: Context) -> Context:
    agent = DDAgent(ctx["openai"])
    recs = agent.act(ctx["filtered"].get("DD", []))
    return {"dd_recs": recs}

def a_yolo(ctx: Context) -> Context:
    agent = YoloAgent(ctx["openai"])
    recs = agent.act(ctx["filtered"].get("YOLO", []))
    return {"yolo_recs": recs}

def s_merge(ctx: Context) -> Context:
    news_recs: StockRecommendations = ctx.get("news_recs")
    dd_recs: StockRecommendations = ctx.get("dd_recs")
    yolo_recs: StockRecommendations = ctx.get("yolo_recs")
    merged: dict[str, StockRecommendations] = {}
    for recs in [news_recs, dd_recs, yolo_recs]:
        if recs:
            for rec in recs.recommendations:
                # here we just take the latest recommendation for each ticker if there are duplicates
                merged[rec.ticker] = rec

    tickers = list(merged.keys())
    return {"merged_recs": merged, "tickers": tickers}

def s_snapshots(ctx: Context) -> Context:
    yf = YahooFinanceClient()
    snaps = [yf.get_yf_snapshot(t) for t in ctx["tickers"]]
    return {"snapshots": snaps}

def a_plan(ctx: Context) -> Context:
    planner = PortfolioPlannerAgent(ctx["openai"])
    portfolio = planner.act(ctx["snapshots"])
    return {"portfolio": portfolio}

def s_final_merge(ctx: Context) -> Context:
    # combine everything into final recommendations by ticker
    final_recs = {}
    for ticker in ctx["tickers"]:
        snapshot = [s for s in ctx["snapshots"] if s.ticker == ticker]
        if snapshot and snapshot[0].error:
            continue
        final_recs[ticker] = {
            "stock_recommendations": ctx["merged_recs"].get(ticker).model_dump_json() 
            if ctx["merged_recs"].get(ticker) else None,
            "snapshot": snapshot[0].__dict__ if snapshot else None,
            "portfolio": [p.model_dump_json() for p in ctx["portfolio"].plans if p.ticker == ticker],
        }
        # write for debug
        os.makedirs("debug", exist_ok=True)
        os.makedirs("debug/result", exist_ok=True)
        with open(f"debug/result/final_recommendations_{int(time.time())}.json","w",encoding="utf-8") as f:
            json.dump(final_recs, f, ensure_ascii=False, indent=2)

    return {"final_recommendations": final_recs}

def s_send_to_discord(ctx: Context) -> Context:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL_TEST")
    discord_client = DiscordClient(webhook_url)
    
    week_str = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7*24*3600))
    discord_client.send_message(
        f"""
        ## Stock AI Recommendations for week of {week_str}

        ### Legend for Trading Strategy fields:

    - Entry: The price at which the trader enters the position.
    - Stop: The price at which the trader will exit the position to prevent further losses.
    - Targets: The prices at which the trader plans to take profits.
    - Horizon: The time frame for the trade.
    - R/R: The risk-to-reward ratio of the trade. (e.g., 1.5 means potential reward is 1.5 times the risk taken)
    """
    )

    for ticker, info in ctx["final_recommendations"].items():
        embed = build_embed(ticker, info)
        discord_client.send_embed(embed)
        time.sleep(0.5)
    
    return {}


reddit_stock_workflow = Workflow(steps=[
    Step("init_openai", [s_openai]),
    Step("scrape reddit", [s_scrape]),
    Step("filter posts", [s_filter]),
    Step("run reddit agents", [a_news, a_dd, a_yolo]),
    Step("merge all recommendations", [s_merge]),
    Step("fetch yf snapshots", [s_snapshots]),
    Step("run planner agent", [a_plan]),
    Step("final merge", [s_final_merge]),
    Step("send to discord", [s_send_to_discord]),
])
