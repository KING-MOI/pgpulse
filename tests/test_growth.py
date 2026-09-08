import json

import pytest
from fakes import FakeConnection

from pgpulse.checks.growth import TABLE_SIZES_SQL, table_growth
from pgpulse.config import Config
from pgpulse.result import Status

DAY = 86400
GB = 1024**3


def sizes(now, **tables):
    return [{"database": "app", "now": now, "name": name, "bytes": size} for name, size in tables.items()]


def run(tmp_path, rows, **limits):
    cfg = Config.model_validate({"table_growth": {"state_file": str(tmp_path / "state.json"), **limits}})
    return table_growth(FakeConnection({TABLE_SIZES_SQL: rows}), cfg)


def test_without_state_file_the_check_is_skipped():
    assert table_growth(FakeConnection(), Config()).status is Status.SKIP


def test_first_run_saves_a_snapshot(tmp_path):
    result = run(tmp_path, sizes(0, orders=GB))
    assert result.status is Status.SKIP
    assert json.loads((tmp_path / "state.json").read_text()) == {"app": {"taken": 0, "sizes": {"orders": GB}}}


@pytest.mark.parametrize(
    ("grown", "expected"),
    [(0, Status.OK), (GB // 2, Status.OK), (2 * GB, Status.WARN), (20 * GB, Status.FAIL)],
)
def test_growth_per_day_is_graded(tmp_path, grown, expected):
    run(tmp_path, sizes(0, orders=GB))
    result = run(tmp_path, sizes(2 * DAY, orders=GB + 2 * grown))
    assert result.status is expected


def test_recent_snapshot_is_kept_until_min_hours_pass(tmp_path):
    run(tmp_path, sizes(0, orders=GB))
    assert run(tmp_path, sizes(600, orders=50 * GB)).status is Status.SKIP
    result = run(tmp_path, sizes(DAY, orders=3 * GB))
    assert result.details == ["orders: +2,048.0 MB per day"]


def test_new_tables_are_not_judged(tmp_path):
    run(tmp_path, sizes(0, orders=GB))
    assert run(tmp_path, sizes(DAY, orders=GB, events=50 * GB)).status is Status.OK


def test_databases_keep_separate_snapshots(tmp_path):
    run(tmp_path, sizes(0, orders=GB))
    other = [r | {"database": "billing"} for r in sizes(DAY, orders=50 * GB)]
    assert run(tmp_path, other).status is Status.SKIP
    assert set(json.loads((tmp_path / "state.json").read_text())) == {"app", "billing"}
