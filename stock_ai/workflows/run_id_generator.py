from enum import Enum

class RunIdType(Enum):
    REDDIT_STOCK_RECOMMENDATION = "reddit_stock_recommendation"
    REDDIT_STOCK_TRADE = "reddit_stock_trade"
    TEST_RUN = "test_run"
    TEST_RUN_TRADE = "test_run_trade"


def run_id_generator(run_id_type: RunIdType, timestamp_str: str) -> str:
    return f"{run_id_type.value}_{timestamp_str}"
