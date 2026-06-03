from fakes import FakeConnection

from pgpulse.checks.replication import REPLICATION_LAG_SQL, replication_lag
from pgpulse.config import Config
from pgpulse.result import Status


def standby(name, seconds):
    return {"application_name": name, "client": "10.0.0.2", "seconds": seconds}


def run(*rows):
    return replication_lag(FakeConnection({REPLICATION_LAG_SQL: list(rows)}), Config())


def test_no_standbys_is_ok():
    assert run().summary == "no standbys attached"


def test_caught_up_standby_reports_null_lag_as_zero():
    result = run(standby("replica1", None))
    assert result.status is Status.OK
    assert result.details == ["replica1 (10.0.0.2): 0.0s behind"]


def test_lagging_standby_warns():
    assert run(standby("a", 1.0), standby("b", 45.0)).status is Status.WARN


def test_far_behind_standby_fails():
    result = run(standby("a", 600.0), standby("b", 45.0))
    assert result.status is Status.FAIL
    assert result.summary == "2 standbys, worst lag 600.0s"
