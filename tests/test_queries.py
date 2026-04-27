from fakes import FakeConnection

from pgpulse.checks.queries import LONG_QUERIES_SQL, long_running_queries
from pgpulse.config import Config
from pgpulse.result import Status


def row(pid, seconds):
    return {"pid": pid, "usename": "app", "seconds": seconds, "query": "select 1"}


def run(*rows):
    return long_running_queries(FakeConnection({LONG_QUERIES_SQL: list(rows)}), Config())


def test_no_active_queries_is_ok():
    assert run().status is Status.OK


def test_short_queries_are_ignored():
    assert run(row(1, 2.0), row(2, 59.0)).status is Status.OK


def test_query_past_warn_threshold_warns():
    result = run(row(1, 2.0), row(2, 120.0))
    assert result.status is Status.WARN
    assert len(result.details) == 1
    assert "pid 2" in result.details[0]


def test_query_past_fail_threshold_fails():
    assert run(row(1, 600.0)).status is Status.FAIL
