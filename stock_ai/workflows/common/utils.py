"""Common utility functions for workflows."""

from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.workflow_base import StepFn, StepFns, StepFnFactory, StepFnFactories


def idempotency_check(persistence: SqlAlchemyPersistence, run_id: str, table: str) -> bool:
    """Check if data already exists for this run_id in the given table.

    Args:
        persistence: Database persistence layer
        run_id: Unique workflow run identifier
        table: Table name to check

    Returns:
        True if data exists, False otherwise
    """
    if run_id.startswith("no-idempotency-"):
        # disable idempotency check
        print("skip idempotency check...")
        return False
    print(f"Checking if {table} already exists for run_id {run_id}...")
    existing = persistence.get(table, run_id=run_id)
    # will return a list of rows if any exist with this run_id
    return (existing is not None) and (isinstance(existing, list) and len(existing) > 0)

# factories to generate dataclasses for Step. Use dataclass because it's easier to use isinstance() in base workflow.
def step_fn_dc_factory(funcs: list[StepFn]) -> StepFns:
    return StepFns(functions=funcs)

def step_fn_factory_dc_factory(factories: list[StepFnFactory]) -> StepFnFactories:
    return StepFnFactories(factories=factories)