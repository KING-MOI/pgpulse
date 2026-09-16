from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from pgpulse import __version__
from pgpulse.checks import REGISTRY
from pgpulse.config import Config, load
from pgpulse.db import Connection, describe
from pgpulse.db import connect as connect_db
from pgpulse.report import render, to_json, to_markdown, worst
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
    parser.add_argument(
        "--format", choices=["table", "json", "markdown"], default="table", help="output format"
    )
    parser.add_argument(
        "--fail-on",
        choices=["warn", "fail"],
        help="lowest status that makes the exit code non-zero (default: fail_on from config, then fail)",
    )
    parser.add_argument("--config", type=Path, help="path to a pgpulse.toml file")
    parser.add_argument("-q", "--quiet", action="store_true", help="only show checks that need attention")
    parser.add_argument(
        "--no-color", action="store_true", help="disable colored output (NO_COLOR is honored too)"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--list-checks", action="store_true", help="list available checks and exit")
    return parser


def main(argv: list[str] | None = None, connect: Callable[[Config], Connection] = connect_db) -> int:
    args = build_parser().parse_args(argv)
    console = Console(no_color=args.no_color or None)
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
    unknown = sorted(set(cfg.exclude) - set(REGISTRY))
    if unknown:
        Console(stderr=True).print(
            f"[bold red]bad config:[/] unknown checks in exclude: {', '.join(unknown)}"
        )
        return 2
    names = [n for n in dict.fromkeys(args.check or REGISTRY) if n not in args.exclude + cfg.exclude]
    if not names:
        Console(stderr=True).print("[bold red]no checks selected[/]")
        return 2
    try:
        conn = connect(cfg)
    except ConnectionError as exc:
        Console(stderr=True).print(f"[bold red]cannot connect:[/] {exc}")
        return 3
    except ValueError as exc:
        Console(stderr=True).print(f"[bold red]{exc}[/]")
        return 2
    try:
        target = describe(conn)
        results = run_checks(conn, cfg, names)
    finally:
        conn.close()
    if args.format == "json":
        print(to_json(results, target))
    elif args.format == "markdown":
        print(to_markdown([r for r in results if not args.quiet or r.status > Status.OK], target))
    else:
        render(results, console, f"pgpulse: {target}", quiet=args.quiet)
    threshold = Status.WARN if (args.fail_on or cfg.fail_on) == "warn" else Status.FAIL
    return 1 if worst(results) >= threshold else 0


if __name__ == "__main__":
    sys.exit(main())
