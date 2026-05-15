from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from pgpulse.checks import REGISTRY
from pgpulse.config import Config, load
from pgpulse.db import Connection, PsycopgConnection
from pgpulse.report import render
from pgpulse.result import Status
from pgpulse.runner import run_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pgpulse", description="Health checks for Postgres.")
    parser.add_argument("--dsn", default="", help="libpq connection string or URI")
    parser.add_argument(
        "-c", "--check", action="append", choices=sorted(REGISTRY), help="run only this check (repeatable)"
    )
    parser.add_argument("--config", type=Path, help="path to a pgpulse.toml file")
    parser.add_argument("--list-checks", action="store_true", help="list available checks and exit")
    return parser


def main(argv: list[str] | None = None, connect: Callable[[str], Connection] = PsycopgConnection) -> int:
    args = build_parser().parse_args(argv)
    console = Console()
    if args.list_checks:
        for name, fn in REGISTRY.items():
            console.print(f"[bold]{name}[/]  {fn.__doc__ or ''}")
        return 0
    cfg = load(args.config) if args.config else Config()
    if args.dsn:
        cfg.dsn = args.dsn
    try:
        conn = connect(cfg.dsn or "")
    except ConnectionError as exc:
        Console(stderr=True).print(f"[bold red]cannot connect:[/] {exc}")
        return 3
    try:
        results = run_checks(conn, cfg, args.check)
    finally:
        conn.close()
    render(results, console)
    worst = max((r.status for r in results), default=Status.OK)
    return 1 if worst >= Status.FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
