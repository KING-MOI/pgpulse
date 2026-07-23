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

    data = json.loads(to_json([CheckResult("bloat", Status.WARN, "1 bloated", ["public.a"])], "app on db1"))
    assert data["server"] == "app on db1"
    assert data["status"] == "warn"
    assert data["checks"] == [
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


def test_report_shows_check_duration():
    text = output([CheckResult("bloat", Status.OK, "fine", seconds=0.0123)])
    assert "12ms" in text


def test_quiet_hides_passing_checks_but_keeps_the_tally():
    console = Console(record=True, width=120, color_system=None)
    render(
        [CheckResult("good", Status.OK, "fine"), CheckResult("bad", Status.WARN, "meh")], console, quiet=True
    )
    text = console.export_text()
    assert "good" not in text and "bad" in text
    assert text.strip().splitlines()[-1] == "1 ok, 1 warn"


def test_quiet_with_everything_passing_prints_only_the_tally():
    console = Console(record=True, width=120, color_system=None)
    render([CheckResult("good", Status.OK, "fine")], console, quiet=True)
    assert console.export_text().strip().splitlines() == ["pgpulse", "1 ok"]


def test_markdown_table_and_collapsed_details():
    from pgpulse.report import to_markdown

    text = to_markdown(
        [
            CheckResult("cache_hit", Status.OK, "99%"),
            CheckResult("bloat", Status.FAIL, "1 bloated", ["public.a"]),
        ],
        "app on db1",
    )
    lines = text.splitlines()
    assert lines[0] == "### pgpulse: app on db1"
    assert "| 🔴 | `bloat` | 1 bloated |" in lines
    assert "- public.a" in lines


def test_markdown_escapes_query_text():
    from pgpulse.report import to_markdown

    text = to_markdown([CheckResult("long_queries", Status.WARN, "a | b", ["pid 1: select a<b>c || 'x'"])])
    assert "| a &#124; b |" in text
    assert "- pid 1: select a&lt;b&gt;c || &#x27;x&#x27;" in text
