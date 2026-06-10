from fakes import FakeConnection

from pgpulse.checks.sequences import SEQUENCES_SQL, sequence_exhaustion
from pgpulse.config import Config
from pgpulse.result import Status

INT_MAX = 2_147_483_647


def seq(last, increment=1, start=1, min_value=1, max_value=INT_MAX):
    return {
        "schemaname": "public",
        "sequencename": "orders_id_seq",
        "start_value": start,
        "last_value": last,
        "min_value": min_value,
        "max_value": max_value,
        "increment_by": increment,
    }


def run(*rows):
    return sequence_exhaustion(FakeConnection({SEQUENCES_SQL: list(rows)}), Config())


def test_fresh_sequence_is_ok():
    assert run(seq(1000)).status is Status.OK


def test_mostly_used_sequence_warns():
    result = run(seq(1_700_000_000))
    assert result.status is Status.WARN
    assert result.details == ["public.orders_id_seq: 79.2% of the way to 2,147,483,647"]


def test_nearly_exhausted_sequence_fails():
    assert run(seq(2_100_000_000)).status is Status.FAIL


def test_descending_sequence_measures_toward_min_value():
    result = run(seq(-96, increment=-1, start=-1, min_value=-100, max_value=-1))
    assert result.status is Status.FAIL
    assert result.details == ["public.orders_id_seq: 96.0% of the way to -100"]
