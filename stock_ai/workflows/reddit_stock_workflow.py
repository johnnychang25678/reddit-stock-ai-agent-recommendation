from stock_ai.agents.reddit_agents.reddit_base_agent import RedditBaseAgent
from stock_ai.agents.stock_plan_agents.data_classes import FinalRecommendation
from stock_ai.agents.stock_plan_agents.stock_picker_agent import StockPickerAgent
from stock_ai.reddit.types import RedditPost
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from stock_ai.agents.reddit_agents.data_classes import StockRecommendation
from stock_ai.agents.reddit_agents.news_agent import NewsAgent
from stock_ai.agents.reddit_agents.dd_agent import DDAgent
from stock_ai.agents.reddit_agents.yolo_agent import YoloAgent
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.workflow_base import StepFn, StepFns, StepFnFactory, StepFnFactories, Step, Workflow
from stock_ai.notifiers.discord.reddit_stock_notifier import send_stock_recommendations_to_discord
from stock_ai.workflows.common.api_clients import get_openai_client, get_reddit_scraper

from dataclasses import asdict
from sqlalchemy import text, bindparam

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
        agent.evaluate(recs, actual_reddit_post_url=p.url)

        rows = []
        for r in recs.recommendations:
            print(r.ticker, r.decision)
            if r.decision == "BUY":
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

def _make_picker_step_fn(stock_recommendations: list[StockRecommendation]) -> list[StepFn]:
    openai = get_openai_client()
    stock_picker_agent = StockPickerAgent(openai)
    def step_fn(persistence: SqlAlchemyPersistence, run_id: str) -> None:
        final_recs = stock_picker_agent.act(stock_recommendations)
        tickers = final_recs.tickers
        valid_tickers = [rec.ticker for rec in stock_recommendations]
        retry = 0
        while retry < 2 and not stock_picker_agent.evaluate(tickers, valid_tickers=valid_tickers):
            print(f"[retry] Attempt {retry + 1}")
            final_recs = stock_picker_agent.act(stock_recommendations)
            tickers = final_recs.tickers
            retry += 1
        text_clause = text(
            "SELECT * FROM news_recommendations WHERE run_id = :run_id AND ticker IN :ticker UNION ALL " \
            "SELECT * FROM dd_recommendations WHERE run_id = :run_id AND ticker IN :ticker UNION ALL " \
            "SELECT * FROM yolo_recommendations WHERE run_id = :run_id AND ticker IN :ticker"
        ).bindparams(bindparam("ticker", expanding=True))
        rec_rows =persistence.query(text_clause, {"run_id": run_id, "ticker": tickers})
        final_rows = []
        for rec_row in rec_rows:
            row = {
                "run_id": rec_row.run_id,
                "ticker": rec_row.ticker,
                "reason": rec_row.reason,
                "confidence": rec_row.confidence,
                "reddit_post_url": rec_row.reddit_post_url,
            }
            final_rows.append(row)

        persistence.set("final_recommendations", final_rows)
    return [step_fn]

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

def a_picker_factory(persistence: SqlAlchemyPersistence, run_id: str) -> list[StepFn]:
    if _idempotency_check(persistence, run_id, "final_recommendations"):
        print(f"Final recommendations already generated for run_id {run_id}, skipping Picker agent step")
        return []
    text_clause = text(
        "SELECT * FROM news_recommendations WHERE run_id = :run_id UNION ALL " \
        "SELECT * FROM dd_recommendations WHERE run_id = :run_id UNION ALL " \
        "SELECT * FROM yolo_recommendations WHERE run_id = :run_id"
    )
    stock_recommendations = persistence.query(text_clause, {"run_id": run_id})
    list_dc = []
    for sr in stock_recommendations:
        sr_dc = StockRecommendation(
            ticker=sr.ticker,
            reason=sr.reason,
            confidence=sr.confidence,
            reddit_post_url=sr.reddit_post_url,
        )
        list_dc.append(sr_dc)

    step_fns = _make_picker_step_fn(list_dc)

    return step_fns

def s_notify_discord(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    frs = persistence.get("final_recommendations", run_id=run_id)
    final_recs: list[dict] = []
    for fr in frs:
        fr_dc = FinalRecommendation.from_orm(fr)
        final_recs.append(asdict(fr_dc))
    send_stock_recommendations_to_discord(final_recs)

# factories to generate dataclasses for Step. Use dataclass because it's easier to use isinstance() in base workflow.
def step_fn_dc_factory(funcs: list[StepFn]) -> StepFns:
    return StepFns(functions=funcs)

def step_fn_factory_dc_factory(factories: list[StepFnFactory]) -> StepFnFactories:
    return StepFnFactories(factories=factories)

def init_workflow(run_id: str, persistence: SqlAlchemyPersistence) -> Workflow:
    reddit_stock_workflow = Workflow(
        run_id=run_id,
        persistence=persistence,
        steps=[
            Step("insert run metadata", step_fn_dc_factory([s_insert_run_metadata])),
            Step("scrape reddit", step_fn_dc_factory([s_scrape])),
            Step("filter posts", step_fn_dc_factory([s_filter])),
            Step("run stock agents", step_fn_factory_dc_factory([a_news_factory, a_dd_factory, a_yolo_factory])),
            Step("run stock picker agent", step_fn_factory_dc_factory([a_picker_factory])),
            Step("merge and notify discord", step_fn_dc_factory([s_notify_discord])),
        ]
    )
    return reddit_stock_workflow
