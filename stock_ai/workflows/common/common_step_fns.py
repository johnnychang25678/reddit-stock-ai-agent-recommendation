"""Common step functions shared across workflows."""

from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.common.utils import idempotency_check


def s_insert_run_metadata(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Insert run metadata to track workflow execution.

    This is typically the first step in a workflow to record that a run has started.

    Args:
        persistence: Database persistence layer
        run_id: Unique workflow run identifier
    """
    if idempotency_check(persistence, run_id, "run_metadata"):
        print(f"Run metadata already exists for run_id {run_id}, skipping insert step")
        return
    row = {
        "run_id": run_id,
    }
    persistence.set("run_metadata", [row])
