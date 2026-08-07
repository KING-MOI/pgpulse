from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

SETTINGS_SQL = """
SELECT name, setting FROM pg_settings
WHERE name IN ('fsync', 'full_page_writes', 'autovacuum', 'track_counts')
"""

RISKY = {
    "fsync": ("off", Status.FAIL, "a crash can corrupt the cluster"),
    "full_page_writes": ("off", Status.FAIL, "torn pages after a crash cannot be repaired"),
    "track_counts": ("off", Status.FAIL, "autovacuum and most pgpulse checks are blind"),
    "autovacuum": ("off", Status.WARN, "dead tuples and xid age only shrink by hand"),
}


@check("settings")
def risky_settings(conn: Connection, cfg: Config) -> CheckResult:
    """Server settings that trade safety or visibility for speed."""
    status = Status.OK
    details = []
    for row in conn.fetchall(SETTINGS_SQL):
        bad, level, why = RISKY[row["name"]]
        if row["setting"] == bad:
            status = max(status, level)
            details.append(f"{row['name']} = {bad}: {why}")
    if not details:
        return CheckResult("settings", Status.OK, "no risky settings")
    return CheckResult("settings", status, plural(len(details), "risky setting"), details)
