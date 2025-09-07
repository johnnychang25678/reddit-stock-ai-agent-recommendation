from dataclasses import dataclass
import concurrent.futures as cf
from typing import Any
from collections.abc import Callable

# Context is a dictionary that holds data passed between steps
# each step function takes in a Context and returns a Context
# Context should be immutable, so each function returns a new Context
Context = dict[str, Any]
StepFn = Callable[[Context], Context]

@dataclass
class Step:
    name: str
    functions: list[StepFn]  # list of functions to run in this step


class Workflow:
    def __init__(self, steps: list[Step]):
        self.steps = steps

    def run(self, initial_context: Context | None = None) -> Context:
        context = initial_context or {}
        # run act step serially
        for step in self.steps:
            print(f"Running step: {step.name}")
            print(f"Current context keys: {list(context.keys())}")
            if len(step.functions) > 1:
                # run in parallel
                with cf.ThreadPoolExecutor(max_workers=len(step.functions) + 1) as ex:
                    futures = [ex.submit(func, context) for func in step.functions]
                    for future in cf.as_completed(futures):
                        result = future.result()
                        context.update(result)
            else:
                result = step.functions[0](context)
                context.update(result)

        return context