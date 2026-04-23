from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

CONNECTIONS_SQL = """
SELECT count(*) AS used,
       current_setting('max_connections')::int AS max
FROM pg_stat_activity
"""


@check("connections")
def connection_saturation(conn: Connection, cfg: Config) -> CheckResult:
    row = conn.fetchall(CONNECTIONS_SQL)[0]
    used, limit = row["used"], row["max"]
    ratio = used / limit
    status = Status.OK
    if ratio >= cfg.connections.fail:
        status = Status.FAIL
    elif ratio >= cfg.connections.warn:
        status = Status.WARN
    return CheckResult("connections", status, f"{used}/{limit} connections in use ({ratio:.0%})")
