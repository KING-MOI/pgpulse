import pytest
from fakes import FakeConnection

from pgpulse.checks.connections import CONNECTIONS_SQL, connection_saturation
from pgpulse.config import Config
from pgpulse.result import Status


@pytest.mark.parametrize(
    ("used", "expected"),
    [(10, Status.OK), (85, Status.WARN), (97, Status.FAIL), (100, Status.FAIL)],
)
def test_saturation_levels(used, expected):
    conn = FakeConnection({CONNECTIONS_SQL: [{"used": used, "max": 100}]})
    assert connection_saturation(conn, Config()).status is expected


def test_summary_counts():
    conn = FakeConnection({CONNECTIONS_SQL: [{"used": 12, "max": 100}]})
    assert connection_saturation(conn, Config()).summary.startswith("12/100")
