from fakes import FakeConnection

from pgpulse.checks.bloat import DEAD_TUPLES_SQL, table_bloat
from pgpulse.config import Config
from pgpulse.result import Status


def tbl(name, live, dead):
    return {"schemaname": "public", "relname": name, "live": live, "dead": dead}


def run(*rows):
    return table_bloat(FakeConnection({DEAD_TUPLES_SQL: list(rows)}), Config())


def test_clean_tables_are_ok():
    assert run(tbl("a", 100_000, 10)).status is Status.OK


def test_small_tables_are_skipped():
    assert run(tbl("tiny", 10, 90)).status is Status.OK


def test_moderate_bloat_warns():
    result = run(tbl("a", 70_000, 30_000))
    assert result.status is Status.WARN
    assert result.details == ["public.a: 30% dead tuples"]


def test_worst_table_decides_status():
    result = run(tbl("a", 70_000, 30_000), tbl("b", 20_000, 80_000))
    assert result.status is Status.FAIL
    assert len(result.details) == 2
