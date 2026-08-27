from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, grade, plural

LONG_QUERIES_SQL = """
SELECT pid, usename, extract(epoch FROM now() - query_start)::float AS seconds,
       left(regexp_replace(query, '[[:space:]]+', ' ', 'g'), 80) AS query
FROM pg_stat_activity
WHERE state = 'active' AND backend_type = 'client backend' AND pid <> pg_backend_pid()
ORDER BY query_start
"""


@check("long_queries")
def long_running_queries(conn: Connection, cfg: Config) -> CheckResult:
    """Active queries running longer than the configured limit."""
    limits = cfg.long_queries
    rows = [r for r in conn.fetchall(LONG_QUERIES_SQL) if r["seconds"] >= limits.warn_seconds]
    if not rows:
        return CheckResult("long_queries", Status.OK, "no long-running queries")
    worst = max(r["seconds"] for r in rows)
    status = grade(worst, limits.warn_seconds, limits.fail_seconds)
    details = [f"pid {r['pid']} ({r['usename']}) {r['seconds']:.0f}s: {r['query']}" for r in rows]
    return CheckResult(
        "long_queries",
        status,
        f"{plural(len(rows), 'query', 'queries')} over {limits.warn_seconds:g}s",
        details,
    )


IDLE_IN_TRANSACTION_SQL = """
SELECT pid, usename, extract(epoch FROM now() - state_change)::float AS seconds,
       left(regexp_replace(query, '[[:space:]]+', ' ', 'g'), 80) AS query
FROM pg_stat_activity
WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
ORDER BY state_change
"""


@check("idle_in_transaction")
def idle_in_transaction(conn: Connection, cfg: Config) -> CheckResult:
    """Sessions holding a transaction open while doing nothing."""
    limits = cfg.idle_in_transaction
    rows = [r for r in conn.fetchall(IDLE_IN_TRANSACTION_SQL) if r["seconds"] >= limits.warn_seconds]
    if not rows:
        return CheckResult("idle_in_transaction", Status.OK, "no idle transactions")
    worst = max(r["seconds"] for r in rows)
    status = grade(worst, limits.warn_seconds, limits.fail_seconds)
    details = [f"pid {r['pid']} ({r['usename']}) idle {r['seconds']:.0f}s after: {r['query']}" for r in rows]
    return CheckResult("idle_in_transaction", status, plural(len(rows), "idle transaction"), details)


LONG_TRANSACTIONS_SQL = """
SELECT pid, usename, state, extract(epoch FROM now() - xact_start)::float AS seconds,
       left(regexp_replace(query, '[[:space:]]+', ' ', 'g'), 80) AS query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND backend_type = 'client backend' AND pid <> pg_backend_pid()
ORDER BY xact_start
"""


@check("long_transactions")
def long_transactions(conn: Connection, cfg: Config) -> CheckResult:
    """Transactions open for a long time, whatever they are doing right now."""
    limits = cfg.long_transactions
    rows = [r for r in conn.fetchall(LONG_TRANSACTIONS_SQL) if r["seconds"] >= limits.warn_seconds]
    if not rows:
        return CheckResult("long_transactions", Status.OK, "no long transactions")
    worst = max(r["seconds"] for r in rows)
    status = grade(worst, limits.warn_seconds, limits.fail_seconds)
    details = [
        f"pid {r['pid']} ({r['usename']}, {r['state']}) open {r['seconds']:.0f}s: {r['query']}" for r in rows
    ]
    return CheckResult("long_transactions", status, plural(len(rows), "long transaction"), details)
