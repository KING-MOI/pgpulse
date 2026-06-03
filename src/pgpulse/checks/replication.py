from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

REPLICATION_LAG_SQL = """
SELECT application_name, client_addr::text AS client,
       extract(epoch FROM replay_lag)::float AS seconds
FROM pg_stat_replication
"""


@check("replication_lag")
def replication_lag(conn: Connection, cfg: Config) -> CheckResult:
    """Replay lag of each standby attached to this primary."""
    limits = cfg.replication_lag
    rows = conn.fetchall(REPLICATION_LAG_SQL)
    if not rows:
        return CheckResult("replication_lag", Status.OK, "no standbys attached")
    status = Status.OK
    details = []
    for r in rows:
        lag = r["seconds"] or 0.0
        if lag >= limits.fail_seconds:
            status = Status.FAIL
        elif lag >= limits.warn_seconds:
            status = max(status, Status.WARN)
        details.append(f"{r['application_name']} ({r['client']}): {lag:.1f}s behind")
    worst = max(r["seconds"] or 0.0 for r in rows)
    return CheckResult(
        "replication_lag",
        status,
        f"{plural(len(rows), 'standby', 'standbys')}, worst lag {worst:.1f}s",
        details,
    )
