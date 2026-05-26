from __future__ import annotations

from collections.abc import Callable

from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult

CheckFn = Callable[[Connection, Config], CheckResult]

REGISTRY: dict[str, CheckFn] = {}


def check(name: str) -> Callable[[CheckFn], CheckFn]:
    def register(fn: CheckFn) -> CheckFn:
        REGISTRY[name] = fn
        return fn

    return register


from pgpulse.checks import bloat, cache, connections, indexes, locks, queries  # noqa: E402, F401
