from fakes import FakeConnection

from pgpulse.checks.replication import REPLICATION_LAG_SQL, replication_lag
from pgpulse.config import Config
from pgpulse.db import RECOVERY_SQL
from pgpulse.result import Status


def standby(name, seconds):
    return {"application_name": name, "client": "10.0.0.2", "seconds": seconds}


def run(*rows):
    responses = {RECOVERY_SQL: [{"in_recovery": False}], REPLICATION_LAG_SQL: list(rows)}
    return replication_lag(FakeConnection(responses), Config())


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


GB = 1024**3


def slot(name, active, retained):
    return {
        "slot_name": name,
        "slot_type": "logical",
        "active": active,
        "retained_bytes": retained,
        "retained": "x",
    }


def run_slots(*rows):
    from pgpulse.checks.replication import SLOTS_SQL, replication_slots

    return replication_slots(FakeConnection({SLOTS_SQL: list(rows)}), Config())


def test_active_slot_with_little_wal_is_ok():
    result = run_slots(slot("cdc", True, 1024))
    assert result.status is Status.OK
    assert result.details == []


def test_inactive_slot_warns():
    result = run_slots(slot("cdc", False, 1024))
    assert result.status is Status.WARN
    assert "inactive" in result.details[0]


def test_slot_holding_too_much_wal_fails():
    assert run_slots(slot("cdc", True, 20 * GB)).status is Status.FAIL


def test_standby_reports_its_own_replay_lag():
    from pgpulse.checks.replication import STANDBY_LAG_SQL

    conn = FakeConnection({RECOVERY_SQL: [{"in_recovery": True}], STANDBY_LAG_SQL: [{"seconds": 90.0}]})
    result = replication_lag(conn, Config())
    assert result.status is Status.WARN
    assert result.details == ["this standby (local): 90.0s behind"]
