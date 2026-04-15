from __future__ import annotations

from typing import Any, Protocol


class Connection(Protocol):
    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...
