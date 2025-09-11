from dataclasses import dataclass
import concurrent.futures as cf
from typing import Any
from collections.abc import Callable
from stock_ai.workflows.persistence.base_persistence import Persistence

# params: persistence, run_id
StepFn = Callable[[Persistence, str], Any]

@dataclass
class Step:
    name: str
    functions: list[StepFn]  # list of functions to run in this step


class Workflow:
    def __init__(self, run_id:str, steps: list[Step], persistence: Persistence):
        self.run_id = run_id
        self.steps = steps
        self.persistence = persistence

    def run(self):
        # run each step serially
        for step in self.steps:
            print(f"Running step: {step.name}")
            if len(step.functions) > 1:
                # run in parallel
                with cf.ThreadPoolExecutor(max_workers=len(step.functions) + 1) as ex:
                    futures = [ex.submit(func, self.persistence, self.run_id) for func in step.functions]
                    for future in cf.as_completed(futures):
                        future.result()
            else:
                step.functions[0](self.persistence, self.run_id)
