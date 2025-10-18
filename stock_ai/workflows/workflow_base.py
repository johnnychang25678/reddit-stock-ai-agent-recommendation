from dataclasses import dataclass
import concurrent.futures as cf
from typing import Any, TypeVar, Union, List, cast
from collections.abc import Callable
from stock_ai.workflows.persistence.base_persistence import Persistence


# This constrains P so that it must be either Persistence itself or a subclass of Persistence.
# In other words: "P can only be something that implements the Persistence interface."
P = TypeVar("P", bound=Persistence)

# params: persistence, run_id
StepFn = Callable[[P, str], Any]

# params: persistence, run_id -> list of StepFn.
StepFnFactory = Callable[[P, str], list[StepFn]]

StepFunctions = Union[list[StepFn], StepFnFactory]

@dataclass
class Step:
    name: str
    functions: StepFunctions


class Workflow:
    def __init__(self, run_id:str, steps: list[Step], persistence: Persistence):
        self.run_id = run_id
        self.steps = steps
        self.persistence = persistence

    def run(self):
        # run each step serially
        for step in self.steps:
            print(f"Running step: {step.name}")
            functions = step.functions
            if callable(step.functions):
                # execute the factory to get the list of functions
                functions = step.functions(self.persistence, self.run_id)
    
            # Tell the type checker that functions is now a list of StepFn
            functions = cast(List[StepFn], functions)
            if not functions:
                print(f"No functions to run for step: {step.name}, skipping.")
                continue

            if len(functions) > 1:
                # run in parallel
                with cf.ThreadPoolExecutor(max_workers=len(functions) + 1) as ex:
                    futures = [ex.submit(func, self.persistence, self.run_id) for func in functions]
                    for future in cf.as_completed(futures):
                        future.result()
            else:
                functions[0](self.persistence, self.run_id)
