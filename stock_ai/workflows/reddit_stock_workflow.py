from dataclasses import asdict
from stock_ai.agents.stock_plan_agents.data_classes import TradePlan
from stock_ai.reddit.types import RedditPost
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from stock_ai.agents.reddit_agents.data_classes import StockRecommendation
from stock_ai.agents.reddit_agents.news_agent import NewsAgent
from stock_ai.agents.reddit_agents.dd_agent import DDAgent
from stock_ai.agents.reddit_agents.yolo_agent import YoloAgent
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.yahoo_finance.types import StockSnapshot
from stock_ai.yahoo_finance.yahoo_finance_client import YahooFinanceClient
from stock_ai.agents.stock_plan_agents.portfolio_planner_agent import PortfolioPlannerAgent
from stock_ai.workflows.workflow_base import Workflow, Step
from stock_ai.workflows.persistence.base_persistence import Persistence
from stock_ai.notifiers.discord.reddit_stock_notifier import send_stock_recommendations_to_discord
from stock_ai.workflows.common.api_clients import get_openai_client, get_reddit_scraper

from sqlalchemy.inspection import inspect


def _idempotency_check(persistence: SqlAlchemyPersistence, run_id: str, table: str) -> bool:
    def row_to_dict(row):
        """Convert a SQLAlchemy ORM row to dict (columns only)."""
        return {c.key: getattr(row, c.key) for c in inspect(row).mapper.column_attrs}

    if run_id.startswith("no-idempotency-"):
        # disable idempotency check
        print("skip idempotency check...")
        return False
    print(f"Checking if {table} already exists for run_id {run_id}...")
    existing = persistence.get(table, {"run_id": run_id})
    if isinstance(existing, list):
        for row in existing:
            print(row_to_dict(row))
    # will return a list of rows if any exist with this run_id
    return (existing is not None) and (isinstance(existing, list) and len(existing) > 0)

def s_insert_run_metadata(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "run_metadata"):
        print(f"Run metadata already exists for run_id {run_id}, skipping insert step")
        return
    row = {
        "run_id": run_id,
    }
    persistence.set("run_metadata", [row])

def s_scrape(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "reddit_posts"):
        print(f"Posts already scraped for run_id {run_id}, skipping scrape step")
        return

    reddit_scraper = get_reddit_scraper()
    flairs_want = {"News", "DD", "YOLO"}
    subreddit_name = "wallstreetbets"
    cut_off_days = 7

    posts = reddit_scraper.scrape(
        subreddit_name, flairs_want, 
        skip_empty_selftext=True, cut_off_days=cut_off_days)

    # RedditPost model to dict rows
    rows = []
    for _, plist in posts.items():
        for p in plist:
            d = asdict(p)
            d["run_id"] = run_id
            rows.append(d)

    persistence.set("reddit_posts", rows)

def s_filter(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "reddit_filtered_posts"):
        print(f"Posts already filtered for run_id {run_id}, skipping filter step")
        return

    posts = persistence.get("reddit_posts", {"run_id": run_id})
    # convert to list[RedditPostORMModel] to dict flair -> list[RedditPost]
    posts_dict:dict[str, list] = {}
    for p in posts:
        flair = p.flair
        reddit_post = RedditPost.from_orm(p)
        if flair not in posts_dict:
            posts_dict[flair] = []
        posts_dict[flair].append(reddit_post)
    filtered = AfterScrapeFilter()(posts_dict)
    rows = []
    for _, plist in filtered.items():
        for p in plist:
            d = asdict(p)
            d["run_id"] = run_id
            rows.append(d)

    persistence.set("reddit_filtered_posts", rows)

def _filter_posts_by_flair(posts: list, flair: str) -> list[RedditPost]:
    # filtered out flair = flair
    posts_for_agent = []
    for p in posts:
        reddit_post = RedditPost.from_orm(p)
        if reddit_post.flair == flair:
            posts_for_agent.append(reddit_post)
    return posts_for_agent


def a_news(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "news_recommendations"):
        print(f"News recommendations already generated for run_id {run_id}, skipping news agent step")
        return
    openai = get_openai_client()
    agent = NewsAgent(openai)
    filtered_posts = persistence.get("reddit_filtered_posts", {"run_id": run_id})
    # filtered out flair = flair
    posts_for_agent = _filter_posts_by_flair(filtered_posts, "News")
    recs = agent.act(posts_for_agent)

    rows = []
    for r in recs.recommendations:
        stock_rec_dc = StockRecommendation.from_pydantic(r)
        d = asdict(stock_rec_dc)
        d["run_id"] = run_id
        rows.append(d)

    persistence.set("news_recommendations", rows)

def a_dd(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "dd_recommendations"):
        print(f"DD recommendations already generated for run_id {run_id}, skipping DD agent step")
        return
    openai = get_openai_client()
    agent = DDAgent(openai)
    filtered_posts = persistence.get("reddit_filtered_posts", {"run_id": run_id})
    posts_for_agent = _filter_posts_by_flair(filtered_posts, "DD")

    recs = agent.act(posts_for_agent)

    rows = []
    for r in recs.recommendations:
        stock_rec_dc = StockRecommendation.from_pydantic(r)
        d = asdict(stock_rec_dc)
        d["run_id"] = run_id
        rows.append(d)

    persistence.set("dd_recommendations", rows)

