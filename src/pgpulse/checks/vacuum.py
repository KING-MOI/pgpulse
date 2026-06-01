from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

XID_LIMIT = 2**31

XID_AGE_SQL = """
SELECT datname, age(datfrozenxid)::bigint AS age
FROM pg_database
WHERE datallowconn
ORDER BY age DESC
"""


@check("xid_wraparound")
def xid_wraparound(conn: Connection, cfg: Config) -> CheckResult:
    """How close each database is to transaction ID wraparound."""
    limits = cfg.xid_wraparound
    rows = conn.fetchall(XID_AGE_SQL)
    if not rows:
        return CheckResult("xid_wraparound", Status.OK, "no databases visible")
    worst = rows[0]
    ratio = worst["age"] / XID_LIMIT
    status = Status.OK
    if ratio >= limits.fail:
        status = Status.FAIL
    elif ratio >= limits.warn:
        status = Status.WARN
    details = [
        f"{r['datname']}: {r['age']:,} ({r['age'] / XID_LIMIT:.1%})"
        for r in rows
        if r["age"] / XID_LIMIT >= limits.warn
    ]
    return CheckResult(
        "xid_wraparound",
        status,
        f"{worst['datname']} has used {ratio:.1%} of xid space",
        details,
    )


STALE_VACUUM_SQL = """
SELECT schemaname, relname, n_dead_tup AS dead,
       extract(epoch FROM now() - greatest(last_vacuum, last_autovacuum))::float / 86400 AS days
FROM pg_stat_user_tables
WHERE n_dead_tup >= %s
"""


@check("vacuum_age")
def vacuum_age(conn: Connection, cfg: Config) -> CheckResult:
    """Tables with dead tuples that have not been vacuumed recently."""
    limits = cfg.vacuum_age
    status = Status.OK
    details = []
    for r in conn.fetchall(STALE_VACUUM_SQL, (limits.min_dead_rows,)):
        days = r["days"]
        if days is not None and days < limits.warn_days:
            continue
        stale = days is None or days >= limits.fail_days
        status = max(status, Status.FAIL if stale else Status.WARN)
        when = "never vacuumed" if days is None else f"last vacuumed {days:.0f} days ago"
        details.append(f"{r['schemaname']}.{r['relname']}: {when}, {r['dead']:,} dead tuples")
    if not details:
        return CheckResult("vacuum_age", Status.OK, "vacuum is keeping up")
    return CheckResult("vacuum_age", status, plural(len(details), "table") + " overdue for vacuum", details)
