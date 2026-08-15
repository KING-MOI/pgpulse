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


def prepared(seconds):
    return {"gid": "tx-1", "owner": "app", "database": "shop", "seconds": seconds}


def run_prepared(*rows):
    from pgpulse.checks.locks import PREPARED_SQL, prepared_transactions

    return prepared_transactions(FakeConnection({PREPARED_SQL: list(rows)}), Config())


def test_fresh_prepared_transactions_are_fine():
    assert run_prepared(prepared(5.0)).status is Status.OK


def test_lingering_prepared_transaction_warns():
    result = run_prepared(prepared(600.0))
    assert result.status is Status.WARN
    assert result.details == ["tx-1 (app on shop) prepared 600s ago"]


def test_abandoned_prepared_transaction_fails():
    assert run_prepared(prepared(86_400.0)).status is Status.FAIL
