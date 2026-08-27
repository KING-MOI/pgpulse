import pytest
from fakes import FakeConnection

from pgpulse.checks.queries import LONG_TRANSACTIONS_SQL, long_transactions
from pgpulse.config import Config
from pgpulse.result import Status


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
