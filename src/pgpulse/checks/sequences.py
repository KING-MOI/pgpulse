from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

SEQUENCES_SQL = """
SELECT s.schemaname, s.sequencename, s.start_value, s.last_value, s.increment_by,
       CASE a.atttypid WHEN 'int2'::regtype THEN greatest(s.min_value, -32768)
                       WHEN 'int4'::regtype THEN greatest(s.min_value, -2147483648)
                       ELSE s.min_value END AS min_value,
       CASE a.atttypid WHEN 'int2'::regtype THEN least(s.max_value, 32767)
                       WHEN 'int4'::regtype THEN least(s.max_value, 2147483647)
                       ELSE s.max_value END AS max_value
FROM pg_sequences s
LEFT JOIN pg_depend d
       ON d.classid = 'pg_class'::regclass AND d.refclassid = 'pg_class'::regclass
      AND d.objid = format('%I.%I', s.schemaname, s.sequencename)::regclass
      AND d.deptype IN ('a', 'i')
LEFT JOIN pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
WHERE s.last_value IS NOT NULL
"""


@check("sequences")
def sequence_exhaustion(conn: Connection, cfg: Config) -> CheckResult:
    """Sequences that are running out of values."""
    limits = cfg.sequences
    status = Status.OK
    details = []
    for r in conn.fetchall(SEQUENCES_SQL):
        limit = r["max_value"] if r["increment_by"] > 0 else r["min_value"]
        used = (r["last_value"] - r["start_value"]) / (limit - r["start_value"])
        if used < limits.warn:
            continue
        status = max(status, Status.FAIL if used >= limits.fail else Status.WARN)
        details.append(f"{r['schemaname']}.{r['sequencename']}: {used:.1%} of the way to {limit:,}")
    if not details:
        return CheckResult("sequences", Status.OK, "sequences have room to grow")
    return CheckResult(
        "sequences", status, plural(len(details), "sequence") + " close to exhaustion", details
    )
