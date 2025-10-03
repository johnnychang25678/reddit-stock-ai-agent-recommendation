from typing import Any
from abc import ABC, abstractmethod

class Persistence(ABC):
    @abstractmethod
    def get(self, *args, **kwargs) -> Any: ...
    @abstractmethod
    def set(self, table: str, rows: list[dict]) -> None: ...
    @abstractmethod
    def update(self, *args, **kwargs) -> None: ...


