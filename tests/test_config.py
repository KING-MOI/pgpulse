from pgpulse.config import Config, load


def test_defaults_are_sane():
    cfg = Config()
    assert cfg.cache_hit.fail < cfg.cache_hit.warn
    assert cfg.connections.warn < cfg.connections.fail


def test_load_overrides_thresholds(tmp_path):
    path = tmp_path / "pgpulse.toml"
    path.write_text('dsn = "postgresql:///app"\n\n[cache_hit]\nwarn = 0.97\n')
    cfg = load(path)
    assert cfg.dsn == "postgresql:///app"
    assert cfg.cache_hit.warn == 0.97
    assert cfg.cache_hit.fail == 0.95


def test_unknown_keys_are_rejected(tmp_path):
    import pytest
    from pydantic import ValidationError

    path = tmp_path / "pgpulse.toml"
    path.write_text("[cache_hit]\nwran = 0.9\n")
    with pytest.raises(ValidationError, match="wran"):
        load(path)


def test_ratios_must_be_fractions():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Config.model_validate({"cache_hit": {"warn": 99}})


def test_thresholds_must_be_ordered():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="cache_hit.fail"):
        Config.model_validate({"cache_hit": {"warn": 0.9, "fail": 0.95}})
    with pytest.raises(ValidationError, match="fail_seconds"):
        Config.model_validate({"long_queries": {"warn_seconds": 600}})


def test_example_config_matches_defaults():
    from pathlib import Path

    example = load(Path(__file__).parent.parent / "pgpulse.example.toml")
    assert example.model_dump(exclude={"dsn"}) == Config().model_dump(exclude={"dsn"})


def test_example_config_mentions_every_setting():
    import tomllib
    from pathlib import Path

    raw = tomllib.loads((Path(__file__).parent.parent / "pgpulse.example.toml").read_text())
    defaults = Config().model_dump()
    assert raw.keys() == defaults.keys()
    for key, value in defaults.items():
        if isinstance(value, dict):
            assert raw[key].keys() == value.keys(), key