def a_yolo(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "yolo_recommendations"):
        print(f"YOLO recommendations already generated for run_id {run_id}, skipping YOLO agent step")
        return
    openai = get_openai_client()
    agent = YoloAgent(openai)
    filtered_posts = persistence.get("reddit_filtered_posts", {"run_id": run_id})
    posts_for_agent = _filter_posts_by_flair(filtered_posts, "YOLO")

    recs = agent.act(posts_for_agent)

    rows = []
    for r in recs.recommendations:
        stock_rec_dc = StockRecommendation.from_pydantic(r)
        d = asdict(stock_rec_dc)
        d["run_id"] = run_id
        rows.append(d)

    persistence.set("yolo_recommendations", rows)

def s_snapshots(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "financial_snapshots"):
        print(f"Snapshots already fetched for run_id {run_id}, skipping financial snapshots step")
        return
    yf = YahooFinanceClient()
    news_recs = persistence.get("news_recommendations", {"run_id": run_id})
    dd_recs = persistence.get("dd_recommendations", {"run_id": run_id})
    yolo_recs = persistence.get("yolo_recommendations", {"run_id": run_id})
    tickers = set()
    for rec in news_recs + dd_recs + yolo_recs:
        tickers.add(rec.ticker)
    print(f"Fetching snapshots for tickers: {tickers}")
    snaps = [yf.get_yf_snapshot(t) for t in tickers]
    rows = []
    for s in snaps:
        d = asdict(s)
        d["run_id"] = run_id
        del d["error"] # delete error field before saving to DB
        print(d)
        rows.append(d)

    persistence.set("financial_snapshots", rows)

def a_plan(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "portfolio_plans"):
        print(f"Portfolio already planned for run_id {run_id}, skipping planner step")
        return
    openai = get_openai_client()
    planner = PortfolioPlannerAgent(openai)
    snapshots = persistence.get("financial_snapshots", {"run_id": run_id})
    snapshots_dc = [StockSnapshot.from_orm(s) for s in snapshots]
    portfolio = planner.act(snapshots_dc)

    trade_plans = portfolio.plans # pydantic
    rows = []
    for tp in trade_plans:
        tp_dc = TradePlan.from_pydantic(tp)
        d = asdict(tp_dc)
        d["run_id"] = run_id
        rows.append(d)

    persistence.set("portfolio_plans", rows)

def s_merge_and_notify_discord(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    print("************ Final merge step ************")
    # combine everything into final recommendations by ticker
    final_recs = {}
    portfolio_plans = persistence.get("portfolio_plans", {"run_id": run_id})

    snapshots = persistence.get("financial_snapshots", {"run_id": run_id})
    snapshot_dc_dict = {}
    for s in snapshots:
        snapshot_dc = StockSnapshot.from_orm(s)
        snapshot_dc_dict[snapshot_dc.ticker] = snapshot_dc

    news_recs = persistence.get("news_recommendations", {"run_id": run_id})
    recs_dc_dict = {}
    for n in news_recs:
        n_dc = StockRecommendation.from_orm(n)
        recs_dc_dict[n_dc.ticker] = n_dc

    dd_recs = persistence.get("dd_recommendations", {"run_id": run_id})
    for d in dd_recs:
        d_dc = StockRecommendation.from_orm(d)
        recs_dc_dict[d_dc.ticker] = d_dc

    yolo_recs = persistence.get("yolo_recommendations", {"run_id": run_id})
    for y in yolo_recs:
        y_dc = StockRecommendation.from_orm(y)
        recs_dc_dict[y_dc.ticker] = y_dc

    for p in portfolio_plans:
        print(p.ticker)
        ticker = p.ticker
        if ticker not in final_recs:
            final_recs[ticker] = {
                "portfolio": asdict(TradePlan.from_orm(p)),
                "snapshot": asdict(snapshot_dc_dict[ticker]) if ticker in snapshot_dc_dict else None,
                "stock_recommendations": asdict(recs_dc_dict[ticker]) if ticker in recs_dc_dict else None,
            }

    print(final_recs)
    # send to discord
    send_stock_recommendations_to_discord(final_recs)

def init_workflow(run_id: str, persistence: SqlAlchemyPersistence) -> Workflow:
    reddit_stock_workflow = Workflow(
        run_id=run_id,
        persistence=persistence,
        steps=[
            Step("insert run metadata", [s_insert_run_metadata]),
            Step("scrape reddit", [s_scrape]),
            Step("filter posts", [s_filter]),
            Step("run reddit agents", [a_news, a_dd, a_yolo]),
            Step("fetch yf snapshots", [s_snapshots]),
            Step("run planner agent", [a_plan]),
            Step("merge and notify discord", [s_merge_and_notify_discord]),
        ]
    )
    return reddit_stock_workflow
