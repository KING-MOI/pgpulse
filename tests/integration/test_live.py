import os

import pytest

from pgpulse.checks import REGISTRY
from pgpulse.config import Config
from pgpulse.db import PsycopgConnection
from pgpulse.result import Status
from pgpulse.runner import run_checks

DSN = os.environ.get("PGPULSE_TEST_DSN")

pytestmark = pytest.mark.skipif(not DSN, reason="set PGPULSE_TEST_DSN to run against a real server")


@pytest.fixture
def conn():
    conn = PsycopgConnection(DSN)
    yield conn
    conn.close()


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_check_query_runs_on_this_server(conn, name):
    [result] = run_checks(conn, Config(), [name])
    assert result.status is not Status.ERROR, result.summary


@pytest.fixture
def scratch():
    import psycopg

    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute("DROP SCHEMA IF EXISTS pgpulse_test CASCADE")
        admin.execute("CREATE SCHEMA pgpulse_test")
        yield admin
        admin.execute("DROP SCHEMA pgpulse_test CASCADE")


def test_sequence_feeding_an_int_column_is_flagged(conn, scratch):
    scratch.execute("CREATE TABLE pgpulse_test.legacy (id int)")
    scratch.execute("CREATE SEQUENCE pgpulse_test.legacy_id_seq AS bigint OWNED BY pgpulse_test.legacy.id")
    scratch.execute("SELECT setval('pgpulse_test.legacy_id_seq', 2000000000)")
    [result] = run_checks(conn, Config(), ["sequences"])
    assert any(d.startswith("pgpulse_test.legacy_id_seq: 93.1%") for d in result.details), result.details


def test_failed_concurrent_index_is_flagged(conn, scratch):
    import psycopg

    scratch.execute("CREATE TABLE pgpulse_test.dupes (v text)")
    scratch.execute("INSERT INTO pgpulse_test.dupes VALUES ('a'), ('a')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        scratch.execute("CREATE UNIQUE INDEX CONCURRENTLY dupes_v ON pgpulse_test.dupes (v)")
    [result] = run_checks(conn, Config(), ["invalid_indexes"])
    assert result.status is Status.FAIL
    assert "pgpulse_test.dupes_v" in result.details


def test_duplicate_index_is_flagged(conn, scratch):
    scratch.execute("CREATE TABLE pgpulse_test.orders (id int, v text)")
    scratch.execute("CREATE INDEX orders_v ON pgpulse_test.orders (v)")
    scratch.execute("CREATE INDEX orders_v_again ON pgpulse_test.orders (v)")
    scratch.execute("CREATE INDEX orders_v_partial ON pgpulse_test.orders (v) WHERE id > 0")
    [result] = run_checks(conn, Config(), ["duplicate_indexes"])
    assert "pgpulse_test.orders: orders_v, orders_v_again" in result.details


def test_cycling_sequence_is_not_flagged(conn, scratch):
    scratch.execute("CREATE SEQUENCE pgpulse_test.ring AS int CYCLE")
    scratch.execute("SELECT setval('pgpulse_test.ring', 2100000000)")
    [result] = run_checks(conn, Config(), ["sequences"])
    assert not any(d.startswith("pgpulse_test.ring") for d in result.details), result.details


def test_exclusion_constraint_index_is_not_unused(conn, scratch):
    scratch.execute("CREATE TABLE pgpulse_test.booking (r int4range, EXCLUDE USING gist (r WITH &&))")
    cfg = Config.model_validate({"unused_indexes": {"min_size_bytes": 0}})
    [result] = run_checks(conn, cfg, ["unused_indexes"])
    assert not any(d.startswith("pgpulse_test.booking") for d in result.details), result.details


@pytest.mark.parametrize(
    ("index", "flagged"),
    [
        (None, True),
        ("(a, b)", False),
        ("(b, a)", False),
        ("(a, b, c)", False),
        ("(a, c, b)", True),
        ("(a)", True),
    ],
)
def test_foreign_key_index_coverage(conn, scratch, index, flagged):
    scratch.execute("CREATE TABLE pgpulse_test.parent (a int, b int, PRIMARY KEY (a, b))")
    scratch.execute(
        "CREATE TABLE pgpulse_test.child (a int, b int, c int, FOREIGN KEY (a, b) REFERENCES pgpulse_test.parent)"
    )
    if index:
        scratch.execute(f"CREATE INDEX ON pgpulse_test.child {index}")
    [result] = run_checks(conn, Config(), ["unindexed_foreign_keys"])
    assert ("pgpulse_test.child: child_a_b_fkey" in result.details) is flagged, result.details


def test_not_valid_constraint_is_flagged_until_validated(conn, scratch):
    scratch.execute("CREATE TABLE pgpulse_test.prices (v int)")
    scratch.execute("ALTER TABLE pgpulse_test.prices ADD CONSTRAINT positive CHECK (v > 0) NOT VALID")
    [result] = run_checks(conn, Config(), ["not_valid_constraints"])
    assert "pgpulse_test.prices: positive" in result.details
    scratch.execute("ALTER TABLE pgpulse_test.prices VALIDATE CONSTRAINT positive")
    [result] = run_checks(conn, Config(), ["not_valid_constraints"])
    assert "pgpulse_test.prices: positive" not in result.details


def test_outdated_extension_is_flagged(conn, scratch):
    scratch.execute("CREATE EXTENSION hstore VERSION '1.4' SCHEMA pgpulse_test")
    try:
        [result] = run_checks(conn, Config(), ["extension_updates"])
        assert any(d.startswith("hstore 1.4 -> ") for d in result.details), result.details
    finally:
        scratch.execute("DROP EXTENSION hstore")
