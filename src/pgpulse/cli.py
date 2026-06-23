from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from pgpulse.checks import REGISTRY
from pgpulse.config import Config, load
from pgpulse.db import Connection, PsycopgConnection
from pgpulse.report import render, to_json
from pgpulse.result import Status
from pgpulse.runner import run_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pgpulse", description="Health checks for Postgres.")
    parser.add_argument(
        "--dsn",
        default=os.environ.get("PGPULSE_DSN", ""),
        help="libpq connection string or URI (default: $PGPULSE_DSN, then libpq PG* variables)",
    )
    parser.add_argument(
        "-c",
        "--check",
        action="append",
        choices=sorted(REGISTRY),
        metavar="NAME",
        help="run only this check (repeatable)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        action="append",
        default=[],
        choices=sorted(REGISTRY),
        metavar="NAME",
        help="skip this check (repeatable)",
    )
    parser.add_argument("--format", choices=["table", "json"], default="table", help="output format")
    parser.add_argument(
        "--fail-on",
        choices=["warn", "fail"],
        default="fail",
        help="lowest status that makes the exit code non-zero",
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
    try:
        cfg = load(args.config) if args.config else Config()
    except (OSError, ValueError) as exc:
        Console(stderr=True).print(f"[bold red]bad config:[/] {exc}")
        return 2
    if args.dsn:
        cfg.dsn = args.dsn
    names = [n for n in args.check or REGISTRY if n not in args.exclude]
    if not names:
        Console(stderr=True).print("[bold red]no checks selected[/]")
        return 2
    try:
        conn = connect(cfg.dsn or "")
    except ConnectionError as exc:
        Console(stderr=True).print(f"[bold red]cannot connect:[/] {exc}")
        return 3
    try:
        results = run_checks(conn, cfg, names)
    finally:
        conn.close()
    if args.format == "json":
        print(to_json(results))
    else:
        render(results, console)
    worst = max((r.status for r in results), default=Status.OK)
    threshold = Status.WARN if args.fail_on == "warn" else Status.FAIL
    return 1 if worst >= threshold else 0


if __name__ == "__main__":
    sys.exit(main())
