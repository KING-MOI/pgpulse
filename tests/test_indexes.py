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
