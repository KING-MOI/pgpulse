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


UNINDEXED_FOREIGN_KEYS_SQL = """
SELECT n.nspname AS schemaname, t.relname, c.conname
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE c.contype = 'f' AND c.conparentid = 0
  AND NOT EXISTS (
      SELECT 1 FROM pg_index i
      WHERE i.indrelid = c.conrelid
        AND (string_to_array(i.indkey::text, ' ')::int2[])[1:cardinality(c.conkey)] @> c.conkey
  )
ORDER BY 1, 2, 3
"""


@check("unindexed_foreign_keys")
def unindexed_foreign_keys(conn: Connection, cfg: Config) -> CheckResult:
    """Foreign keys with no index on the referencing columns, so parent deletes scan the child."""
    rows = conn.fetchall(UNINDEXED_FOREIGN_KEYS_SQL)
    if not rows:
        return CheckResult("unindexed_foreign_keys", Status.OK, "every foreign key is indexed")
    details = [f"{r['schemaname']}.{r['relname']}: {r['conname']}" for r in rows]
    return CheckResult(
        "unindexed_foreign_keys", Status.WARN, plural(len(rows), "unindexed foreign key"), details
    )
