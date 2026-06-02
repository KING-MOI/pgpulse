from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

UNUSED_INDEXES_SQL = """
SELECT s.schemaname, s.relname, s.indexrelname,
       pg_relation_size(s.indexrelid) AS size_bytes,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0 AND NOT i.indisunique
ORDER BY size_bytes DESC
"""


@check("unused_indexes")
def unused_indexes(conn: Connection, cfg: Config) -> CheckResult:
    """Non-unique indexes that have never been scanned."""
    floor = cfg.unused_indexes.min_size_bytes
    rows = [r for r in conn.fetchall(UNUSED_INDEXES_SQL) if r["size_bytes"] >= floor]
    if not rows:
        return CheckResult("unused_indexes", Status.OK, "no unused indexes")
    details = [f"{r['schemaname']}.{r['indexrelname']} on {r['relname']} ({r['size']})" for r in rows]
    return CheckResult(
        "unused_indexes", Status.WARN, plural(len(rows), "unused index", "unused indexes"), details
    )


INVALID_INDEXES_SQL = """
SELECT n.nspname AS schemaname, c.relname AS indexrelname
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT i.indisvalid
"""


@check("invalid_indexes")
def invalid_indexes(conn: Connection, cfg: Config) -> CheckResult:
    """Indexes left invalid by a failed CREATE INDEX CONCURRENTLY."""
    rows = conn.fetchall(INVALID_INDEXES_SQL)
    if not rows:
        return CheckResult("invalid_indexes", Status.OK, "no invalid indexes")
    details = [f"{r['schemaname']}.{r['indexrelname']}" for r in rows]
    return CheckResult(
        "invalid_indexes", Status.FAIL, plural(len(rows), "invalid index", "invalid indexes"), details
    )
