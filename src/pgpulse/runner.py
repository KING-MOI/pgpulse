from __future__ import annotations

import time
from collections.abc import Iterable

from pgpulse.checks import REGISTRY
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status


def run_checks(conn: Connection, cfg: Config, names: Iterable[str] | None = None) -> list[CheckResult]:
    results = []
    for name in REGISTRY if names is None else names:
        started = time.perf_counter()
        try:
            result = REGISTRY[name](conn, cfg)
        except Exception as exc:
            result = CheckResult(name, Status.ERROR, f"{type(exc).__name__}: {exc}")
        result.seconds = time.perf_counter() - started
        results.append(result)
    return results
