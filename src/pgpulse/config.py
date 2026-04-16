from __future__ import annotations

from pydantic import BaseModel


class CacheHitConfig(BaseModel):
    warn: float = 0.99
    fail: float = 0.95


class Config(BaseModel):
    dsn: str | None = None
    cache_hit: CacheHitConfig = CacheHitConfig()
