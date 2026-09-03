import pytest
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


def stale(days, dead=50_000):
    return {"schemaname": "public", "relname": "events", "dead": dead, "days": days}


def run_stale(*rows):
    from pgpulse.checks.vacuum import STALE_VACUUM_SQL, vacuum_age

    return vacuum_age(FakeConnection({STALE_VACUUM_SQL: list(rows)}), Config())


def test_recently_vacuumed_tables_are_ok():
    assert run_stale(stale(1.0)).status is Status.OK


def test_week_old_vacuum_warns():
    result = run_stale(stale(10.0))
    assert result.status is Status.WARN
    assert result.details == ["public.events: last vacuumed 10 days ago, 50,000 dead tuples"]


def test_never_vacuumed_fails():
    result = run_stale(stale(None))
    assert result.status is Status.FAIL
    assert "never vacuumed" in result.details[0]


def test_dead_row_floor_is_passed_to_the_query():
    from pgpulse.checks.vacuum import STALE_VACUUM_SQL, vacuum_age

    conn = FakeConnection({STALE_VACUUM_SQL: []})
    cfg = Config.model_validate({"vacuum_age": {"min_dead_rows": 42}})
    vacuum_age(conn, cfg)
    assert conn.params == [(42,)]


def run_xmin(*rows):
    from pgpulse.checks.vacuum import XMIN_HOLDERS_SQL, xmin_horizon

    return xmin_horizon(FakeConnection({XMIN_HOLDERS_SQL: list(rows)}), Config())


def test_young_xmin_is_ok():
    result = run_xmin({"holder": "session 42", "age": 1_000})
    assert result.status is Status.OK
    assert result.details == []


def test_old_xmin_names_the_holder():
    result = run_xmin(
        {"holder": "replication slot cdc", "age": 50_000_000}, {"holder": "session 7", "age": 10}
    )
    assert result.status is Status.WARN
    assert result.details == ["replication slot cdc: 50,000,000 transactions old"]


def test_ancient_xmin_fails():
    assert run_xmin({"holder": "prepared transaction tx1", "age": 300_000_000}).status is Status.FAIL


def run_stats(*rows):
    from pgpulse.checks.vacuum import STALE_STATS_SQL, stale_stats

    return stale_stats(FakeConnection({STALE_STATS_SQL: list(rows)}), Config())


def stats_row(live, modified, never=False):
    return {"schemaname": "public", "relname": "orders", "live": live, "modified": modified, "never": never}


def test_fresh_stats_are_ok():
    assert run_stats(stats_row(100_000, 1_000)).status is Status.OK


def test_heavily_modified_table_warns():
    result = run_stats(stats_row(100_000, 80_000))
    assert result.status is Status.WARN
    assert result.details == ["public.orders: 80% of rows changed since last analyze"]


def test_never_analyzed_table_warns():
    assert run_stats(stats_row(50_000, 0, never=True)).details == ["public.orders: never analyzed"]


def test_multixact_age_has_its_own_check():
    from pgpulse.checks.vacuum import MXID_AGE_SQL, mxid_wraparound

    conn = FakeConnection({MXID_AGE_SQL: [{"datname": "app", "age": 1_700_000_000}]})
    result = mxid_wraparound(conn, Config())
    assert result.status is Status.FAIL
    assert result.summary == "app has used 79.2% of multixact space"


@pytest.mark.parametrize(("busy", "expected"), [(0, Status.OK), (2, Status.OK), (3, Status.WARN)])
def test_autovacuum_worker_saturation(busy, expected):
    from pgpulse.checks.vacuum import AUTOVACUUM_WORKERS_SQL, autovacuum_workers

    conn = FakeConnection({AUTOVACUUM_WORKERS_SQL: [{"busy": busy, "max": 3}]})
    result = autovacuum_workers(conn, Config())
    assert result.status is expected
    assert result.summary == f"{busy}/3 autovacuum workers busy"
