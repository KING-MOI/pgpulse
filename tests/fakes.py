from __future__ import annotations

from typing import Any


class FakeConnection:
    def __init__(self, responses: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.responses = responses or {}
        self.queries: list[str] = []
        self.params: list[tuple[Any, ...] | None] = []
        self.closed = False

    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        self.queries.append(sql)
        self.params.append(params)
        if sql not in self.responses:
            raise AssertionError(f"unexpected query: {sql[:60]!r}")
        return self.responses[sql]

    def close(self) -> None:
        self.closed = True


def healthy() -> dict[str, list[dict[str, Any]]]:
    from pgpulse.checks.bloat import DEAD_TUPLES_SQL
    from pgpulse.checks.cache import CACHE_HIT_SQL
    from pgpulse.checks.connections import CONNECTIONS_SQL
    from pgpulse.checks.indexes import INVALID_INDEXES_SQL, UNUSED_INDEXES_SQL
    from pgpulse.checks.locks import BLOCKED_SQL
    from pgpulse.checks.queries import IDLE_IN_TRANSACTION_SQL, LONG_QUERIES_SQL
    from pgpulse.checks.vacuum import STALE_VACUUM_SQL, XID_AGE_SQL

    return {
        CACHE_HIT_SQL: [{"hit": 999.0, "read": 1.0}],
        CONNECTIONS_SQL: [{"used": 5, "max": 100}],
        LONG_QUERIES_SQL: [],
        IDLE_IN_TRANSACTION_SQL: [],
        UNUSED_INDEXES_SQL: [],
        INVALID_INDEXES_SQL: [],
        DEAD_TUPLES_SQL: [],
        BLOCKED_SQL: [],
        STALE_VACUUM_SQL: [],
        XID_AGE_SQL: [{"datname": "app", "age": 1_000_000}],
    }
