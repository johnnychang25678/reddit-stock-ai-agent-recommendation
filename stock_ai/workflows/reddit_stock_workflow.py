import os, time, json
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from stock_ai.agents.reddit_agents.pydantic_models import StockRecommendations, StockRecommendation
from stock_ai.agents.reddit_agents.news_agent import NewsAgent
from stock_ai.agents.reddit_agents.dd_agent import DDAgent
from stock_ai.agents.reddit_agents.yolo_agent import YoloAgent
from stock_ai.yahoo_finance.yahoo_finance_client import YahooFinanceClient
from stock_ai.agents.stock_plan_agents.portfolio_planner_agent import PortfolioPlannerAgent
from stock_ai.workflows.workflow_base import Workflow, Step
from stock_ai.workflows.persistence.base_persistence import Persistence
from stock_ai.notifiers.discord.reddit_stock_notifier import send_stock_recommendations_to_discord
from stock_ai.workflows.common.api_clients import get_openai_client, get_reddit_scraper
from stock_ai.workflows.persistence.in_memory import InMemoryPersistence


def _idempotency_check(persistence: Persistence, run_id: str, key: str) -> bool:
    if run_id.startswith("no-idempotency-"):
        # disable idempotency check
        return False
    existing = persistence.get(key)
    return existing is not None and existing.get("run_id") == run_id

def s_scrape(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "posts"):
        print(f"Posts already scraped for run_id {run_id}, skipping scrape step")
        return

    reddit_scraper = get_reddit_scraper()
    flairs_want = {"News", "DD", "YOLO"}
    subreddit_name = "wallstreetbets"
    cut_off_days = 7

    posts = reddit_scraper.scrape(
        subreddit_name, flairs_want, 
        skip_empty_selftext=True, cut_off_days=cut_off_days)

    val = {"run_id": run_id, "posts": posts}
    persistence.set("posts", val)

def s_filter(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "filtered"):
        print(f"Posts already filtered for run_id {run_id}, skipping filter step")
        return
    posts = persistence.get("posts")
    filtered = AfterScrapeFilter()(posts.get("posts", []))
    val = {"run_id": run_id, "filtered": filtered}
    persistence.set("filtered", val)

def a_news(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "news_recs"):
        print(f"News recommendations already generated for run_id {run_id}, skipping news step")
        return
    print("keys", persistence)
    openai = get_openai_client()
    agent = NewsAgent(openai)
    filtered = persistence.get("filtered", {}).get("filtered", {})
    recs = agent.act(filtered.get("News", []))
    val = {"run_id": run_id, "news_recs": recs}
    persistence.set("news_recs", val)

def a_dd(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "dd_recs"):
        print(f"DD recommendations already generated for run_id {run_id}, skipping DD step")
        return
    openai = get_openai_client()
    agent = DDAgent(openai)
    filtered = persistence.get("filtered", {}).get("filtered", {})
    recs = agent.act(filtered.get("DD", []))
    val = {"run_id": run_id, "dd_recs": recs}
    persistence.set("dd_recs", val)

def a_yolo(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "yolo_recs"):
        print(f"YOLO recommendations already generated for run_id {run_id}, skipping YOLO step")
        return
    openai = get_openai_client()
    agent = YoloAgent(openai)
    filtered = persistence.get("filtered", {}).get("filtered", {})
    recs = agent.act(filtered.get("YOLO", []))
    val = {"run_id": run_id, "yolo_recs": recs}
    persistence.set("yolo_recs", val)

def s_merge(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "merged_recs"):
        print(f"Recommendations already merged for run_id {run_id}, skipping merge step")
        return
    news_recs: StockRecommendations = persistence.get("news_recs", {}).get("news_recs")
    dd_recs: StockRecommendations = persistence.get("dd_recs", {}).get("dd_recs")
    yolo_recs: StockRecommendations = persistence.get("yolo_recs", {}).get("yolo_recs")
    merged: dict[str, StockRecommendation] = {}
    for recs in [news_recs, dd_recs, yolo_recs]:
        if recs:
            for rec in recs.recommendations:
                # here we just take the latest recommendation for each ticker if there are duplicates
                merged[rec.ticker] = rec

    tickers = list(merged.keys())
    val = {"run_id": run_id, "merged_recs": merged, "tickers": tickers}
    persistence.set("merged_recs", val)

