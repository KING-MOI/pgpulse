from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection, in_recovery
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
    if in_recovery(conn):
        return CheckResult("unused_indexes", Status.SKIP, "scan counts on a standby only cover the standby")
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


DUPLICATE_INDEXES_SQL = """
SELECT n.nspname AS schemaname, t.relname, array_agg(c.relname ORDER BY c.relname) AS indexes
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
GROUP BY n.nspname, t.relname, i.indkey::text, i.indclass::text,
         coalesce(pg_get_expr(i.indexprs, i.indrelid), ''),
         coalesce(pg_get_expr(i.indpred, i.indrelid), '')
HAVING count(*) > 1
"""


@check("duplicate_indexes")
def duplicate_indexes(conn: Connection, cfg: Config) -> CheckResult:
    """Indexes that cover exactly the same columns as another index."""
    rows = conn.fetchall(DUPLICATE_INDEXES_SQL)
    if not rows:
        return CheckResult("duplicate_indexes", Status.OK, "no duplicate indexes")
    details = [f"{r['schemaname']}.{r['relname']}: {', '.join(r['indexes'])}" for r in rows]
    return CheckResult(
        "duplicate_indexes", Status.WARN, plural(len(rows), "set") + " of duplicate indexes", details
    )


SEQ_SCANS_SQL = """
SELECT schemaname, relname, seq_scan, coalesce(idx_scan, 0) AS idx_scan, n_live_tup AS rows
FROM pg_stat_user_tables
WHERE n_live_tup >= %s AND seq_scan > 0
ORDER BY seq_tup_read DESC
"""


@check("index_usage")
def index_usage(conn: Connection, cfg: Config) -> CheckResult:
    """Large tables that are mostly read with sequential scans."""
    if in_recovery(conn):
        return CheckResult("index_usage", Status.SKIP, "scan counts on a standby only cover the standby")
    limits = cfg.index_usage
    details = []
    for r in conn.fetchall(SEQ_SCANS_SQL, (limits.min_rows,)):
        ratio = r["idx_scan"] / (r["idx_scan"] + r["seq_scan"])
        if ratio < limits.warn:
            details.append(
                f"{r['schemaname']}.{r['relname']}: {ratio:.0%} index scans over {r['rows']:,} rows"
            )
    if not details:
        return CheckResult("index_usage", Status.OK, "large tables are read through indexes")
    return CheckResult(
        "index_usage", Status.WARN, plural(len(details), "table") + " mostly sequentially scanned", details
    )
