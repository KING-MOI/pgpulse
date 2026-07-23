from __future__ import annotations

import html
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


def render(results: list[CheckResult], console: Console, title: str = "pgpulse", quiet: bool = False) -> None:
    console.print(f"[bold]{title}[/]")
    table = Table()
    table.add_column("status")
    table.add_column("check")
    table.add_column("summary")
    table.add_column("time", justify="right", style="dim")
    for r in results:
        if quiet and r.status <= Status.OK:
            continue
        table.add_row(
            f"[{STYLES[r.status]}]{r.status.name}[/]", r.name, r.summary, f"{r.seconds * 1000:.0f}ms"
        )
    if table.row_count:
        console.print(table)
    for r in results:
        for line in r.details:
            console.print(f"  [{STYLES[r.status]}]{r.name}[/] {line}")
    counts = Counter(r.status for r in results)
    console.print(", ".join(f"[{STYLES[s]}]{counts[s]} {s.name.lower()}[/]" for s in Status if counts[s]))


def worst(results: list[CheckResult]) -> Status:
    return max((r.status for r in results), default=Status.OK)


def to_json(results: list[CheckResult], server: str = "") -> str:
    return json.dumps(
        {
            "server": server,
            "status": worst(results).name.lower(),
            "checks": [
                asdict(r) | {"status": r.status.name.lower(), "seconds": round(r.seconds, 4)} for r in results
            ],
        },
        indent=2,
    )


ICONS = {Status.SKIP: "⚪", Status.OK: "🟢", Status.WARN: "🟡", Status.FAIL: "🔴", Status.ERROR: "🟣"}


def to_markdown(results: list[CheckResult], server: str = "") -> str:
    lines = [
        f"### pgpulse: {server}" if server else "### pgpulse",
        "",
        "| | check | summary |",
        "|---|---|---|",
    ]
    lines += [
        f"| {ICONS[r.status]} | `{r.name}` | {html.escape(r.summary).replace('|', '&#124;')} |"
        for r in results
    ]
    for r in results:
        if r.details:
            lines += ["", f"<details><summary>{r.name}</summary>", ""]
            lines += [f"- {html.escape(line)}" for line in r.details]
            lines += ["", "</details>"]
    return "\n".join(lines)