def s_snapshots(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "snapshots"):
        print(f"Snapshots already fetched for run_id {run_id}, skipping snapshots step")
        return
    yf = YahooFinanceClient()
    tickers = persistence.get("merged_recs", {}).get("tickers", [])
    snaps = [yf.get_yf_snapshot(t) for t in tickers]
    val = {"run_id": run_id, "snapshots": snaps}
    persistence.set("snapshots", val)

def a_plan(persistence: Persistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "portfolio"):
        print(f"Portfolio already planned for run_id {run_id}, skipping planner step")
        return
    openai = get_openai_client()
    planner = PortfolioPlannerAgent(openai)
    snapshots = persistence.get("snapshots", {}).get("snapshots", [])
    portfolio = planner.act(snapshots)
    val = {"run_id": run_id, "portfolio": portfolio}
    persistence.set("portfolio", val)

def s_final_merge(persistence: Persistence, run_id: str) -> dict:
    print("************ Final merge step ************")
    if _idempotency_check(persistence, run_id, "final_recommendations"):
        print(f"Final recommendations already generated for run_id {run_id}, skipping final merge step")
        return persistence.get("final_recommendations")
    # combine everything into final recommendations by ticker
    final_recs = {}
    tickers = persistence.get("merged_recs", {}).get("tickers", [])
    print("tickers:", tickers)
    snapshots = persistence.get("snapshots", {}).get("snapshots", [])
    print("snapshots:", snapshots)
    merged_recs = persistence.get("merged_recs", {}).get("merged_recs", {})
    portfolio = persistence.get("portfolio", {}).get("portfolio", []) # TradePlans
    print("portfolio:", portfolio)
    for ticker in tickers:
        snapshot = [s for s in snapshots if s.ticker == ticker]
        if snapshot and snapshot[0].error:
            continue
        final_recs[ticker] = {
            "stock_recommendations": merged_recs.get(ticker).model_dump_json()
            if merged_recs.get(ticker) else None,
            "snapshot": snapshot[0].__dict__ if snapshot else None,
            "portfolio": [p.model_dump_json() for p in portfolio.plans if p.ticker == ticker],
        }
        # write for debug
        os.makedirs("debug", exist_ok=True)
        os.makedirs("debug/result", exist_ok=True)
        with open(f"debug/result/final_recommendations_{time.strftime('%Y%m%d')}_{int(time.time())}.json","w",encoding="utf-8") as f:
            json.dump(final_recs, f, ensure_ascii=False, indent=2)
    val = {"run_id": run_id, "final_recommendations": final_recs}
    persistence.set("final_recommendations", val)
    return {"final_recommendations": final_recs}

def s_send_to_discord(persistence: Persistence, run_id: str) -> None:
    recs = persistence.get("final_recommendations", {}).get("final_recommendations")
    send_stock_recommendations_to_discord(recs)

def init_workflow(run_id: str, persistence: Persistence) -> Workflow:
    reddit_stock_workflow = Workflow(
        run_id=run_id,
        persistence=persistence,
        steps=[
            Step("scrape reddit", [s_scrape]),
            Step("filter posts", [s_filter]),
            Step("run reddit agents", [a_news, a_dd, a_yolo]),
            Step("merge all recommendations", [s_merge]),
            Step("fetch yf snapshots", [s_snapshots]),
            Step("run planner agent", [a_plan]),
            Step("final merge", [s_final_merge]),
            Step("send to discord", [s_send_to_discord]),
        ]
    )
    return reddit_stock_workflow
