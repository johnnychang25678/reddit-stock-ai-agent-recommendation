from enum import Enum

class RunIdType(Enum):
    REDDIT_STOCK_RECOMMENDATION = "reddit_stock_recommendation"
    REDDIT_STOCK_TRADE = "reddit_stock_trade"
    DAILY_PERF = "daily_perf"
    TEST_RUN = "test_run"
    TEST_RUN_TRADE = "test_run_trade"
    TEST_DAILY_PERF = "test_daily_perf"


def run_id_generator(run_id_type: RunIdType, timestamp_str: str) -> str:
    return f"{run_id_type.value}_{timestamp_str}"
