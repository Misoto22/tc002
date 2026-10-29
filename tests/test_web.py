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
[rotation]
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
    for asset in ("/js/app.js", "/js/pages/rotation.js", "/css/tokens.css", "/icons.svg"):
        assert call(url, asset)[0] == 200


def test_state_reports_config_and_offline_clock(ui):
    url, _, cfg = ui
    status, _, body = call(url, "/api/state")
    state = json.loads(body)
    assert status == 200
    assert state["config"]["path"] == str(cfg)
    assert state["config"]["data"]["rotation"]["slots"][0]["screen"] == "claude"
    assert state["clock"]["online"] is False
    assert "volume" in state["schema"]["display"]


def test_save_validates_and_writes_toml(ui):
    url, token, cfg = ui
    _, _, body = call(url, "/api/state")
    data = json.loads(body)["config"]["data"]
    data["display"] = {"volume": 3}
    data["rotation"]["slots"].append({"screen": "sys", "seconds": 10})
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
    status, headers, body = call(url, "/api/preview/claude.gif")
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


def test_led_assets_match_the_python_renderer(ui):
    from tc002.render import font
    from tc002.render.canvas import HEIGHT, WIDTH
    from tc002.render.palette import hex_palette

    url, _, _ = ui
    status, _, body = call(url, "/api/led")
    data = json.loads(body)
    assert status == 200
    assert data == {
        "font": {"big": font.BIG, "small": font.SMALL},
        "palette": hex_palette(),
        "size": {"width": WIDTH, "height": HEIGHT},
    }


def test_quick_settings_write_only_display(ui):
    url, token, cfg = ui
    status, _, body = call(url, "/api/quick", {"display": {"volume": 4}}, {"X-TC002-Token": token})
    assert status == 200, body
    text = cfg.read_text()
    assert "volume = 4" in text and 'screen = "claude"' in text  # rotation untouched
    status, _, _ = call(url, "/api/quick", {"display": {"volume": 40}}, {"X-TC002-Token": token})
    assert status == 422 and "volume = 4" in cfg.read_text()


def test_presets_are_listed_and_applied_to_a_draft(ui):
    url, token, _ = ui
    state = json.loads(call(url, "/api/state")[2])
    assert {p["id"] for p in state["presets"]} >= {"focus", "ambient"}
    draft = state["config"]["data"]
    status, _, body = call(
        url, "/api/preset", {"data": draft, "preset": "ambient"}, {"X-TC002-Token": token}
    )
    data = json.loads(body)["data"]
    assert status == 200
    assert [s.get("builtin") for s in data["rotation"]["slots"]] == ["clock", "weather"]
    assert "weather" in data["device"]["keep_builtins"]
    assert (
        call(url, "/api/preset", {"data": draft, "preset": "nope"}, {"X-TC002-Token": token})[0]
        == 422
    )


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


def test_show_pushes_a_screen_the_clock_does_not_have_yet(monkeypatch):
    from tc002.web import api as api_module

    calls = []

    class Clock:
        def apps(self):
            return []

        def push(self, app, payload):
            calls.append(("push", app, "image" in payload))

        def switch_custom(self, app):
            calls.append(("switch", app))

    api = api_module.Api("192.0.2.1", None)
    monkeypatch.setattr(api, "_device", lambda: Clock())
    api.show({"screen": "claude"})  # samples local files only, so it runs on any OS
    assert calls == [("push", "claude", True), ("switch", "claude")]


def test_device_http_errors_keep_their_status():
    from tc002.device import DeviceError

    assert DeviceError("x", 404).status == 404 and DeviceError("y").status is None


def test_agents_endpoint_lists_sessions_and_limits(ui):
    from tc002.runtime import sessions

    sessions.record_hook(
        {"hook_event_name": "Notification", "session_id": "s1", "cwd": "/x/kura", "message": "ok?"}
    )
    url, _, _ = ui
    status, _, body = call(url, "/api/agents")
    data = json.loads(body)
    assert status == 200 and data["counts"]["waiting"] == 1
    assert data["sessions"][0]["project"] == "kura"
    assert set(data["usage"]) == {"claude", "codex"}


