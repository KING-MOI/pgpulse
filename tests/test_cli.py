from fakes import FakeConnection, healthy

from pgpulse.checks.connections import CONNECTIONS_SQL
from pgpulse.cli import main


def connector(responses):
    conns = []

    def connect(dsn):
        conn = FakeConnection(responses)
        conn.dsn = dsn
        conns.append(conn)
        return conn

    connect.conns = conns
    return connect


def test_healthy_database_exits_zero(capsys):
    assert main([], connect=connector(healthy())) == 0
    assert "cache_hit" in capsys.readouterr().out


def test_failing_check_exits_one():
    responses = healthy()
    responses[CONNECTIONS_SQL] = [{"used": 100, "max": 100}]
    assert main([], connect=connector(responses)) == 1


def test_connection_is_closed_and_gets_dsn():
    connect = connector(healthy())
    main(["--dsn", "postgresql://localhost/app"], connect=connect)
    assert connect.conns[0].closed
    assert connect.conns[0].dsn == "postgresql://localhost/app"


def test_connection_failure_exits_three(capsys):
    def refuse(dsn):
        raise ConnectionError("connection refused")

    assert main([], connect=refuse) == 3
    assert "connection refused" in capsys.readouterr().out
