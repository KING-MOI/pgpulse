from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

SEQUENCES_SQL = """
SELECT schemaname, sequencename, start_value, last_value, min_value, max_value, increment_by
FROM pg_sequences
WHERE last_value IS NOT NULL
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
