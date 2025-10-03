from typing import Any, Mapping
from sqlalchemy import select, insert

from stock_ai.db.session import get_session
from stock_ai.db.base import Base
from stock_ai.workflows.persistence.base_persistence import Persistence


class SqlAlchemyPersistence(Persistence):
    """
    Multi-table SQL persistence using a registry of table bindings.

    registry: Mapping[str, type[Base]]
        dict table_name -> SqlAlchemy ORM model class.
    """

    def __init__(self, registry: Mapping[str, type[Base]]):
        if not registry:
            raise ValueError("registry must not be empty")
        self._registry = dict(registry)


    def get(self, table: str, default: Any = None, **filters) -> Any:
        """
        SELECT * FROM table [with simple filters in **filters].
        """
        binded_model = self._registry.get(table)
        if not binded_model:
            raise KeyError(f"Unknown table {table}")

        with get_session() as s:
            stmt = select(binded_model)
            for k, v in filters.items():
                col = getattr(binded_model, k, None)
                if not col:
                    raise ValueError(f"Unknown column {k!r} for {binded_model.__name__}")
                # this chain adds AND conditions
                stmt = stmt.where(col == v)

            return list(s.scalars(stmt).all()) or default

    def set(self, table: str, rows: list[dict]) -> None:
        """
        Insert rows into the table for table name 'key'.

        sqlalchmey insert example:
        # SomeTable has columns 'col1': int, 'col2': str
        insert_stmt = insert(SomeTable).values(
            [
                {"col1": 1, "col2": "some data"},
                {"col1": 2, "col2": "some more data"},
            ]
        )
        with get_session() as session:
            session.execute(insert_stmt)
            session.commit()
        """
        binded_model = self._registry.get(table)
        if not binded_model:
            raise KeyError(f"Unknown table {table!r}")

        if not rows:
            return

        with get_session() as s:
            stmt = insert(binded_model).values(rows)
            s.execute(stmt)
            s.commit()

    def update(self, mapping: Mapping[str, Any]) -> None:
        # No use cases for now.
        pass

    def hello(self) -> str:
        return "Hello from SqlAlchemyPersistence"