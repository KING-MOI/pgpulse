from fakes import FakeConnection

from pgpulse.checks.settings import SETTINGS_SQL, risky_settings
from pgpulse.config import Config
from pgpulse.result import Status


def run(**settings):
    rows = [{"name": k, "setting": v} for k, v in settings.items()]
    return risky_settings(FakeConnection({SETTINGS_SQL: rows}), Config())


def test_safe_settings_are_ok():
    assert run(fsync="on", full_page_writes="on", autovacuum="on", track_counts="on").status is Status.OK


def test_autovacuum_off_warns():
    result = run(fsync="on", autovacuum="off")
    assert result.status is Status.WARN
    assert result.details == ["autovacuum = off: dead tuples and xid age only shrink by hand"]


def test_fsync_off_fails():
    assert run(fsync="off", autovacuum="off").status is Status.FAIL
