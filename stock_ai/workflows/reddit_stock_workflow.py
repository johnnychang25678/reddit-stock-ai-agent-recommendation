from dataclasses import asdict
from stock_ai.agents.reddit_agents.reddit_base_agent import RedditBaseAgent
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
from stock_ai.workflows.workflow_base import Workflow, Step, StepFn
from stock_ai.workflows.persistence.base_persistence import Persistence
from stock_ai.notifiers.discord.reddit_stock_notifier import send_stock_recommendations_to_discord
from stock_ai.workflows.common.api_clients import get_openai_client, get_reddit_scraper


def _idempotency_check(persistence: SqlAlchemyPersistence, run_id: str, table: str) -> bool:
    if run_id.startswith("no-idempotency-"):
        # disable idempotency check
        print("skip idempotency check...")
        return False
    print(f"Checking if {table} already exists for run_id {run_id}...")
    existing = persistence.get(table, run_id=run_id)
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

    posts = persistence.get("reddit_posts", run_id=run_id)
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

# -------- Some factory functions to generate step functions for each Reddit post --------
# need this to resolve late binding closure issue
def _make_stock_step_fn(agent_type: str, agent:RedditBaseAgent, p: RedditPost) -> StepFn:
    def step_fn(persistence: SqlAlchemyPersistence, run_id: str) -> None:
        recs = agent.act([p])

        rows = []
        for r in recs.recommendations:
            stock_rec_dc = StockRecommendation.from_pydantic(r)
            d = asdict(stock_rec_dc)
            d["run_id"] = run_id
            rows.append(d)

        persistence.set(f"{agent_type.lower()}_recommendations", rows)
    return step_fn


def _generate_stock_agent_step_functions(agent_type: str, reddit_posts: list[RedditPost]) -> list[StepFn]:
    """ Generate step functions for each Reddit post for the given agent type. """
    openai = get_openai_client()
    if agent_type == "News":
        agent = NewsAgent(openai)
    elif agent_type == "DD":
        agent = DDAgent(openai)
    elif agent_type == "YOLO":
        agent = YoloAgent(openai)
    step_fns = []
    for p in reddit_posts:
        step_fn = _make_stock_step_fn(agent_type, agent, p)
        step_fns.append(step_fn)

    return step_fns

def _make_planner_step_fn(planner: PortfolioPlannerAgent, s: StockSnapshot) -> StepFn:
    def step_fn(persistence: SqlAlchemyPersistence, run_id: str) -> None:
        portfolio = planner.act([s])

        trade_plans = portfolio.plans # pydantic
        rows = []
        for tp in trade_plans:
            tp_dc = TradePlan.from_pydantic(tp)
            d = asdict(tp_dc)
            d["run_id"] = run_id
            rows.append(d)

        persistence.set("portfolio_plans", rows)
    return step_fn

def _generate_planner_step_functions(snapshots: list[StockSnapshot]) -> list[StepFn]:
    """ Generate step functions for each StockSnapshot for the planner agent. """
    openai = get_openai_client()
    planner = PortfolioPlannerAgent(openai)
    step_fns = []
    for s in snapshots:
        step_fn = _make_planner_step_fn(planner, s)
        step_fns.append(step_fn)

    return step_fns

#-------- End of factory functions --------

def a_news_factory(persistence: SqlAlchemyPersistence, run_id: str) -> list[StepFn]:
    if _idempotency_check(persistence, run_id, "news_recommendations"):
        print(f"News recommendations already generated for run_id {run_id}, skipping news agent step")
        return []
    flair = "News"
    filtered_posts = persistence.get("reddit_filtered_posts", run_id=run_id, flair=flair)
    step_fns = _generate_stock_agent_step_functions(flair, filtered_posts)

    return step_fns

def a_dd_factory(persistence: SqlAlchemyPersistence, run_id: str) -> list[StepFn]:
    if _idempotency_check(persistence, run_id, "dd_recommendations"):
        print(f"DD recommendations already generated for run_id {run_id}, skipping DD agent step")
        return []
    flair = "DD"
    filtered_posts = persistence.get("reddit_filtered_posts", run_id=run_id, flair=flair)
    step_fns = _generate_stock_agent_step_functions(flair, filtered_posts)

    return step_fns

def a_yolo_factory(persistence: SqlAlchemyPersistence, run_id: str) -> list[StepFn]:
    if _idempotency_check(persistence, run_id, "yolo_recommendations"):
        print(f"YOLO recommendations already generated for run_id {run_id}, skipping YOLO agent step")
        return []
    flair = "YOLO"
    filtered_posts = persistence.get("reddit_filtered_posts", run_id=run_id, flair=flair)
    step_fns = _generate_stock_agent_step_functions(flair, filtered_posts)

    return step_fns

def s_snapshots(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    if _idempotency_check(persistence, run_id, "financial_snapshots"):
        print(f"Snapshots already fetched for run_id {run_id}, skipping financial snapshots step")
        return
    yf = YahooFinanceClient()
    news_recs = persistence.get("news_recommendations", run_id=run_id)
    dd_recs = persistence.get("dd_recommendations", run_id=run_id)
    yolo_recs = persistence.get("yolo_recommendations", run_id=run_id)
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
        rows.append(d)

    persistence.set("financial_snapshots", rows)

def a_plan_factory(persistence: SqlAlchemyPersistence, run_id: str) -> list[StepFn]:
    if _idempotency_check(persistence, run_id, "portfolio_plans"):
        print(f"Portfolio already planned for run_id {run_id}, skipping planner step")
        return []
    snapshots = persistence.get("financial_snapshots", run_id=run_id)
    snapshots_dc = [StockSnapshot.from_orm(s) for s in snapshots]
    step_fns = _generate_planner_step_functions(snapshots_dc)
    return step_fns

def s_merge_and_notify_discord(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    print("************ Final merge step ************")
    # combine everything into final recommendations by ticker
    final_recs = {}
    portfolio_plans = persistence.get("portfolio_plans", run_id=run_id)

    snapshots = persistence.get("financial_snapshots", run_id=run_id)
    snapshot_dc_dict = {}
    for s in snapshots:
        snapshot_dc = StockSnapshot.from_orm(s)
        snapshot_dc_dict[snapshot_dc.ticker] = snapshot_dc

    news_recs = persistence.get("news_recommendations", run_id=run_id)
    recs_dc_dict = {}
    for n in news_recs:
        n_dc = StockRecommendation.from_orm(n)
        recs_dc_dict[n_dc.ticker] = n_dc

    dd_recs = persistence.get("dd_recommendations", run_id=run_id)
    for d in dd_recs:
        d_dc = StockRecommendation.from_orm(d)
        recs_dc_dict[d_dc.ticker] = d_dc

    yolo_recs = persistence.get("yolo_recommendations", run_id=run_id)
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

    # print(final_recs)
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
            Step("run news agent", a_news_factory),
            Step("run dd agent", a_dd_factory),
            Step("run yolo agent", a_yolo_factory),
            Step("fetch yf snapshots", [s_snapshots]),
            Step("run planner agent", a_plan_factory),
            # Step("run planner agent", [a_plan]),
            Step("merge and notify discord", [s_merge_and_notify_discord]),
        ]
    )
    return reddit_stock_workflow
