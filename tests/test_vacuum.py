from fakes import FakeConnection

from pgpulse.checks.vacuum import XID_AGE_SQL, xid_wraparound
from pgpulse.config import Config
from pgpulse.result import Status


def run(*rows):
    return xid_wraparound(FakeConnection({XID_AGE_SQL: list(rows)}), Config())


def test_young_databases_are_ok():
    result = run({"datname": "app", "age": 200_000_000})
    assert result.status is Status.OK
    assert result.details == []


def test_old_database_warns():
    result = run({"datname": "app", "age": 1_200_000_000}, {"datname": "postgres", "age": 100})
    assert result.status is Status.WARN
    assert result.details == ["app: 1,200,000,000 (55.9%)"]


def test_near_wraparound_fails():
    assert run({"datname": "app", "age": 1_800_000_000}).status is Status.FAIL
