from rich.console import Console

from pgpulse.report import render
from pgpulse.result import CheckResult, Status


def output(results):
    console = Console(record=True, width=120, color_system=None)
    render(results, console)
    return console.export_text()


def test_report_lists_every_check():
    text = output([CheckResult("cache_hit", Status.OK, "fine"), CheckResult("bloat", Status.FAIL, "bad")])
    assert "cache_hit" in text and "OK" in text
    assert "bloat" in text and "FAIL" in text


def test_report_prints_details():
    text = output([CheckResult("bloat", Status.WARN, "1 bloated", ["public.a: 30% dead tuples"])])
    assert "public.a: 30% dead tuples" in text
