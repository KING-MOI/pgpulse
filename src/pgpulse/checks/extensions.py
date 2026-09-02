from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, plural

OUTDATED_EXTENSIONS_SQL = """
SELECT name, installed_version, default_version
FROM pg_available_extensions
WHERE installed_version IS NOT NULL AND installed_version <> default_version
ORDER BY name
"""


@check("extension_updates")
def extension_updates(conn: Connection, cfg: Config) -> CheckResult:
    """Extensions still on an older version than the server ships, often left over from an upgrade."""
    rows = conn.fetchall(OUTDATED_EXTENSIONS_SQL)
    if not rows:
        return CheckResult("extension_updates", Status.OK, "extensions are up to date")
    details = [
        f"{r['name']} {r['installed_version']} -> {r['default_version']} (ALTER EXTENSION {r['name']} UPDATE)"
        for r in rows
    ]
    return CheckResult("extension_updates", Status.WARN, plural(len(rows), "outdated extension"), details)
