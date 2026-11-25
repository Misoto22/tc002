"""The application layer: the use cases the CLI, web API and MCP server share."""

import pytest

from tc002 import cli
from tc002.app import App, ClockUnreachable, InvalidRequest, InvalidSettings, NotConfigured
from tc002.clock.device import DeviceError
from tc002.host import launchd
from tc002.runtime import night

TOML = """\
[screens]
enabled = ["claude", "sys"]
[device]
keep_builtins = ["clock"]
[rotation]
slots = [{ screen = "claude", seconds = 30 }]
"""


class Clock:
    """Just enough of a TC002 for the use cases below."""

    base = "http://clock"

    def __init__(self, fail=False):
        self.fail, self.calls, self.installed = fail, [], []

    def _maybe_fail(self):
        if self.fail:
            raise DeviceError("http://clock/getBase: timed out")

    def base_info(self):
        self._maybe_fail()
        return {"appVer": "2.0.4"}

    def info(self):
        return {"base": self.base_info(), "config": {}}

    def apps(self):
        self._maybe_fail()
        return list(self.installed)

    def push(self, app, payload):
        self._maybe_fail()
        self.calls.append(("push", app))
        self.installed.append(app)

    def remove(self, app):
        self.calls.append(("remove", app))

    def switch_custom(self, app):
        self.calls.append(("switch", app))

    def switch_builtin(self, category, index):
        self.calls.append(("builtin", category, index))


@pytest.fixture
def no_service(monkeypatch):
    monkeypatch.setattr(launchd, "status", lambda: "not installed")
    monkeypatch.setattr(launchd, "restart", lambda: False)


def app_with(tmp_path, clock=None, host="192.0.2.1"):
    cfg = tmp_path / "tc002.toml"
    cfg.write_text(TOML)
    return App(host, cfg, tmp_path / "state", device=(lambda: clock) if clock else None)


def test_no_clock_is_not_configured(tmp_path):
    app = app_with(tmp_path, host=None)
    with pytest.raises(NotConfigured):
        app.show("claude")
    assert app.clock_state() == {"online": False, "error": "no clock configured"}


def test_show_checks_names_and_switches(tmp_path):
    clock = Clock()
    app = app_with(tmp_path, clock)
    assert app.show(builtin="clock") == {"ok": True, "builtin": "clock"}
    assert clock.calls == [("builtin", "tools", 1)]
    for bad in ({"screen": "nope"}, {"builtin": "nope"}, {}):
        with pytest.raises(InvalidRequest):
            app.show(**bad)


def test_device_errors_become_clock_unreachable(tmp_path):
    app = app_with(tmp_path, Clock(fail=True))
    with pytest.raises(ClockUnreachable) as caught:
        app.custom_apps()
    assert caught.value.status is None and "timed out" in caught.value.detail
    assert isinstance(caught.value.__cause__, DeviceError)


def test_no_app_method_lets_a_lower_level_error_through(tmp_path):
    bad = tmp_path / "tc002.toml"
    bad.write_text("[screens\n")
    app = App("192.0.2.1", bad, device=lambda: Clock(fail=True))
    with pytest.raises(InvalidSettings) as caught:
        app.overview()
    assert caught.value.title == "Invalid tc002.toml" and str(bad) in caught.value.detail


def test_status_and_now_showing_work_offline(tmp_path, no_service):
    app = app_with(tmp_path, Clock(fail=True))
    status = app.status()
    assert status["clock"]["online"] is False and "timed out" in status["clock"]["error"]
    assert status["service"] == "not installed" and status["night"]["dark"] is False
    shown = app.now_showing()
    assert shown["driver"].startswith("rotation") and shown["rotation"][0]["screen"] == "claude"


def test_screens_list_says_what_is_enabled_and_in_rotation(tmp_path):
    listed = app_with(tmp_path).screens()
    by_name = {s["name"]: s for s in listed["screens"]}
    assert by_name["claude"] == {
        "name": "claude",
        "enabled": True,
        "rotationSeconds": 30,
        "networked": False,
    }
    assert by_name["fire"]["enabled"] is False
    assert {"name": "clock", "category": "tools", "kept": True, "rotationSeconds": None} in (
        listed["builtins"]
    )


def test_save_config_rejects_bad_settings_and_leaves_the_file(tmp_path, no_service):
    app = app_with(tmp_path, host=None)
    before = app.config_path.read_text()
    with pytest.raises(InvalidSettings) as caught:
        app.save_config({"display": {"volume": 99}})
    assert caught.value.errors and app.config_path.read_text() == before
    saved = app.save_config({"display": {"volume": 3}})
    assert saved["applied"] is False and app.settings().display["volume"] == 3


def test_set_display_merges_into_tc002_toml(tmp_path, no_service):
    app = app_with(tmp_path, host=None)
    app.set_display({"volume": 2})
    app.set_display({"showWeek": True})
    assert app.settings().display == {"volume": 2, "showWeek": True}
    with pytest.raises(InvalidRequest):
        app.set_display({})


def test_focus_minutes_are_checked(tmp_path):
    app = app_with(tmp_path)
    done = app.focus_start(5)
    assert done["running"] and done["minutes"] == 5 and done["screenEnabled"] is False
    assert app.focus_now()["phase"] == "focus"
    for bad in (0, 181, True, "5"):
        with pytest.raises(InvalidSettings):
            app.focus_start(bad)
    assert app.focus_stop() == {"running": False} and app.focus_now() is None


def test_screen_off_and_on(tmp_path):
    clock = Clock()
    app = app_with(tmp_path, clock)
    assert app.screen_off()["dark"] is True
    assert ("switch", night.APP) in clock.calls
    assert app.screen_on()["dark"] is False and ("remove", night.APP) in clock.calls


def test_start_message_refuses_empty_text_and_unknown_kinds(tmp_path):
    app = app_with(tmp_path, Clock())
    with pytest.raises(InvalidRequest):
        app.start_message("   ")
    with pytest.raises(InvalidRequest):
        app.start_message("hi", "alert", "nope")


def test_cli_reports_application_errors_in_one_line(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "tc002.toml"
    cfg.write_text(TOML)
    with pytest.raises(SystemExit) as caught:
        cli.main(["--config", str(cfg), "--host", "192.0.2.1", "focus", "start", "--minutes", "0"])
    assert "1 to 180" in str(caught.value)


def test_cli_doctor_prints_the_app_checks(tmp_path, monkeypatch, capsys, no_service):
    cfg = tmp_path / "tc002.toml"
    cfg.write_text(TOML)
    assert cli.main(["--config", str(cfg), "doctor"]) == 1  # no clock configured
    out = capsys.readouterr().out
    assert "[FAIL] clock: no host" in out and "[warn] service: not installed" in out


def test_no_attribute_hides_a_use_case(tmp_path):
    app = App("192.0.2.1", tmp_path / "x.toml", preview_dir=tmp_path, device=Clock)
    app.agents()  # creates the readers it keeps
    hidden = [name for name in vars(app) if callable(getattr(App, name, None))]
    assert not hidden, f"instance attributes named like App methods: {hidden}"
