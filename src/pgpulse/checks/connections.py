from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status, grade, plural

CONNECTIONS_SQL = """
SELECT count(*) AS used,
       current_setting('max_connections')::int
         - current_setting('superuser_reserved_connections')::int
         - coalesce(current_setting('reserved_connections', true)::int, 0) AS max
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


UNENCRYPTED_SQL = """
SELECT a.usename, host(a.client_addr) AS client, count(*) AS sessions
FROM pg_stat_activity a
JOIN pg_stat_ssl s USING (pid)
WHERE a.backend_type = 'client backend' AND NOT s.ssl
  AND a.client_addr IS NOT NULL AND NOT a.client_addr <<= '127.0.0.0/8' AND a.client_addr <> '::1'
GROUP BY 1, 2
ORDER BY sessions DESC, 1, 2
"""


@check("unencrypted_connections")
def unencrypted_connections(conn: Connection, cfg: Config) -> CheckResult:
    """Sessions from other hosts that are not using SSL."""
    rows = conn.fetchall(UNENCRYPTED_SQL)
    if not rows:
        return CheckResult("unencrypted_connections", Status.OK, "remote sessions all use ssl")
    total = sum(r["sessions"] for r in rows)
    details = [f"{r['usename']} from {r['client']}: {plural(r['sessions'], 'session')}" for r in rows]
    return CheckResult(
        "unencrypted_connections", Status.WARN, plural(total, "remote session") + " without ssl", details
    )
