from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Status(IntEnum):
    SKIP = -1
    OK = 0
    WARN = 1
    FAIL = 2
    ERROR = 3


@dataclass
class CheckResult:
    name: str
    status: Status
    summary: str
    details: list[str] = field(default_factory=list)
    seconds: float = 0.0


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else many or one + 's'}"
