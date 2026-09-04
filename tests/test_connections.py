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


def test_remote_sessions_without_ssl_warn():
    from pgpulse.checks.connections import UNENCRYPTED_SQL, unencrypted_connections

    rows = [
        {"usename": "app", "client": "10.0.0.7", "sessions": 3},
        {"usename": "etl", "client": "10.0.0.9", "sessions": 1},
    ]
    result = unencrypted_connections(FakeConnection({UNENCRYPTED_SQL: rows}), Config())
    assert result.status is Status.WARN
    assert result.summary == "4 remote sessions without ssl"
    assert result.details == ["app from 10.0.0.7: 3 sessions", "etl from 10.0.0.9: 1 session"]
