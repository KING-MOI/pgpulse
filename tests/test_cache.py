from fakes import FakeConnection

from pgpulse.checks.cache import CACHE_HIT_SQL, cache_hit_ratio
from pgpulse.config import Config
from pgpulse.result import Status


def run(hit, read):
    conn = FakeConnection({CACHE_HIT_SQL: [{"hit": hit, "read": read}]})
    return cache_hit_ratio(conn, Config())


def test_healthy_ratio_is_ok():
    assert run(99_900.0, 100.0).status is Status.OK


def test_ratio_between_thresholds_warns():
    assert run(97_000.0, 3_000.0).status is Status.WARN


def test_low_ratio_fails():
    assert run(50_000.0, 50_000.0).status is Status.FAIL


def test_too_few_reads_are_not_judged():
    result = run(5.0, 5.0)
    assert result.status is Status.OK
    assert result.summary == "only 10 block reads so far, too few to judge"


def test_summary_shows_percentage():
    assert "99.90%" in run(99_900.0, 100.0).summary


def test_empty_stats_do_not_divide_by_zero():
    result = run(None, None)
    assert result.status is Status.OK
    assert "too few to judge" in result.summary


def test_ratio_exactly_at_a_threshold_is_not_below_it():
    assert run(99_000.0, 1_000.0).status is Status.OK
    assert run(95_000.0, 5_000.0).status is Status.WARN


def test_index_cache_hit_uses_its_own_thresholds():
    from pgpulse.checks.cache import INDEX_CACHE_HIT_SQL, index_cache_hit_ratio

    conn = FakeConnection({INDEX_CACHE_HIT_SQL: [{"hit": 90_000.0, "read": 10_000.0}]})
    cfg = Config.model_validate({"index_cache_hit": {"warn": 0.95, "fail": 0.8}})
    result = index_cache_hit_ratio(conn, cfg)
    assert result.status is Status.WARN
    assert result.summary == "index cache hit ratio 90.00%"
