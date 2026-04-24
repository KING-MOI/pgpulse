from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

LONG_QUERIES_SQL = """
SELECT pid, usename, extract(epoch FROM now() - query_start)::float AS seconds,
       left(query, 80) AS query
FROM pg_stat_activity
WHERE state = 'active' AND pid <> pg_backend_pid()
ORDER BY query_start
"""


@check("long_queries")
def long_running_queries(conn: Connection, cfg: Config) -> CheckResult:
    limits = cfg.long_queries
    rows = [r for r in conn.fetchall(LONG_QUERIES_SQL) if r["seconds"] >= limits.warn_seconds]
    if not rows:
        return CheckResult("long_queries", Status.OK, "no long-running queries")
    worst = max(r["seconds"] for r in rows)
    status = Status.FAIL if worst >= limits.fail_seconds else Status.WARN
    details = [f"pid {r['pid']} ({r['usename']}) {r['seconds']:.0f}s: {r['query']}" for r in rows]
    return CheckResult("long_queries", status, f"{len(rows)} queries over {limits.warn_seconds:g}s", details)
