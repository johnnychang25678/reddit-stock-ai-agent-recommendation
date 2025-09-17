from typing import Any
from collections.abc import Mapping, Iterable
import threading
from stock_ai.workflows.persistence.base_persistence import Persistence

class InMemoryPersistence(Persistence):
    """Thread-safe in-memory store"""
    def __init__(self):
        self._d: dict[str, Any] = {}
        # use reentrant lock to allow same thread to re-acquire lock
        self._lock = threading.RLock()
    
    def __repr__(self) -> str:
        with self._lock: 
            return self._d.keys().__repr__()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._d.get(key, default)

    def set(self, key: str, rows: list[dict]) -> None:
        with self._lock: 
            self._d[key] = rows

    def update(self, mapping: Mapping[str, Any]) -> None:
        with self._lock:
            self._d.update(mapping)

    def keys(self) -> Iterable[str]:
        with self._lock:
            return list(self._d.keys())
