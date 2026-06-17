from __future__ import annotations

from typing import Any, Protocol


class Connection(Protocol):
    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...


RECOVERY_SQL = "SELECT pg_is_in_recovery() AS in_recovery"


def in_recovery(conn: Connection) -> bool:
    return bool(conn.fetchall(RECOVERY_SQL)[0]["in_recovery"])


VERSION_SQL = "SELECT current_setting('server_version_num')::int AS version"


def server_version(conn: Connection) -> int:
    return int(conn.fetchall(VERSION_SQL)[0]["version"])


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
