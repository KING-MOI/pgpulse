from __future__ import annotations

from typing import Any


class FakeConnection:
    def __init__(self, responses: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.responses = responses or {}
        self.queries: list[str] = []
        self.closed = False

    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        self.queries.append(sql)
        if sql not in self.responses:
            raise AssertionError(f"unexpected query: {sql[:60]!r}")
        return self.responses[sql]

    def close(self) -> None:
        self.closed = True
