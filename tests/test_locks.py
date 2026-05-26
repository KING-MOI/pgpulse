from fakes import FakeConnection

from pgpulse.checks.locks import BLOCKED_SQL, blocking_locks
from pgpulse.config import Config
from pgpulse.result import Status


def waiter(pid, seconds, blockers=(1,)):
    return {"pid": pid, "blocked_by": list(blockers), "seconds": seconds, "query": "update t set x = 1"}


def run(*rows):
    return blocking_locks(FakeConnection({BLOCKED_SQL: list(rows)}), Config())


def test_no_waiters_is_ok():
    assert run().status is Status.OK


def test_brief_waits_are_ignored():
    assert run(waiter(2, 1.0)).status is Status.OK


def test_long_wait_warns_and_names_blockers():
    result = run(waiter(2, 30.0, blockers=(7, 9)))
    assert result.status is Status.WARN
    assert "on 7, 9" in result.details[0]


def test_very_long_wait_fails():
    assert run(waiter(2, 300.0)).status is Status.FAIL
