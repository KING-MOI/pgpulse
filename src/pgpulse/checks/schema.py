from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

NO_PRIMARY_KEY_SQL = """
SELECT n.nspname AS schemaname, c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p')
  AND NOT c.relispartition
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
  AND NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisprimary)
ORDER BY 1, 2
"""


@check("primary_keys")
def missing_primary_keys(conn: Connection, cfg: Config) -> CheckResult:
    """Tables without a primary key, which breaks logical replication of updates."""
    rows = conn.fetchall(NO_PRIMARY_KEY_SQL)
    if not rows:
        return CheckResult("primary_keys", Status.OK, "every table has a primary key")
    details = [f"{r['schemaname']}.{r['relname']}" for r in rows]
    return CheckResult(
        "primary_keys", Status.WARN, plural(len(rows), "table") + " without a primary key", details
    )
