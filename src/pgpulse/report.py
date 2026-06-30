from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict

from rich.console import Console
from rich.table import Table

from pgpulse.result import CheckResult, Status

STYLES = {
    Status.SKIP: "dim",
    Status.OK: "bold green",
    Status.WARN: "bold yellow",
    Status.FAIL: "bold red",
    Status.ERROR: "bold magenta",
}


def render(results: list[CheckResult], console: Console) -> None:
    table = Table(title="pgpulse")
    table.add_column("status")
    table.add_column("check")
    table.add_column("summary")
    table.add_column("time", justify="right", style="dim")
    for r in results:
        table.add_row(
            f"[{STYLES[r.status]}]{r.status.name}[/]", r.name, r.summary, f"{r.seconds * 1000:.0f}ms"
        )
    console.print(table)
    for r in results:
        for line in r.details:
            console.print(f"  [{STYLES[r.status]}]{r.name}[/] {line}")
    counts = Counter(r.status for r in results)
    console.print(", ".join(f"[{STYLES[s]}]{counts[s]} {s.name.lower()}[/]" for s in Status if counts[s]))


def to_json(results: list[CheckResult]) -> str:
    return json.dumps([asdict(r) | {"status": r.status.name.lower()} for r in results], indent=2)
