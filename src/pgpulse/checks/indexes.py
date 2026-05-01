from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

UNUSED_INDEXES_SQL = """
SELECT s.schemaname, s.relname, s.indexrelname,
       pg_relation_size(s.indexrelid) AS size_bytes
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0 AND NOT i.indisunique
ORDER BY size_bytes DESC
"""


@check("unused_indexes")
def unused_indexes(conn: Connection, cfg: Config) -> CheckResult:
    floor = cfg.unused_indexes.min_size_bytes
    rows = [r for r in conn.fetchall(UNUSED_INDEXES_SQL) if r["size_bytes"] >= floor]
    if not rows:
        return CheckResult("unused_indexes", Status.OK, "no unused indexes")
    details = [
        f"{r['schemaname']}.{r['indexrelname']} on {r['relname']} ({r['size_bytes']} bytes)" for r in rows
    ]
    return CheckResult("unused_indexes", Status.WARN, f"{len(rows)} unused indexes", details)
