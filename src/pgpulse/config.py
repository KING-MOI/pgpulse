from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Ratio = Annotated[float, Field(ge=0, le=1)]


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CacheHitConfig(Section):
    warn: Ratio = 0.99
    fail: Ratio = 0.95

    @model_validator(mode="after")
    def _ordered(self) -> CacheHitConfig:
        if self.fail > self.warn:
            raise ValueError("cache_hit.fail must not be above cache_hit.warn")
        return self


class Ascending(Section):
    @model_validator(mode="after")
    def _ordered(self) -> Ascending:
        fields = [f for f in type(self).model_fields if f.startswith("warn")]
        for warn in fields:
            fail = warn.replace("warn", "fail")
            if getattr(self, warn) > getattr(self, fail):
                raise ValueError(f"{fail} must not be below {warn}")
        return self


class ConnectionsConfig(Ascending):
    warn: Ratio = 0.8
    fail: Ratio = 0.95


class LongQueriesConfig(Ascending):
    warn_seconds: float = 60
    fail_seconds: float = 300


class IdleInTransactionConfig(Ascending):
    warn_seconds: float = 30
    fail_seconds: float = 300


class BlockingLocksConfig(Ascending):
    warn_seconds: float = 10
    fail_seconds: float = 120


class XidWraparoundConfig(Ascending):
    warn: Ratio = 0.5
    fail: Ratio = 0.75


class VacuumAgeConfig(Section):
    warn_days: float = 7
    fail_days: float = 30
    min_dead_rows: int = 10_000


class ReplicationLagConfig(Ascending):
    warn_seconds: float = 30
    fail_seconds: float = 300


class ReplicationSlotsConfig(Section):
    warn_bytes: int = 1024**3
    fail_bytes: int = 10 * 1024**3


class SequencesConfig(Ascending):
    warn: Ratio = 0.75
    fail: Ratio = 0.9


class DeadlocksConfig(Section):
    warn_per_day: float = 1
    fail_per_day: float = 20


class TempFilesConfig(Section):
    warn_bytes_per_day: int = 10 * 1024**3


class RollbacksConfig(Ascending):
    warn: Ratio = 0.05
    fail: Ratio = 0.2


class CheckpointsConfig(Section):
    warn: Ratio = 0.3
    min_checkpoints: int = 10


class UnusedIndexesConfig(Section):
    min_size_bytes: int = 1024 * 1024


class IndexUsageConfig(Section):
    warn: Ratio = 0.5
    min_rows: int = 10_000


class BloatConfig(Ascending):
    warn: Ratio = 0.2
    fail: Ratio = 0.5
    min_rows: int = 10_000


class Config(Section):
    dsn: str | None = None
    exclude: list[str] = []
    cache_hit: CacheHitConfig = CacheHitConfig()
    connections: ConnectionsConfig = ConnectionsConfig()
    long_queries: LongQueriesConfig = LongQueriesConfig()
    idle_in_transaction: IdleInTransactionConfig = IdleInTransactionConfig()
    blocking_locks: BlockingLocksConfig = BlockingLocksConfig()
    unused_indexes: UnusedIndexesConfig = UnusedIndexesConfig()
    index_usage: IndexUsageConfig = IndexUsageConfig()
    bloat: BloatConfig = BloatConfig()
    xid_wraparound: XidWraparoundConfig = XidWraparoundConfig()
    vacuum_age: VacuumAgeConfig = VacuumAgeConfig()
    replication_lag: ReplicationLagConfig = ReplicationLagConfig()
    replication_slots: ReplicationSlotsConfig = ReplicationSlotsConfig()
    sequences: SequencesConfig = SequencesConfig()
    deadlocks: DeadlocksConfig = DeadlocksConfig()
    temp_files: TempFilesConfig = TempFilesConfig()
    rollbacks: RollbacksConfig = RollbacksConfig()
    checkpoints: CheckpointsConfig = CheckpointsConfig()


def load(path: Path) -> Config:
    with path.open("rb") as fh:
        return Config.model_validate(tomllib.load(fh))
