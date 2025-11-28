import os
from dotenv import load_dotenv
import time
from datetime import date, timedelta

from stock_ai.db.models import (
    RedditPost, RedditFilteredPost, DdRecommendation, YoloRecommendation, RunMetaData,
    NewsRecommendation, FinancialSnapshot, PortfolioPlan, FinalRecommendation)
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.reddit_stock_workflow import init_workflow
from stock_ai.db.session import init_db
from stock_ai.workflows.run_id_generator import RunIdType

def main():
    s = time.perf_counter()
    init_db()
    persistence = SqlAlchemyPersistence(
        registry={
            "run_metadata": RunMetaData,
            "reddit_posts": RedditPost,
            "reddit_filtered_posts": RedditFilteredPost,
            "news_recommendations": NewsRecommendation,
            "dd_recommendations": DdRecommendation,
            "yolo_recommendations": YoloRecommendation,
            "financial_snapshots": FinancialSnapshot,
            "portfolio_plans": PortfolioPlan,
            "final_recommendations": FinalRecommendation
        },
    )
    is_test_env = os.getenv("ENVIRONMENT") == "TEST" 

    # use sunday + 1 day (Monday) so the trade workflow is easier to fetch the id
    # e.g., 20251123 is Sunday, so this becomes 20251124 (Monday)
    today_plus_one = (date.today() + timedelta(days=1)).strftime("%Y%m%d") 
    run_id = RunIdType.REDDIT_STOCK_RECOMMENDATION.value + "_" + today_plus_one
    # run_id = RunIdType.TEST_RUN_TRADE.value + "_" + "20251126-1"
    if is_test_env:
        run_id = os.getenv("TEST_RUN_ID", run_id)

    init_workflow(run_id, persistence).run()
    e = time.perf_counter()
    print(f"Workflow completed in {e - s:.2f} seconds.")


if __name__ == "__main__":
    load_dotenv()
    main()
