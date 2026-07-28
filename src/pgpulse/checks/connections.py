from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, grade

CONNECTIONS_SQL = """
SELECT count(*) AS used,
       current_setting('max_connections')::int
         - current_setting('superuser_reserved_connections')::int AS max
FROM pg_stat_activity
WHERE backend_type = 'client backend'
"""


@check("connections")
def connection_saturation(conn: Connection, cfg: Config) -> CheckResult:
    """Client connections in use versus max_connections."""
    row = conn.fetchall(CONNECTIONS_SQL)[0]
    used, limit = row["used"], row["max"]
    ratio = used / limit
    status = grade(ratio, cfg.connections.warn, cfg.connections.fail)
    return CheckResult("connections", status, f"{used}/{limit} connections in use ({ratio:.0%})")
