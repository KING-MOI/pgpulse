from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection, in_recovery
from pgpulse.result import CheckResult, Status, plural

REPLICATION_LAG_SQL = """
SELECT application_name, coalesce(client_addr::text, 'local') AS client,
       extract(epoch FROM replay_lag)::float AS seconds
FROM pg_stat_replication
"""

STANDBY_LAG_SQL = """
SELECT CASE WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0
            ELSE extract(epoch FROM now() - pg_last_xact_replay_timestamp())::float
       END AS seconds
"""


@check("replication_lag")
def replication_lag(conn: Connection, cfg: Config) -> CheckResult:
    """Replay lag of each standby attached to this primary."""
    limits = cfg.replication_lag
    if in_recovery(conn):
        rows = [{"application_name": "this standby", "client": "local", **conn.fetchall(STANDBY_LAG_SQL)[0]}]
    else:
        rows = conn.fetchall(REPLICATION_LAG_SQL)
    if not rows:
        return CheckResult("replication_lag", Status.OK, "no standbys attached")
    status = Status.OK
    details = []
    for r in rows:
        lag = r["seconds"] or 0.0
        if lag >= limits.fail_seconds:
            status = Status.FAIL
        elif lag >= limits.warn_seconds:
            status = max(status, Status.WARN)
        details.append(f"{r['application_name']} ({r['client']}): {lag:.1f}s behind")
    worst = max(r["seconds"] or 0.0 for r in rows)
    return CheckResult(
        "replication_lag",
        status,
        f"{plural(len(rows), 'standby', 'standbys')}, worst lag {worst:.1f}s",
        details,
    )


SLOTS_SQL = """
WITH pos AS (
    SELECT CASE WHEN pg_is_in_recovery() THEN pg_last_wal_replay_lsn() ELSE pg_current_wal_lsn() END AS lsn
)
SELECT slot_name, slot_type, active,
       pg_wal_lsn_diff(pos.lsn, restart_lsn)::bigint AS retained_bytes,
       pg_size_pretty(pg_wal_lsn_diff(pos.lsn, restart_lsn)) AS retained
FROM pg_replication_slots, pos
"""


@check("replication_slots")
def replication_slots(conn: Connection, cfg: Config) -> CheckResult:
    """Inactive replication slots and the WAL they hold back."""
    limits = cfg.replication_slots
    rows = conn.fetchall(SLOTS_SQL)
    status = Status.OK
    details = []
    for r in rows:
        retained = r["retained_bytes"] or 0
        if retained >= limits.fail_bytes:
            status = Status.FAIL
        elif not r["active"] or retained >= limits.warn_bytes:
            status = max(status, Status.WARN)
        else:
            continue
        state = "active" if r["active"] else "inactive"
        details.append(
            f"{r['slot_name']} ({r['slot_type']}, {state}) retains {r['retained'] or '0 bytes'} of WAL"
        )
    if not rows:
        return CheckResult("replication_slots", Status.OK, "no replication slots")
    return CheckResult(
        "replication_slots", status, plural(len(rows), "slot") + f", {len(details)} need attention", details
    )
