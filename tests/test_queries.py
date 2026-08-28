import pytest
from fakes import FakeConnection

from pgpulse.checks.queries import (
    LONG_QUERIES_SQL,
    LONG_TRANSACTIONS_SQL,
    long_running_queries,
    long_transactions,
)
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


def test_idle_in_transaction_levels():
    from pgpulse.checks.queries import IDLE_IN_TRANSACTION_SQL, idle_in_transaction

    def run_idle(*rows):
        return idle_in_transaction(FakeConnection({IDLE_IN_TRANSACTION_SQL: list(rows)}), Config())

    assert run_idle(row(1, 5.0)).status is Status.OK
    assert run_idle(row(1, 45.0)).status is Status.WARN
    assert run_idle(row(1, 45.0), row(2, 900.0)).status is Status.FAIL


def txn(seconds, state="idle in transaction"):
    return {"pid": 42, "usename": "app", "state": state, "seconds": seconds, "query": "SELECT 1"}


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(10, Status.OK), (299, Status.OK), (300, Status.WARN), (3599, Status.WARN), (3600, Status.FAIL)],
)
def test_long_transaction_levels(seconds, expected):
    conn = FakeConnection({LONG_TRANSACTIONS_SQL: [txn(seconds)]})
    assert long_transactions(conn, Config()).status is expected


def test_long_transaction_details_name_the_state():
    conn = FakeConnection({LONG_TRANSACTIONS_SQL: [txn(400, state="active"), txn(5)]})
    result = long_transactions(conn, Config())
    assert result.summary == "1 long transaction"
    assert result.details == ["pid 42 (app, active) open 400s: SELECT 1"]
