from fakes import FakeConnection

from pgpulse.checks.activity import DATABASE_STATS_SQL, deadlocks
from pgpulse.config import Config
from pgpulse.result import Status


def stats(**overrides):
    row = {
        "deadlocks": 0,
        "temp_files": 0,
        "temp_bytes": 0,
        "xact_commit": 1000,
        "xact_rollback": 0,
        "days": 10.0,
    }
    return FakeConnection({DATABASE_STATS_SQL: [row | overrides]})


def test_no_deadlocks_is_ok():
    assert deadlocks(stats(), Config()).status is Status.OK


def test_occasional_deadlocks_warn():
    result = deadlocks(stats(deadlocks=15), Config())
    assert result.status is Status.WARN
    assert result.summary == "15 deadlocks, 1.5 per day"


def test_frequent_deadlocks_fail():
    assert deadlocks(stats(deadlocks=500), Config()).status is Status.FAIL
