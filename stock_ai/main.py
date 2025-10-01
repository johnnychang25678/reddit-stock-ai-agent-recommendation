from dotenv import load_dotenv
import time

from stock_ai.db.models import (
    RedditPost, RedditFilteredPost, DdRecommendation, YoloRecommendation, RunMetaData,
    NewsRecommendation, FinancialSnapshot, PortfolioPlan)
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.reddit_stock_workflow import init_workflow
from stock_ai.db.session import init_db

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
        },
    )
    run_id = "my_run_id"
    init_workflow(run_id, persistence).run()
    e = time.perf_counter()
    print(f"Workflow completed in {e - s:.2f} seconds.")


if __name__ == "__main__":
    load_dotenv()
    main()
