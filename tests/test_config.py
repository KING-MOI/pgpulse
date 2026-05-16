from pgpulse.config import Config, load


def test_defaults_are_sane():
    cfg = Config()
    assert cfg.cache_hit.fail < cfg.cache_hit.warn
    assert cfg.connections.warn < cfg.connections.fail


def test_load_overrides_thresholds(tmp_path):
    path = tmp_path / "pgpulse.toml"
    path.write_text('dsn = "postgresql:///app"\n\n[cache_hit]\nwarn = 0.9\n')
    cfg = load(path)
    assert cfg.dsn == "postgresql:///app"
    assert cfg.cache_hit.warn == 0.9
    assert cfg.cache_hit.fail == 0.95


def test_unknown_keys_are_rejected(tmp_path):
    import pytest
    from pydantic import ValidationError

    path = tmp_path / "pgpulse.toml"
    path.write_text("[cache_hit]\nwran = 0.9\n")
    with pytest.raises(ValidationError, match="wran"):
        load(path)
