from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CacheHitConfig(Section):
    warn: float = 0.99
    fail: float = 0.95


class ConnectionsConfig(Section):
    warn: float = 0.8
    fail: float = 0.95


class LongQueriesConfig(Section):
    warn_seconds: float = 60
    fail_seconds: float = 300


class UnusedIndexesConfig(Section):
    min_size_bytes: int = 1024 * 1024


class BloatConfig(Section):
    warn: float = 0.2
    fail: float = 0.5
    min_rows: int = 10_000


class Config(Section):
    dsn: str | None = None
    cache_hit: CacheHitConfig = CacheHitConfig()
    connections: ConnectionsConfig = ConnectionsConfig()
    long_queries: LongQueriesConfig = LongQueriesConfig()
    unused_indexes: UnusedIndexesConfig = UnusedIndexesConfig()
    bloat: BloatConfig = BloatConfig()


def load(path: Path) -> Config:
    with path.open("rb") as fh:
        return Config.model_validate(tomllib.load(fh))
