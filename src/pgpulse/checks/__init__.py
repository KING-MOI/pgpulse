from __future__ import annotations

import importlib
import pkgutil
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


for _module in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_module.name}")
