from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

CACHE_HIT_SQL = """
SELECT sum(heap_blks_hit)::float AS hit, sum(heap_blks_read)::float AS read
FROM pg_statio_user_tables
"""


@check("cache_hit")
def cache_hit_ratio(conn: Connection, cfg: Config) -> CheckResult:
    """Share of table block reads served from shared buffers."""
    row = conn.fetchall(CACHE_HIT_SQL)[0]
    hit, read = row["hit"] or 0.0, row["read"] or 0.0
    if hit + read < cfg.cache_hit.min_blocks:
        return CheckResult(
            "cache_hit", Status.OK, f"only {hit + read:,.0f} block reads so far, too few to judge"
        )
    ratio = hit / (hit + read)
    status = Status.OK
    if ratio < cfg.cache_hit.fail:
        status = Status.FAIL
    elif ratio < cfg.cache_hit.warn:
        status = Status.WARN
    return CheckResult("cache_hit", status, f"table cache hit ratio {ratio:.2%}")
