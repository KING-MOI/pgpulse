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
    from pgpulse.checks.activity import ARCHIVER_SQL, CHECKPOINTS_SQL, DATABASE_STATS_SQL
    from pgpulse.checks.bloat import DEAD_TUPLES_SQL
    from pgpulse.checks.cache import CACHE_HIT_SQL, INDEX_CACHE_HIT_SQL
    from pgpulse.checks.connections import CONNECTIONS_SQL
    from pgpulse.checks.indexes import (
        DUPLICATE_INDEXES_SQL,
        INVALID_INDEXES_SQL,
        SEQ_SCANS_SQL,
        UNUSED_INDEXES_SQL,
    )
    from pgpulse.checks.locks import BLOCKED_SQL
    from pgpulse.checks.queries import IDLE_IN_TRANSACTION_SQL, LONG_QUERIES_SQL
    from pgpulse.checks.replication import REPLICATION_LAG_SQL, SLOTS_SQL
    from pgpulse.checks.schema import NO_PRIMARY_KEY_SQL
    from pgpulse.checks.sequences import SEQUENCES_SQL
    from pgpulse.checks.settings import SETTINGS_SQL
    from pgpulse.checks.vacuum import (
        MXID_AGE_SQL,
        STALE_STATS_SQL,
        STALE_VACUUM_SQL,
        XID_AGE_SQL,
        XMIN_HOLDERS_SQL,
    )
    from pgpulse.db import RECOVERY_SQL, SERVER_SQL, VERSION_SQL

    return {
        RECOVERY_SQL: [{"in_recovery": False}],
        SERVER_SQL: [{"database": "app", "host": "10.0.0.5", "version": "16.4", "in_recovery": False}],
        VERSION_SQL: [{"version": 160004}],
        CHECKPOINTS_SQL: [{"timed": 100, "requested": 2}],
        CACHE_HIT_SQL: [{"hit": 99_999.0, "read": 1.0}],
        INDEX_CACHE_HIT_SQL: [{"hit": 99_999.0, "read": 1.0}],
        CONNECTIONS_SQL: [{"used": 5, "max": 100}],
        LONG_QUERIES_SQL: [],
        IDLE_IN_TRANSACTION_SQL: [],
        UNUSED_INDEXES_SQL: [],
        INVALID_INDEXES_SQL: [],
        DUPLICATE_INDEXES_SQL: [],
        SEQ_SCANS_SQL: [],
        DEAD_TUPLES_SQL: [],
        BLOCKED_SQL: [],
        REPLICATION_LAG_SQL: [],
        SLOTS_SQL: [],
        SEQUENCES_SQL: [],
        SETTINGS_SQL: [{"name": "fsync", "setting": "on"}],
        NO_PRIMARY_KEY_SQL: [],
        DATABASE_STATS_SQL: [
            {
                "deadlocks": 0,
                "temp_files": 0,
                "temp_bytes": 0,
                "xact_commit": 1000,
                "xact_rollback": 1,
                "days": 10.0,
            }
        ],
        STALE_VACUUM_SQL: [],
        XMIN_HOLDERS_SQL: [],
        STALE_STATS_SQL: [],
        ARCHIVER_SQL: [{"mode": "on", "failed_count": 0, "last_failed_wal": None, "failing": False}],
        XID_AGE_SQL: [{"datname": "app", "age": 1_000_000}],
        MXID_AGE_SQL: [{"datname": "app", "age": 10}],
    }
