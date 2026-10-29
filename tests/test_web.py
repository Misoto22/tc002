"""The `tc002 ui` server over real HTTP: pages, API, and its cross-site defences."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from tc002.integrations import launchd
from tc002.web import server

TOML = """\
[screens]
enabled = ["claude", "sys"]
[device]
keep_builtins = ["clock"]
[playlist]
slots = [{ screen = "claude", seconds = 30 }]
[alerts]
takeover = true
"""


@pytest.fixture
def ui(tmp_path, monkeypatch):
    cfg = tmp_path / "tc002.toml"
    cfg.write_text(TOML)
    monkeypatch.setattr(launchd, "restart", lambda: False)
    monkeypatch.setattr(launchd, "status", lambda: "not installed")
    ready = threading.Event()
    box = {}

    def on_ready(url):
        box["url"] = url
        ready.set()

    # host None: the clock is "not configured", so nothing ever reaches the LAN
    t = threading.Thread(target=server.serve, args=(None, cfg, 0, on_ready), daemon=True)
    t.start()
    ready.wait(5)
    page = urllib.request.urlopen(box["url"]).read().decode()
    token = page.split('name="tc002-token" content="')[1].split('"')[0]
    return box["url"].rstrip("/"), token, cfg


def call(url, path, body=None, headers=None):
    req = urllib.request.Request(
        url + path,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET",
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def test_index_embeds_a_token_and_strict_headers(ui):
    url, token, _ = ui
    status, headers, body = call(url, "/")
    assert status == 200 and len(token) > 20 and b"{{TOKEN}}" not in body
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    for asset in ("/js/app.js", "/js/pages/playlist.js", "/css/tokens.css", "/icons.svg"):
        assert call(url, asset)[0] == 200


def test_state_reports_config_and_offline_clock(ui):
    url, _, cfg = ui
    status, _, body = call(url, "/api/state")
    state = json.loads(body)
    assert status == 200
    assert state["config"]["path"] == str(cfg)
    assert state["config"]["data"]["playlist"]["slots"][0]["screen"] == "claude"
    assert state["clock"]["online"] is False
    assert "volume" in state["schema"]["display"]


def test_save_validates_and_writes_toml(ui):
    url, token, cfg = ui
    _, _, body = call(url, "/api/state")
    data = json.loads(body)["config"]["data"]
    data["display"] = {"volume": 3}
    data["playlist"]["slots"].append({"screen": "sys", "seconds": 10})
    status, _, body = call(url, "/api/config", data, {"X-TC002-Token": token})
    assert status == 200, body
    text = cfg.read_text()
    assert "volume = 3" in text and 'screen = "sys"' in text


def test_invalid_save_is_a_422_problem_and_leaves_the_file(ui):
    url, token, cfg = ui
    before = cfg.read_text()
    bad = {"display": {"volume": 99}}
    status, headers, body = call(url, "/api/config", bad, {"X-TC002-Token": token})
    problem = json.loads(body)
    assert status == 422 and headers["Content-Type"] == "application/problem+json"
    assert problem["title"] == "Invalid settings" and problem["errors"]
    assert cfg.read_text() == before


@pytest.mark.parametrize(
    "headers",
    [
        {},  # no token
        {"X-TC002-Token": "guess"},
        {"X-TC002-Token": "{token}", "Origin": "https://evil.example"},
    ],
)
def test_writes_without_the_token_or_from_another_origin_are_refused(ui, headers):
    url, token, cfg = ui
    before = cfg.read_text()
    headers = {k: v.format(token=token) for k, v in headers.items()}
    status, _, _ = call(url, "/api/config", {"display": {"volume": 1}}, headers)
    assert status == 403 and cfg.read_text() == before


def test_foreign_host_header_is_refused(ui):
    url, _, _ = ui
    status, _, _ = call(url, "/api/state", headers={"Host": "attacker.example"})
    assert status == 421


def test_previews_are_gifs_and_unknown_ones_404(ui):
    url, _, _ = ui
    status, headers, body = call(url, "/api/preview/claude-busy.gif")
    assert status == 200 and headers["Content-Type"] == "image/gif" and body[:6] == b"GIF89a"
    assert call(url, "/api/preview/text.gif?text=HI&color=green")[0] == 200
    assert call(url, "/api/preview/nope.gif")[0] == 404


def test_actions_need_a_clock(ui):
    url, token, _ = ui
    status, _, body = call(url, "/api/show", {"screen": "claude"}, {"X-TC002-Token": token})
    assert status == 409 and json.loads(body)["title"] == "No clock configured"


def test_nested_static_paths_cannot_escape(ui):
    url, _, _ = ui
    assert call(url, "/js/../../api.py")[0] == 404
    assert call(url, "/%2e%2e/web/api.py")[0] == 404


def test_font_matches_the_python_renderer(ui):
    from tc002.render import font

    url, _, _ = ui
    status, _, body = call(url, "/api/font")
    assert status == 200 and json.loads(body) == {"big": font.BIG, "small": font.SMALL}


def test_cities_fall_back_offline_and_need_no_token(ui, monkeypatch):
    from tc002.web import cities

    def no_network(url):
        raise OSError("offline")

    monkeypatch.setattr(cities, "_fetch", no_network)
    url, _, _ = ui
    status, _, body = call(url, "/api/cities?q=%E5%A2%A8%E5%B0%94&lang=zh")
    data = json.loads(body)
    assert status == 200 and data["source"] == "offline"
    assert data["results"][0]["name"] == "墨尔本" and data["results"][0]["region"] == "澳大利亚"


def test_live_preview_needs_a_clock_and_validates(ui):
    url, token, _ = ui
    status, _, body = call(
        url, "/api/live", {"data": {"display": {"volume": 99}}}, {"X-TC002-Token": token}
    )
    assert status == 422
    status, _, body = call(url, "/api/live", {"data": {}}, {"X-TC002-Token": token})
    assert status == 409  # no clock configured in the test server
    status, _, body = call(url, "/api/live/stop", {}, {"X-TC002-Token": token})
    assert status == 200 and json.loads(body) == {"changes": []}
