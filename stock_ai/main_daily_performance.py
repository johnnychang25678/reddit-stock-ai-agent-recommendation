"""Main entry point for the daily performance tracking workflow.

This workflow runs Tuesday-Friday to track portfolio performance.
Skips Monday since the weekly trade workflow runs on Monday.
"""

from dotenv import load_dotenv
import time
from datetime import date

from stock_ai.db.models import (
    RunMetaData, Portfolio, Position, PerformanceSnapshot
)
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.daily_performance_workflow import init_workflow
from stock_ai.db.session import init_db
from stock_ai.workflows.run_id_generator import RunIdType


def main():
    """Run the daily performance tracking workflow.
    
    Skips execution on Mondays when weekly trade workflow runs.
    """
    # Check if today is Monday (0 = Monday, 6 = Sunday)
    if date.today().weekday() == 0:
        print("Skipping daily performance workflow on Monday (weekly trade workflow runs today)")
        return
    
    s = time.perf_counter()
    init_db()
    
    persistence = SqlAlchemyPersistence(
        registry={
            "run_metadata": RunMetaData,
            "portfolios": Portfolio,
            "positions": Position,
            "performance_snapshots": PerformanceSnapshot,
        },
    )
    
    # run_id = RunIdType.DAILY_PERF.value + "_" + date.today().strftime("%Y%m%d")
    run_id = RunIdType.TEST_DAILY_PERF.value + "_" + "20251126-1"
    
    print(f"Starting daily performance workflow with run_id: {run_id}")
    init_workflow(run_id, persistence).run()
    
    e = time.perf_counter()
    print(f"Daily performance workflow completed in {e - s:.2f} seconds.")


if __name__ == "__main__":
    load_dotenv()
    main()
