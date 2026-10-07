import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    monkeypatch.delenv("PGPULSE_DSN", raising=False)
    monkeypatch.delenv("PGPULSE_CONFIG", raising=False)
