"""`tc002 mcp`: a whole stdio session, and the tools' contract with the application layer."""

import io
import json
import subprocess
import sys

import pytest

from tc002.app import App
from tc002.host import launchd
from tc002.mcp import server
from tc002.mcp.tools import TOOLS

TOML = """\
[screens]
enabled = ["claude", "sys"]
[rotation]
slots = [{ screen = "claude", seconds = 30 }]
"""


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(launchd, "status", lambda: "not installed")
    monkeypatch.setattr(launchd, "restart", lambda: False)
    cfg = tmp_path / "tc002.toml"
    cfg.write_text(TOML)
    return App(None, cfg, tmp_path / "state")  # no clock: nothing reaches the LAN


def session(app, *messages):
    """Run the server over in-memory stdio; returns the replies by id."""
    lines = [m if isinstance(m, str) else json.dumps(m) for m in messages]
    out = io.StringIO()
    server.serve(app, io.StringIO("\n".join(lines) + "\n"), out)
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    return {r["id"]: r for r in replies}


def rpc(mid, method, params=None):
    msg = {"jsonrpc": "2.0", "id": mid, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def call(mid, name, arguments=None):
    return rpc(mid, "tools/call", {"name": name, "arguments": arguments or {}})


INIT = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def test_handshake_then_tools_list(app):
    got = session(app, INIT, INITIALIZED, rpc(2, "tools/list"), rpc(3, "ping"))
    assert set(got) == {1, 2, 3}  # the notification gets no reply
    init = got[1]["result"]
    assert init["protocolVersion"] == "2025-06-18"
    assert init["serverInfo"]["name"] == "tc002" and "tools" in init["capabilities"]
    tools = {t["name"]: t for t in got[2]["result"]["tools"]}
    assert set(tools) == set(TOOLS) and got[3]["result"] == {}
    for tool in tools.values():
        assert tool["inputSchema"]["type"] == "object" and len(tool["description"]) > 40


def test_unknown_protocol_version_gets_the_latest(app):
    got = session(app, rpc(1, "initialize", {"protocolVersion": "1999-01-01"}))
    assert got[1]["result"]["protocolVersion"] == server.PROTOCOL_VERSIONS[0]


def test_read_only_and_changing_tools_are_marked_apart(app):
    hints = {name: t.describe()["annotations"] for name, t in TOOLS.items()}
    read_only = {n for n, h in hints.items() if h["readOnlyHint"]}
    assert read_only == {
        "get_status",
        "list_screens",
        "now_showing",
        "get_config",
        "get_clock_settings",
        "run_checks",
    }
    assert all(not hints[n]["destructiveHint"] for n in read_only)
    destructive = {n for n, h in hints.items() if h["destructiveHint"]}
    assert {"set_display", "save_config", "apply_layout", "restore_layout"} == destructive


def test_read_only_calls_return_structured_content(app):
    got = session(app, INIT, call(2, "list_screens"), call(3, "get_status"))
    screens = got[2]["result"]
    assert screens["isError"] is False
    names = [s["name"] for s in screens["structuredContent"]["screens"]]
    assert "claude" in names
    assert json.loads(screens["content"][0]["text"]) == screens["structuredContent"]
    status = got[3]["result"]["structuredContent"]
    assert status["clock"] == {"host": None, "online": False, "error": "no clock configured"}


def test_errors_come_back_as_tool_errors_the_model_can_read(app):
    got = session(
        app,
        call(1, "show_screen", {"screen": "claude"}),  # no clock configured
        call(2, "show_screen", {"screen": "nope"}),  # not in the enum
        call(3, "focus_start", {"minutes": 500}),
        call(4, "set_display", {"display": {"volume": 99}}),
        call(5, "get_status", {"extra": 1}),
    )
    for mid in got:
        assert got[mid]["result"]["isError"] is True, mid
    text = {mid: got[mid]["result"]["content"][0]["text"] for mid in got}
    assert text[1].startswith("No clock configured")
    assert "must be one of" in text[2] and "at most 180" in text[3] and "at most 6" in text[4]
    assert "unknown keys" in text[5]


def test_changing_tools_reach_the_application_layer(app):
    got = session(
        app,
        call(1, "set_display", {"display": {"volume": 2}}),
        call(2, "focus_start", {"minutes": 3}),
        call(3, "focus_stop"),
    )
    assert got[1]["result"]["structuredContent"]["saved"] == str(app.config_path)
    assert app.settings().display == {"volume": 2}
    assert got[2]["result"]["structuredContent"]["minutes"] == 3
    assert got[3]["result"]["structuredContent"] == {"running": False}


def test_protocol_errors(app):
    got = session(
        app,
        "{not json",
        rpc(2, "nope/method"),
        call(3, "no_such_tool"),
        {"jsonrpc": "1.0", "id": 4, "method": "ping"},
    )
    assert got[None]["error"]["code"] == server.PARSE_ERROR
    assert got[2]["error"]["code"] == server.METHOD_NOT_FOUND
    assert got[3]["error"]["code"] == server.INVALID_PARAMS
    assert got[4]["error"]["code"] == server.INVALID_REQUEST


def test_resources_read_like_their_tools(app):
    got = session(
        app, rpc(1, "resources/list"), rpc(2, "resources/read", {"uri": "tc002://config"})
    )
    uris = {r["uri"] for r in got[1]["result"]["resources"]}
    assert "tc002://status" in uris
    (content,) = got[2]["result"]["contents"]
    assert json.loads(content["text"])["data"]["rotation"]["slots"][0]["screen"] == "claude"


def test_stray_prints_go_to_stderr_not_the_protocol_stream(app, monkeypatch, capsys):
    monkeypatch.setattr(App, "status", lambda self: print("noise") or {"ok": True})
    got = session(app, call(1, "get_status"))
    assert got[1]["result"]["structuredContent"] == {"ok": True}
    assert "noise" in capsys.readouterr().err


def test_tc002_mcp_over_a_real_pipe(tmp_path):
    cfg = tmp_path / "tc002.toml"
    cfg.write_text(TOML)
    lines = [INIT, INITIALIZED, rpc(2, "tools/list"), call(3, "list_screens")]
    proc = subprocess.run(
        [sys.executable, "-m", "tc002", "--config", str(cfg), "mcp"],
        input="".join(json.dumps(m) + "\n" for m in lines),
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "TC002_HOST": "", "HOME": str(tmp_path)},
    )
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [r["id"] for r in replies] == [1, 2, 3], proc.stderr
    assert replies[2]["result"]["isError"] is False


def test_save_config_refuses_a_file_changed_since_it_was_read(app):
    got = session(app, call(1, "get_config"))
    read = got[1]["result"]["structuredContent"]
    app.config_path.write_text(app.config_path.read_text() + "\n# edited by hand\n")
    args = {"data": read["data"], "expected_version": read["version"]}
    got = session(app, call(2, "save_config", args))
    assert got[2]["result"]["isError"] is True
    assert got[2]["result"]["content"][0]["text"].startswith("Config changed")
    assert "edited by hand" in app.config_path.read_text()


def test_set_display_takes_auto_time_zone(app):
    tool = TOOLS["set_display"].describe()
    zone = tool["inputSchema"]["properties"]["display"]["properties"]["timezone"]
    assert "auto" in zone["enum"] and "follows this Mac" in zone["description"]
    got = session(app, call(1, "set_display", {"display": {"timezone": "auto"}}))
    assert got[1]["result"]["isError"] is False
    assert app.settings().display["timezone"] == "auto"
