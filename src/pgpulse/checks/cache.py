from __future__ import annotations

from pgpulse.checks import check
from pgpulse.config import CacheHitConfig, Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status

CACHE_HIT_SQL = """
SELECT sum(heap_blks_hit)::float AS hit, sum(heap_blks_read)::float AS read
FROM pg_statio_user_tables
"""

INDEX_CACHE_HIT_SQL = """
SELECT sum(idx_blks_hit)::float AS hit, sum(idx_blks_read)::float AS read
FROM pg_statio_user_indexes
"""


def _hit_ratio(name: str, kind: str, row: dict, limits: CacheHitConfig) -> CheckResult:
    hit, read = row["hit"] or 0.0, row["read"] or 0.0
    if hit + read < limits.min_blocks:
        return CheckResult(name, Status.OK, f"only {hit + read:,.0f} block reads so far, too few to judge")
    ratio = hit / (hit + read)
    status = Status.OK
    if ratio < limits.fail:
        status = Status.FAIL
    elif ratio < limits.warn:
        status = Status.WARN
    return CheckResult(name, status, f"{kind} cache hit ratio {ratio:.2%}")


@check("cache_hit")
def cache_hit_ratio(conn: Connection, cfg: Config) -> CheckResult:
    """Share of table block reads served from shared buffers."""
    return _hit_ratio("cache_hit", "table", conn.fetchall(CACHE_HIT_SQL)[0], cfg.cache_hit)


@check("index_cache_hit")
def index_cache_hit_ratio(conn: Connection, cfg: Config) -> CheckResult:
    """Share of index block reads served from shared buffers."""
    return _hit_ratio("index_cache_hit", "index", conn.fetchall(INDEX_CACHE_HIT_SQL)[0], cfg.index_cache_hit)
