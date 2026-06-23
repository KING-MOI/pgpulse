from fakes import FakeConnection

from pgpulse.checks.cache import CACHE_HIT_SQL
from pgpulse.config import Config
from pgpulse.result import Status
from pgpulse.runner import run_checks


def test_runs_only_selected_checks():
    conn = FakeConnection({CACHE_HIT_SQL: [{"hit": 99.0, "read": 1.0}]})
    results = run_checks(conn, Config(), ["cache_hit"])
    assert [r.name for r in results] == ["cache_hit"]
    assert conn.queries == [CACHE_HIT_SQL]


def test_crashing_check_becomes_error_result():
    results = run_checks(FakeConnection(), Config(), ["cache_hit", "connections"])
    assert [r.status for r in results] == [Status.ERROR, Status.ERROR]
    assert results[0].summary.startswith("AssertionError")


def test_every_check_passes_against_a_healthy_database():
    from fakes import healthy

    results = run_checks(FakeConnection(healthy()), Config())
    assert {r.name: r.status for r in results if r.status is not Status.OK} == {}


def test_empty_selection_runs_nothing():
    assert run_checks(FakeConnection(), Config(), []) == []
