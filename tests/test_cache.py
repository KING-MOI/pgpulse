from fakes import FakeConnection

from pgpulse.checks.cache import CACHE_HIT_SQL, cache_hit_ratio
from pgpulse.config import Config
from pgpulse.result import Status


def run(hit, read):
    conn = FakeConnection({CACHE_HIT_SQL: [{"hit": hit, "read": read}]})
    return cache_hit_ratio(conn, Config())


def test_healthy_ratio_is_ok():
    assert run(9990.0, 10.0).status is Status.OK


def test_ratio_between_thresholds_warns():
    assert run(970.0, 30.0).status is Status.WARN


def test_low_ratio_fails():
    assert run(500.0, 500.0).status is Status.FAIL


def test_summary_shows_percentage():
    assert "99.90%" in run(9990.0, 10.0).summary
