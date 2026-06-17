from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection, server_version
from pgpulse.result import CheckResult, Status, plural

DATABASE_STATS_SQL = """
SELECT deadlocks, temp_files, temp_bytes, xact_commit, xact_rollback,
       greatest(extract(epoch FROM now() - coalesce(stats_reset, pg_postmaster_start_time())) / 86400, 1)
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
    return CheckResult("deadlocks", status, f"{plural(row['deadlocks'], 'deadlock')}, {per_day:.1f} per day")


@check("temp_files")
def temp_files(conn: Connection, cfg: Config) -> CheckResult:
    """Bytes spilled to temporary files per day, a sign work_mem is too small."""
    limits = cfg.temp_files
    row = conn.fetchall(DATABASE_STATS_SQL)[0]
    per_day = row["temp_bytes"] / row["days"]
    status = Status.WARN if per_day >= limits.warn_bytes_per_day else Status.OK
    return CheckResult(
        "temp_files", status, f"{plural(row['temp_files'], 'temp file')}, {per_day / 1024**2:,.1f} MB per day"
    )


@check("rollbacks")
def rollbacks(conn: Connection, cfg: Config) -> CheckResult:
    """Share of transactions that roll back instead of committing."""
    limits = cfg.rollbacks
    row = conn.fetchall(DATABASE_STATS_SQL)[0]
    total = row["xact_commit"] + row["xact_rollback"]
    ratio = row["xact_rollback"] / total if total else 0.0
    status = Status.OK
    if ratio >= limits.fail:
        status = Status.FAIL
    elif ratio >= limits.warn:
        status = Status.WARN
    return CheckResult("rollbacks", status, f"{ratio:.1%} of {total:,} transactions rolled back")


CHECKPOINTS_SQL = """
SELECT checkpoints_timed AS timed, checkpoints_req AS requested FROM pg_stat_bgwriter
"""

CHECKPOINTS_17_SQL = """
SELECT num_timed AS timed, num_requested AS requested FROM pg_stat_checkpointer
"""


@check("checkpoints")
def checkpoints(conn: Connection, cfg: Config) -> CheckResult:
    """Share of checkpoints forced by WAL volume rather than the timer."""
    limits = cfg.checkpoints
    sql = CHECKPOINTS_17_SQL if server_version(conn) >= 170000 else CHECKPOINTS_SQL
    row = conn.fetchall(sql)[0]
    total = row["timed"] + row["requested"]
    if total < limits.min_checkpoints:
        return CheckResult(
            "checkpoints", Status.OK, f"only {plural(total, 'checkpoint')} so far, too few to judge"
        )
    ratio = row["requested"] / total
    status = Status.WARN if ratio >= limits.warn else Status.OK
    return CheckResult("checkpoints", status, f"{ratio:.0%} of {plural(total, 'checkpoint')} were requested")
