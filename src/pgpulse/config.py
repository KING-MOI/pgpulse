from __future__ import annotations

from pydantic import BaseModel


class CacheHitConfig(BaseModel):
    warn: float = 0.99
    fail: float = 0.95


class ConnectionsConfig(BaseModel):
    warn: float = 0.8
    fail: float = 0.95


class LongQueriesConfig(BaseModel):
    warn_seconds: float = 60
    fail_seconds: float = 300


class UnusedIndexesConfig(BaseModel):
    min_size_bytes: int = 1024 * 1024


class BloatConfig(BaseModel):
    warn: float = 0.2
    fail: float = 0.5
    min_rows: int = 10_000


class Config(BaseModel):
    dsn: str | None = None
    cache_hit: CacheHitConfig = CacheHitConfig()
    connections: ConnectionsConfig = ConnectionsConfig()
    long_queries: LongQueriesConfig = LongQueriesConfig()
    unused_indexes: UnusedIndexesConfig = UnusedIndexesConfig()
    bloat: BloatConfig = BloatConfig()
