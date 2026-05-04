from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Status(IntEnum):
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
