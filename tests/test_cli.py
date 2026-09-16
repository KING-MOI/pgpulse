from fakes import FakeConnection, healthy

from pgpulse.checks.connections import CONNECTIONS_SQL
from pgpulse.cli import main


def connector(responses):
    conns = []

    def connect(cfg):
        conn = FakeConnection(responses)
        conn.dsn = cfg.dsn
        conns.append(conn)
        return conn

    connect.conns = conns
    return connect


def test_healthy_database_exits_zero(capsys):
    assert main([], connect=connector(healthy())) == 0
    out = capsys.readouterr().out
    assert "cache_hit" in out
    assert "app on 10.0.0.5 (PostgreSQL 16.4, primary)" in out


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
    def refuse(cfg):
        raise ConnectionError("connection refused")

    assert main([], connect=refuse) == 3
    assert "connection refused" in capsys.readouterr().err


def test_check_flag_limits_checks(capsys):
    connect = connector(healthy())
    main(["--check", "cache_hit"], connect=connect)
    out = capsys.readouterr().out
    assert "cache_hit" in out
    assert "bloat" not in out


def test_list_checks_does_not_connect(capsys):
    def explode(cfg):
        raise AssertionError("should not connect")

    assert main(["--list-checks"], connect=explode) == 0
    out = capsys.readouterr().out
    assert "cache_hit" in out and "shared buffers" in out


def test_config_file_supplies_dsn_and_flag_overrides_it(tmp_path):
    path = tmp_path / "pgpulse.toml"
    path.write_text('dsn = "from-file"\n')
    connect = connector(healthy())
    main(["--config", str(path)], connect=connect)
    main(["--config", str(path), "--dsn", "from-flag"], connect=connect)
    assert [c.dsn for c in connect.conns] == ["from-file", "from-flag"]


def test_missing_config_file_exits_two(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "nope.toml")], connect=connector(healthy())) == 2
    assert "bad config" in capsys.readouterr().err


def test_invalid_config_exits_two(tmp_path):
    path = tmp_path / "pgpulse.toml"
    path.write_text("[bloat]\nwarn = 'lots'\n")
    assert main(["--config", str(path)], connect=connector(healthy())) == 2


def test_dsn_falls_back_to_environment(monkeypatch):
    monkeypatch.setenv("PGPULSE_DSN", "from-env")
    connect = connector(healthy())
    main([], connect=connect)
    assert connect.conns[0].dsn == "from-env"


def test_json_format(capsys):
    import json

    main(["--format", "json"], connect=connector(healthy()))
    data = json.loads(capsys.readouterr().out)
    assert {d["name"] for d in data["checks"]} >= {"cache_hit", "connections"}


def test_fail_on_warn_turns_warnings_into_failures():
    responses = healthy()
    responses[CONNECTIONS_SQL] = [{"used": 85, "max": 100}]
    assert main([], connect=connector(responses)) == 0
    assert main(["--fail-on", "warn"], connect=connector(responses)) == 1


def test_exclude_flag_drops_checks(capsys):
    main(["--format", "json", "-x", "bloat", "-x", "cache_hit"], connect=connector(healthy()))
    import json

    names = {d["name"] for d in json.loads(capsys.readouterr().out)["checks"]}
    assert "bloat" not in names and "cache_hit" not in names
    assert "connections" in names


def test_excluding_everything_is_a_usage_error(capsys):
    connect = connector(healthy())
    assert main(["-c", "bloat", "-x", "bloat"], connect=connect) == 2
    assert connect.conns == []
    assert "no checks selected" in capsys.readouterr().err


def test_config_can_exclude_checks(tmp_path, capsys):
    import json

    path = tmp_path / "pgpulse.toml"
    path.write_text('exclude = ["primary_keys"]\n')
    main(["--config", str(path), "--format", "json"], connect=connector(healthy()))
    assert "primary_keys" not in {d["name"] for d in json.loads(capsys.readouterr().out)["checks"]}


def test_config_exclude_rejects_unknown_checks(tmp_path, capsys):
    path = tmp_path / "pgpulse.toml"
    path.write_text('exclude = ["primary_key"]\n')
    assert main(["--config", str(path)], connect=connector(healthy())) == 2
    assert "primary_key" in capsys.readouterr().err


def test_malformed_dsn_exits_two(capsys):
    assert main(["--dsn", "garbage"]) == 2
    assert "invalid dsn" in capsys.readouterr().err


def test_repeated_check_flag_runs_once(capsys):
    import json

    main(["--format", "json", "-c", "bloat", "-c", "bloat"], connect=connector(healthy()))
    assert [d["name"] for d in json.loads(capsys.readouterr().out)["checks"]] == ["bloat"]


def test_quiet_markdown_lists_only_problems(capsys):
    responses = healthy()
    responses[CONNECTIONS_SQL] = [{"used": 85, "max": 100}]
    main(["--format", "markdown", "--quiet"], connect=connector(responses))
    out = capsys.readouterr().out
    assert "`connections`" in out
    assert "`cache_hit`" not in out


def test_config_sets_fail_on_and_flag_overrides_it(tmp_path):
    path = tmp_path / "pgpulse.toml"
    path.write_text('fail_on = "warn"\n')
    responses = healthy()
    responses[CONNECTIONS_SQL] = [{"used": 85, "max": 100}]
    assert main(["--config", str(path)], connect=connector(responses)) == 1
    assert main(["--config", str(path), "--fail-on", "fail"], connect=connector(responses)) == 0
