from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, grade, plural

BLOCKED_SQL = """
SELECT pid, pg_blocking_pids(pid) AS blocked_by,
       extract(epoch FROM now() - query_start)::float AS seconds,
       left(regexp_replace(query, '[[:space:]]+', ' ', 'g'), 80) AS query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0
"""


@check("blocking_locks")
def blocking_locks(conn: Connection, cfg: Config) -> CheckResult:
    """Sessions waiting on locks held by other sessions."""
    limits = cfg.blocking_locks
    rows = [r for r in conn.fetchall(BLOCKED_SQL) if r["seconds"] >= limits.warn_seconds]
    if not rows:
        return CheckResult("blocking_locks", Status.OK, "no blocked sessions")
    worst = max(r["seconds"] for r in rows)
    status = grade(worst, limits.warn_seconds, limits.fail_seconds)
    details = [
        f"pid {r['pid']} waiting {r['seconds']:.0f}s on {', '.join(map(str, r['blocked_by']))}: {r['query']}"
        for r in rows
    ]
    return CheckResult("blocking_locks", status, plural(len(rows), "blocked session"), details)
