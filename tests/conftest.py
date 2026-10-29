"""Keep tests away from the real ~/.cache/tc002 state files."""

import pytest

from tc002.runtime import events, hold


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(hold, "PATH", tmp_path / "hold.json")
    monkeypatch.setattr(events, "PATH", tmp_path / "event.json")
