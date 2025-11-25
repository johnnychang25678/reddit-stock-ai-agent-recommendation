"""Main entry point for the weekly trade workflow."""

from dotenv import load_dotenv
import time
from datetime import date

from stock_ai.db.models import (
    RunMetaData, FinalRecommendation,
    Portfolio, Position, Trade, PerformanceSnapshot, TradeInput
)
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.weekly_trade_workflow import init_workflow
from stock_ai.db.session import init_db
from stock_ai.workflows.run_id_generator import RunIdType


def main():
    """Run the weekly trade workflow."""
    s = time.perf_counter()
    init_db()
    
    persistence = SqlAlchemyPersistence(
        registry={
            "run_metadata": RunMetaData,
            "final_recommendations": FinalRecommendation,
            "portfolios": Portfolio,
            "positions": Position,
            "trades": Trade,
            "performance_snapshots": PerformanceSnapshot,
            "trade_inputs": TradeInput,
        },
    )
    
    # Generate run_id for trade workflow
    # Format: REDDIT_STOCK_TRADE_YYYYMMDD
    # run_id = RunIdType.REDDIT_STOCK_TRADE.value + "_" + date.today().strftime("%Y%m%d")
    run_id = RunIdType.TEST_RUN_TRADE.value + "_" + "20251124-1"
    
    print(f"Starting weekly trade workflow with run_id: {run_id}")
    init_workflow(run_id, persistence).run()
    
    e = time.perf_counter()
    print(f"Trade workflow completed in {e - s:.2f} seconds.")


if __name__ == "__main__":
    load_dotenv()
    main()
