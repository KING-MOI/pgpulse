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


def test_heavy_temp_file_usage_warns():
    from pgpulse.checks.activity import temp_files

    assert temp_files(stats(temp_bytes=1024**3), Config()).status is Status.OK
    result = temp_files(stats(temp_files=40, temp_bytes=200 * 1024**3), Config())
    assert result.status is Status.WARN
    assert result.summary == "40 temp files, 20,480.0 MB per day"


def test_rollback_ratio_levels():
    from pgpulse.checks.activity import rollbacks

    assert rollbacks(stats(xact_commit=990, xact_rollback=10), Config()).status is Status.OK
    assert rollbacks(stats(xact_commit=900, xact_rollback=100), Config()).status is Status.WARN
    assert rollbacks(stats(xact_commit=500, xact_rollback=500), Config()).status is Status.FAIL


def test_rollbacks_with_no_transactions():
    from pgpulse.checks.activity import rollbacks

    result = rollbacks(stats(xact_commit=0, xact_rollback=0), Config())
    assert result.status is Status.OK