def test_first_run_saves_the_clock_and_creates_a_config(ui, tmp_path, monkeypatch):
    from tc002 import config
    from tc002.web import setup

    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(config, "LOCAL_FILE", tmp_path / "state" / "local.json")
    monkeypatch.delenv("TC002_CONFIG", raising=False)
    monkeypatch.setattr(
        setup, "probe", lambda host, timeout=0: {"host": host} if host == "10.0.0.9" else None
    )
    url, token, _ = ui
    headers = {"X-TC002-Token": token, "Content-Type": "application/json"}
    status = call(url, "/api/setup", {"host": "10.0.0.8"}, headers)[0]
    assert status == 422
    status, _, body = call(url, "/api/setup", {"host": "10.0.0.9", "preset": "agents"}, headers)
    assert status == 200, body
    assert status == 200
    assert config.local()["host"] == "10.0.0.9"
    assert "[rotation]" in (tmp_path / "state" / "tc002.toml").read_text()


def test_unknown_integration_action_is_404(ui):
    url, token, _ = ui
    headers = {"X-TC002-Token": token, "Content-Type": "application/json"}
    assert call(url, "/api/integrations/rm-rf", {}, headers)[0] == 404


def test_discovery_sweeps_when_nothing_announces(monkeypatch):
    from tc002.web import setup

    monkeypatch.setattr(setup, "probe", lambda h, t: {"host": h} if h.endswith(".7") else None)
    found = setup.discover("10.1.2", listen=lambda: [])
    assert found == {"subnet": "10.1.2.0/24", "clocks": [{"host": "10.1.2.7"}], "how": "sweep"}


def test_discovery_prefers_clocks_that_announce_themselves(monkeypatch):
    from tc002.web import setup

    swept = []
    monkeypatch.setattr(setup, "probe", lambda h, t: swept.append(h) or {"host": h})
    found = setup.discover(
        "10.1.2", listen=lambda: [{"host": "10.1.2.9", "mac": "x", "serial": "y"}]
    )
    assert found["how"] == "broadcast" and found["clocks"] == [{"host": "10.1.2.9"}]
    assert swept == ["10.1.2.9"]  # no sweep of the subnet


def test_live_previews_render_current_state(ui):
    url, _, _ = ui
    for name in ("live-claude", "live-usage"):
        status, _, body = call(url, f"/api/preview/{name}.gif")
        assert status == 200 and body[:6] == b"GIF89a"
    assert call(url, "/api/preview/live-sys.gif")[0] == 404


def test_favicon_is_served_in_the_token_colours(ui):
    import re
    from pathlib import Path

    url, _, _ = ui
    status, headers, body = call(url, "/favicon.svg")
    assert status == 200 and headers["Content-Type"] == "image/svg+xml"
    tokens = (Path(server.STATIC) / "css" / "tokens.css").read_text().split(":root[data-theme")[0]
    for name in ("--primary", "--bg", "--accent"):
        value = re.search(rf"{name}: (#[0-9a-f]{{6}});", tokens).group(1)
        assert value.encode() in body, f"favicon lost {name} {value}"


def test_png_and_ico_icons_match_the_svg_mark(ui):
    # Safari and /favicon.ico ignore SVG: the rasterised icons must exist and be current
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "scripts" / "render_favicon.py"
    spec = importlib.util.spec_from_file_location("render_favicon", script)
    render = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render)
    url, _, _ = ui
    for name, data in render.outputs().items():
        status, headers, body = call(url, f"/{name}")
        assert status == 200, name
        assert headers["Content-Type"] == ("image/x-icon" if name.endswith(".ico") else "image/png")
        assert body == data, f"{name} is stale: run scripts/render_favicon.py"


def test_game_previews_play_themselves(ui):
    url, _, _ = ui
    for name in ("breakout", "snake", "pong"):
        status, _, body = call(url, f"/api/preview/game-{name}.gif")
        assert status == 200 and body[:6] == b"GIF89a"
    assert call(url, "/api/preview/game-tetris.gif")[0] == 404


