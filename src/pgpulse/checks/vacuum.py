from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, grade, plural

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
    status = grade(ratio, limits.warn, limits.fail)
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


XMIN_HOLDERS_SQL = """
SELECT 'session ' || pid AS holder, age(backend_xmin)::bigint AS age
FROM pg_stat_activity WHERE backend_xmin IS NOT NULL AND pid <> pg_backend_pid()
UNION ALL
SELECT 'prepared transaction ' || gid, age(transaction)::bigint FROM pg_prepared_xacts
UNION ALL
SELECT 'replication slot ' || slot_name, age(xmin)::bigint FROM pg_replication_slots WHERE xmin IS NOT NULL
UNION ALL
SELECT 'replication slot ' || slot_name || ' (catalog)', age(catalog_xmin)::bigint
FROM pg_replication_slots WHERE catalog_xmin IS NOT NULL
ORDER BY age DESC
"""


@check("xmin_horizon")
def xmin_horizon(conn: Connection, cfg: Config) -> CheckResult:
    """Whatever is holding back the oldest xmin and stopping vacuum from cleaning up."""
    limits = cfg.xmin_horizon
    rows = conn.fetchall(XMIN_HOLDERS_SQL)
    if not rows:
        return CheckResult("xmin_horizon", Status.OK, "nothing is holding back vacuum")
    oldest = rows[0]
    status = grade(oldest["age"], limits.warn_age, limits.fail_age)
    details = [f"{r['holder']}: {r['age']:,} transactions old" for r in rows if r["age"] >= limits.warn_age]
    return CheckResult("xmin_horizon", status, f"oldest xmin is {oldest['age']:,} transactions old", details)
