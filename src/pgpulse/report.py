from __future__ import annotations

from rich.console import Console
from rich.table import Table

from pgpulse.result import CheckResult, Status

STYLES = {
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
    for r in results:
        table.add_row(f"[{STYLES[r.status]}]{r.status.name}[/]", r.name, r.summary)
    console.print(table)
    for r in results:
        for line in r.details:
            console.print(f"  [{STYLES[r.status]}]{r.name}[/] {line}")
