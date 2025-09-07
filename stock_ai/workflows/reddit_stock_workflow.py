import os
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


reddit_stock_workflow = Workflow(steps=[
    Step("init_openai", [s_openai]),
    Step("scrape reddit", [s_scrape]),
    Step("filter posts", [s_filter]),
    Step("run reddit agents", [a_news, a_dd, a_yolo]),
    Step("merge all recommendations", [s_merge]),
    Step("fetch yf snapshots", [s_snapshots]),
    Step("run planner agent", [a_plan]),
])
