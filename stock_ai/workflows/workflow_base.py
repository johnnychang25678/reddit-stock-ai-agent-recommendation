from dataclasses import dataclass
import concurrent.futures as cf
from typing import Any, TypeVar, Union, cast
from collections.abc import Callable
from stock_ai.workflows.persistence.base_persistence import Persistence
import inspect


# This constrains P so that it must be either Persistence itself or a subclass of Persistence.
# In other words: "P can only be something that implements the Persistence interface."
P = TypeVar("P", bound=Persistence)

# params: persistence, run_id
StepFn = Callable[[P, str], Any]
# params: persistence, run_id -> list of StepFn.
StepFnFactory = Callable[[P, str], list[StepFn]]

@dataclass
class StepFns:
    functions: list[StepFn]

@dataclass
class StepFnFactories:
    factories: list[StepFnFactory]

StepFunctions = Union[StepFns, StepFnFactories]

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
            if isinstance(step.functions, StepFnFactories):
                # it's a StepFnFactories instance
                functions: list[StepFn] = []
                for factory in step.functions.factories:
                    funcs = factory(self.persistence, self.run_id)
                    functions.extend(funcs)
            else:
                functions = step.functions.functions

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
