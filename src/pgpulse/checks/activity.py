from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

DATABASE_STATS_SQL = """
SELECT deadlocks, temp_files, temp_bytes, xact_commit, xact_rollback,
       greatest(extract(epoch FROM now() - coalesce(stats_reset, pg_postmaster_start_time())) / 86400, 1.0 / 24)
         AS days
FROM pg_stat_database
WHERE datname = current_database()
"""


@check("deadlocks")
def deadlocks(conn: Connection, cfg: Config) -> CheckResult:
    """Deadlocks per day since statistics were last reset."""
    limits = cfg.deadlocks
    row = conn.fetchall(DATABASE_STATS_SQL)[0]
    per_day = row["deadlocks"] / row["days"]
    status = Status.OK
    if per_day >= limits.fail_per_day:
        status = Status.FAIL
    elif per_day >= limits.warn_per_day:
        status = Status.WARN
    return CheckResult("deadlocks", status, f"{row['deadlocks']:,} deadlocks, {per_day:.1f} per day")
