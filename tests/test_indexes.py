from fakes import FakeConnection

from pgpulse.checks.indexes import UNUSED_INDEXES_SQL, unused_indexes
from pgpulse.config import Config
from pgpulse.result import Status

MB = 1024 * 1024


def idx(name, size):
    return {
        "schemaname": "public",
        "relname": "orders",
        "indexrelname": name,
        "size_bytes": size,
        "size": f"{size // MB} MB",
    }


def run(*rows):
    return unused_indexes(FakeConnection({UNUSED_INDEXES_SQL: list(rows)}), Config())


def test_no_unused_indexes_is_ok():
    assert run().status is Status.OK


def test_tiny_unused_indexes_are_ignored():
    assert run(idx("orders_tiny", 8192)).status is Status.OK


def test_large_unused_index_warns():
    result = run(idx("orders_big", 50 * MB), idx("orders_tiny", 8192))
    assert result.status is Status.WARN
    assert result.details == ["public.orders_big on orders (50 MB)"]


def test_invalid_indexes_fail():
    from pgpulse.checks.indexes import INVALID_INDEXES_SQL, invalid_indexes

    ok = invalid_indexes(FakeConnection({INVALID_INDEXES_SQL: []}), Config())
    assert ok.status is Status.OK
    bad = invalid_indexes(
        FakeConnection({INVALID_INDEXES_SQL: [{"schemaname": "public", "indexrelname": "orders_ccnew"}]}),
        Config(),
    )
    assert bad.status is Status.FAIL
    assert bad.details == ["public.orders_ccnew"]


def test_duplicate_indexes_warn():
    from pgpulse.checks.indexes import DUPLICATE_INDEXES_SQL, duplicate_indexes

    rows = [{"schemaname": "public", "relname": "orders", "indexes": ["orders_a", "orders_a_copy"]}]
    result = duplicate_indexes(FakeConnection({DUPLICATE_INDEXES_SQL: rows}), Config())
    assert result.status is Status.WARN
    assert result.summary == "1 set of duplicate indexes"
    assert result.details == ["public.orders: orders_a, orders_a_copy"]


def scans(seq, idx):
    return {"schemaname": "public", "relname": "orders", "seq_scan": seq, "idx_scan": idx, "rows": 50_000}


def run_usage(*rows):
    from pgpulse.checks.indexes import SEQ_SCANS_SQL, index_usage

    return index_usage(FakeConnection({SEQ_SCANS_SQL: list(rows)}), Config())


def test_indexed_tables_are_ok():
    assert run_usage(scans(1, 999)).status is Status.OK


def test_seq_scan_heavy_table_warns():
    result = run_usage(scans(90, 10))
    assert result.status is Status.WARN
    assert result.details == ["public.orders: 10% index scans over 50,000 rows"]
