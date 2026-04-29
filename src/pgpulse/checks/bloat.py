from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

DEAD_TUPLES_SQL = """
SELECT schemaname, relname, n_live_tup AS live, n_dead_tup AS dead
FROM pg_stat_user_tables
"""


@check("bloat")
def table_bloat(conn: Connection, cfg: Config) -> CheckResult:
    limits = cfg.bloat
    status = Status.OK
    details = []
    for r in conn.fetchall(DEAD_TUPLES_SQL):
        total = r["live"] + r["dead"]
        if total < limits.min_rows:
            continue
        ratio = r["dead"] / total
        if ratio < limits.warn:
            continue
        status = max(status, Status.FAIL if ratio >= limits.fail else Status.WARN)
        details.append(f"{r['schemaname']}.{r['relname']}: {ratio:.0%} dead tuples")
    if not details:
        return CheckResult("bloat", Status.OK, "no bloated tables")
    return CheckResult("bloat", status, f"{len(details)} bloated tables", details)
