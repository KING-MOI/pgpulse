from __future__ import annotations

from typing import Any, Protocol

from pgpulse.config import Config


class Connection(Protocol):
    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...


RECOVERY_SQL = "SELECT pg_is_in_recovery() AS in_recovery"


def in_recovery(conn: Connection) -> bool:
    return bool(conn.fetchall(RECOVERY_SQL)[0]["in_recovery"])


VERSION_SQL = "SELECT current_setting('server_version_num')::int AS version"


def server_version(conn: Connection) -> int:
    return int(conn.fetchall(VERSION_SQL)[0]["version"])


SERVER_SQL = """
SELECT current_database() AS database,
       coalesce(host(inet_server_addr()), 'local socket') AS host,
       split_part(version(), ' ', 2) AS version,
       pg_is_in_recovery() AS in_recovery
"""


def describe(conn: Connection) -> str:
    row = conn.fetchall(SERVER_SQL)[0]
    role = "standby" if row["in_recovery"] else "primary"
    return f"{row['database']} on {row['host']} (PostgreSQL {row['version']}, {role})"


class PsycopgConnection:
    def __init__(self, dsn: str, statement_timeout_ms: int = 10_000, connect_timeout: int = 10) -> None:
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
        from psycopg.rows import dict_row

        try:
            params = {"application_name": "pgpulse", "connect_timeout": connect_timeout} | conninfo_to_dict(
                dsn
            )
            params["options"] = (
                f"{params.get('options', '')} -c statement_timeout={statement_timeout_ms}".strip()
            )
            self._conn = psycopg.connect(**params, row_factory=dict_row, autocommit=True)
        except psycopg.OperationalError as exc:
            raise ConnectionError(str(exc).strip()) from exc
        except psycopg.ProgrammingError as exc:
            raise ValueError(f"invalid dsn: {str(exc).strip()}") from exc

    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def close(self) -> None:
        self._conn.close()


def connect(cfg: Config) -> Connection:
    return PsycopgConnection(cfg.dsn or "", cfg.statement_timeout_ms, cfg.connect_timeout)
