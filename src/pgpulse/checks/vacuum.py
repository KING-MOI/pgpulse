from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

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
        f"oldest xid in {worst['datname']} is {ratio:.1%} of the way to wraparound",
        details,
    )
