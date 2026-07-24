import os

import pytest

from pgpulse.checks import REGISTRY
from pgpulse.config import Config
from pgpulse.db import PsycopgConnection
from pgpulse.result import Status
from pgpulse.runner import run_checks

DSN = os.environ.get("PGPULSE_TEST_DSN")

pytestmark = pytest.mark.skipif(not DSN, reason="set PGPULSE_TEST_DSN to run against a real server")


@pytest.fixture
def conn():
    conn = PsycopgConnection(DSN)
    yield conn
    conn.close()


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_check_query_runs_on_this_server(conn, name):
    [result] = run_checks(conn, Config(), [name])
    assert result.status is not Status.ERROR, result.summary
