from __future__ import annotations

from collections.abc import Iterable

from pgpulse.checks import REGISTRY
from pgpulse.config import Config
from pgpulse.db import Connection
from pgpulse.result import CheckResult, Status


def run_checks(conn: Connection, cfg: Config, names: Iterable[str] | None = None) -> list[CheckResult]:
    results = []
    for name in REGISTRY if names is None else names:
        try:
            results.append(REGISTRY[name](conn, cfg))
        except Exception as exc:
            results.append(CheckResult(name, Status.ERROR, f"{type(exc).__name__}: {exc}"))
    return results
