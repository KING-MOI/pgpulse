from fakes import FakeConnection

from pgpulse.checks.sequences import SEQUENCES_SQL, sequence_exhaustion
from pgpulse.config import Config
from pgpulse.result import Status

INT_MAX = 2_147_483_647


def seq(last, increment=1):
    return {
        "schemaname": "public",
        "sequencename": "orders_id_seq",
        "last_value": last,
        "max_value": INT_MAX,
        "increment_by": increment,
    }


def run(*rows):
    return sequence_exhaustion(FakeConnection({SEQUENCES_SQL: list(rows)}), Config())


def test_fresh_sequence_is_ok():
    assert run(seq(1000)).status is Status.OK


def test_mostly_used_sequence_warns():
    result = run(seq(1_700_000_000))
    assert result.status is Status.WARN
    assert result.details == ["public.orders_id_seq: 79.2% of 2,147,483,647 used"]


def test_nearly_exhausted_sequence_fails():
    assert run(seq(2_100_000_000)).status is Status.FAIL