def test_every_server_error_title_is_translated():
    import re
    from pathlib import Path

    src = Path(server.__file__).parent
    titles = set()
    for name in ("api.py", "server.py"):
        text = (src / name).read_text()
        titles |= set(re.findall(r'(?:ApiError|_fail)\(\s*\d+,\s*"([^"]+)"', text))
    strings = (src / "static" / "js" / "i18n-errors.js").read_text()
    en, zh = strings.split("export const zh")
    for title in titles:
        key = f'"err.{title.lower().replace(" ", "-")}"'
        assert key in en and key in zh, f"no translation for error {title!r}"


def test_ui_palettes_are_the_same_in_python_css_and_js():
    import re
    from pathlib import Path

    from tc002.render import themes

    static = Path(server.STATIC)
    js = (static / "js" / "prefs.js").read_text()
    listed = re.search(r"PALETTES = \[([^\]]+)\]", js).group(1)
    assert [s.strip(' "') for s in listed.split(",")] == list(themes.UI_PALETTES)
    css = (static / "css" / "palettes.css").read_text()
    assert all(f'data-palette="{p}"' in css for p in themes.UI_PALETTES if p != "paper")


def test_appearance_changes_only_that_table(ui):
    import tomllib

    url, token, cfg = ui
    headers = {"X-TC002-Token": token, "Content-Type": "application/json"}
    status, _, body = call(
        url, "/api/appearance", {"led_theme": "match", "ui_palette": "sakura"}, headers
    )
    assert status == 200 and json.loads(body)["ledTheme"] == "sakura"
    saved = tomllib.loads(cfg.read_text())
    assert saved["appearance"] == {"led_theme": "match", "ui_palette": "sakura"}
    assert saved["rotation"]["slots"][0]["screen"] == "claude"  # the rest is untouched
    assert call(url, "/api/appearance", {"led_theme": "rainbow"}, headers)[0] == 422
    status, _, gif = call(url, "/api/preview/usage.gif?theme=kohaku")
    assert status == 200 and gif[:6] == b"GIF89a"


def test_social_tokens_are_write_only_and_limited_to_token_apps(ui):
    url, token, _ = ui
    headers = {"X-TC002-Token": token, "Content-Type": "application/json"}
    assert call(url, "/api/social-token", {"app": "bilibili", "token": "x"}, headers)[0] == 422
    assert call(url, "/api/social-token", {"app": "youtube", "token": " "}, headers)[0] == 422
    # a valid request needs a clock; with none configured it is refused, never stored
    assert call(url, "/api/social-token", {"app": "youtube", "token": "t"}, headers)[0] == 409


def test_trying_a_screen_returns_what_it_read_and_its_picture(ui):
    url, token, _ = ui
    headers = {"X-TC002-Token": token, "Content-Type": "application/json"}
    body = {"screen": "moon", "options": {"hemisphere": "south", "detail": "full"}}
    status, _, raw = call(url, "/api/try-screen", body, headers)
    result = json.loads(raw)
    assert status == 200 and result["ok"] and result["gif"].startswith("data:image/gif;base64,")
    assert {"eighth", "lit"} <= {label for label, _ in result["facts"]}
    assert call(url, "/api/try-screen", {"screen": "nope"}, headers)[0] == 422


def test_trying_a_failing_screen_says_why(ui, monkeypatch):
    from tc002.screens import stocks

    def offline(*args, **kwargs):
        raise OSError("query1.finance.yahoo.com: no network")

    monkeypatch.setattr(stocks, "fetch_quote", offline)
    url, token, _ = ui
    headers = {"X-TC002-Token": token, "Content-Type": "application/json"}
    result = json.loads(call(url, "/api/try-screen", {"screen": "stocks"}, headers)[2])
    assert result["ok"] is False and "no network" in result["error"]


def test_home_entities_need_a_connection(ui, monkeypatch):
    from tc002 import connections

    monkeypatch.setattr(connections, "value", lambda *a, **k: None)
    url, token, _ = ui
    status = call(url, "/api/home/entities", headers={"X-TC002-Token": token})[0]
    assert status == 409


def test_fixed_previews_are_drawn_once(ui, monkeypatch):
    from tc002.web import previews

    url, _, _ = ui
    previews._fixed.cache_clear()
    for _ in range(3):
        assert call(url, "/api/preview/builtin-youtube.gif")[0] == 200
    assert previews._fixed.cache_info().misses == 1
