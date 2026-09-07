from __future__ import annotations

import json
from pathlib import Path

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, grade, plural

TABLE_SIZES_SQL = """
SELECT current_database() AS database, extract(epoch FROM now())::float AS now,
       format('%I.%I', n.nspname, c.relname) AS name, pg_total_relation_size(c.oid) AS bytes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'm')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
"""

MB = 1024**2


@check("table_growth")
def table_growth(conn: Connection, cfg: Config) -> CheckResult:
    """Tables growing faster than expected, compared with the size snapshot from an earlier run."""
    limits = cfg.table_growth
    if not limits.state_file:
        return CheckResult("table_growth", Status.SKIP, "set table_growth.state_file to track growth")
    rows = conn.fetchall(TABLE_SIZES_SQL)
    if not rows:
        return CheckResult("table_growth", Status.OK, "no tables")
    path = Path(limits.state_file).expanduser()
    database, now = rows[0]["database"], rows[0]["now"]
    state = json.loads(path.read_text()) if path.exists() else {}
    previous = state.get(database)
    if previous and now - previous["taken"] < limits.min_hours * 3600:
        age = (now - previous["taken"]) / 60
        return CheckResult(
            "table_growth", Status.SKIP, f"last snapshot is {age:.0f} minutes old, need {limits.min_hours:g}h"
        )
    state[database] = {"taken": now, "sizes": {r["name"]: r["bytes"] for r in rows}}
    path.write_text(json.dumps(state))
    if not previous:
        return CheckResult("table_growth", Status.SKIP, "saved a first size snapshot to compare against")
    days = (now - previous["taken"]) / 86400
    status = Status.OK
    details = []
    for r in sorted(rows, key=lambda r: r["bytes"], reverse=True):
        before = previous["sizes"].get(r["name"])
        if before is None:
            continue
        per_day = (r["bytes"] - before) / days
        level = grade(per_day, limits.warn_bytes_per_day, limits.fail_bytes_per_day)
        if level is Status.OK:
            continue
        status = max(status, level)
        details.append(f"{r['name']}: +{per_day / MB:,.1f} MB per day")
    if not details:
        return CheckResult(
            "table_growth",
            Status.OK,
            f"no table grew faster than {limits.warn_bytes_per_day / MB:,.0f} MB per day",
        )
    return CheckResult("table_growth", status, plural(len(details), "table") + " growing fast", details)
