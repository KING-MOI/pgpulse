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


def test_json_output_is_machine_readable():
    import json

    from pgpulse.report import to_json

    data = json.loads(to_json([CheckResult("bloat", Status.WARN, "1 bloated", ["public.a"])]))
    assert data == [
        {"name": "bloat", "status": "warn", "summary": "1 bloated", "details": ["public.a"], "seconds": 0.0}
    ]


def test_report_ends_with_status_counts():
    text = output(
        [CheckResult("a", Status.OK, ""), CheckResult("b", Status.OK, ""), CheckResult("c", Status.FAIL, "")]
    )
    assert text.strip().splitlines()[-1] == "2 ok, 1 fail"


def test_skipped_checks_are_dimmed_not_failed():
    text = output([CheckResult("a", Status.SKIP, "not on standby")])
    assert "SKIP" in text
    assert text.strip().splitlines()[-1] == "1 skip"
