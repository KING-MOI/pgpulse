from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from rich.console import Console

from pgpulse.config import Config
from pgpulse.db import Connection, PsycopgConnection
from pgpulse.report import render
from pgpulse.result import Status
from pgpulse.runner import run_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pgpulse", description="Health checks for Postgres.")
    parser.add_argument("--dsn", default="", help="libpq connection string or URI")
    return parser


def main(argv: list[str] | None = None, connect: Callable[[str], Connection] = PsycopgConnection) -> int:
    args = build_parser().parse_args(argv)
    cfg = Config(dsn=args.dsn)
    conn = connect(cfg.dsn or "")
    try:
        results = run_checks(conn, cfg)
    finally:
        conn.close()
    render(results, Console())
    worst = max((r.status for r in results), default=Status.OK)
    return 1 if worst >= Status.FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
