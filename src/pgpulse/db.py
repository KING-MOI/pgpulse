from __future__ import annotations

from typing import Any, Protocol


class Connection(Protocol):
    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...


class PsycopgConnection:
    def __init__(self, dsn: str) -> None:
        import psycopg
        from psycopg.rows import dict_row

        try:
            self._conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
        except psycopg.OperationalError as exc:
            raise ConnectionError(str(exc).strip()) from exc

    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def close(self) -> None:
        self._conn.close()
