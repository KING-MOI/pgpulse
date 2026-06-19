from fakes import FakeConnection

from pgpulse.checks.schema import NO_PRIMARY_KEY_SQL, missing_primary_keys
from pgpulse.config import Config
from pgpulse.result import Status


def test_tables_with_keys_are_ok():
    assert missing_primary_keys(FakeConnection({NO_PRIMARY_KEY_SQL: []}), Config()).status is Status.OK


def test_keyless_tables_warn():
    rows = [{"schemaname": "public", "relname": "audit_log"}]
    result = missing_primary_keys(FakeConnection({NO_PRIMARY_KEY_SQL: rows}), Config())
    assert result.status is Status.WARN
    assert result.details == ["public.audit_log"]
