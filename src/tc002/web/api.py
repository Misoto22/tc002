"""The JSON API behind `tc002 ui`: one table per method, path -> App call.

Each handler checks the shape of the request (that is this front end's job: JSON, not
App, decides what a body looks like) and returns what App returns. Nothing here reads
files, talks to the clock or runs commands; App does.
"""

from ..app import catalog
from .errors import ApiError


def _dict(value, what):
    if not isinstance(value, dict) or not value:
        raise ApiError(422, "Nothing to change", f'Send {{"{what}": {{...}}}}.')
    return value


def _night(app, body):
    """Screen off now (`{"off": true, "until": "morning" | null}`) or on (`{"off": false}`)."""
    if body.get("off"):
        return app.screen_off(until_morning=body.get("until") == "morning")
    return app.screen_on()


def _focus(app, body):
    if body.get("action") == "stop":
        return app.focus_stop()
    done = app.focus_start(body.get("minutes") or None)
    return {k: done[k] for k in ("running", "minutes", "break")}


def _game(app, body):
    if body.get("action") == "stop":
        return app.stop_game()
    return app.play_game(body.get("game"))


def _first_run(app, body):
    return app.first_run(
        body.get("host"), body.get("preset"), body.get("timezone"), body.get("weather")
    )


# GET path -> (app, query) -> JSON
GETS = {
    "/api/state": lambda app, q: app.overview(),
    "/api/led": lambda app, q: catalog.led(),
    "/api/cities": lambda app, q: app.find_cities(q.get("q", ""), q.get("lang", "en")),
    "/api/agents": lambda app, q: app.agents(),
    "/api/discover": lambda app, q: app.discover(),
    "/api/log": lambda app, q: app.log(),
    "/api/wifi/status": lambda app, q: app.wifi_status(),
    "/api/game/frame": lambda app, q: app.game_frame(),
    "/api/symbols": lambda app, q: app.find_symbols(q.get("q")),
    "/api/home/entities": lambda app, q: app.home_entities(),
    "/api/clock/check": lambda app, q: app.clock_check(),
}

# POST path -> (app, body, headers) -> JSON
POSTS = {
    # If-Match: the version the page loaded, so a file changed since is not overwritten
    "/api/config": lambda app, b, h: app.save_config(b, expected=h.get("If-Match")),
    "/api/quick": lambda app, b, h: app.set_display(_dict(b.get("display"), "display")),
    "/api/appearance": lambda app, b, h: app.set_appearance(
        b.get("led_theme"), b.get("ui_palette")
    ),
    "/api/preset": lambda app, b, h: app.apply_preset(b.get("data"), b.get("preset")),
    "/api/live": lambda app, b, h: app.live(b.get("data"), b.get("focus") or None),
    "/api/live/stop": lambda app, b, h: app.live_stop(),
    "/api/show": lambda app, b, h: app.show(b.get("screen"), b.get("builtin")),
    "/api/message": lambda app, b, h: app.start_message(
        b.get("text"), b.get("type"), b.get("kind", "done"), b.get("color")
    ),
    "/api/night": lambda app, b, h: _night(app, b),
    "/api/focus": lambda app, b, h: _focus(app, b),
    "/api/game": lambda app, b, h: _game(app, b),
    "/api/game/key": lambda app, b, h: app.game_key(b.get("key"), b.get("down")),
    "/api/try-screen": lambda app, b, h: app.try_screen(b.get("screen"), b.get("options")),
    "/api/setup": lambda app, b, h: _first_run(app, b),
    "/api/social-token": lambda app, b, h: app.set_social_token(b.get("app"), b.get("token")),
    "/api/secret": lambda app, b, h: app.save_secret(
        b.get("connection"), b.get("field"), b.get("value")
    ),
    "/api/reveal": lambda app, b, h: app.reveal(b.get("what")),
    "/api/wifi/join-hotspot": lambda app, b, h: app.wifi_join_hotspot(),
    "/api/wifi/send": lambda app, b, h: app.wifi_send(b.get("ssid"), b.get("password")),
    "/api/wifi/rejoin": lambda app, b, h: app.wifi_rejoin(b.get("ssid")),
}
INTEGRATIONS = "/api/integrations/"  # + action name -> app.integration(action)
PREVIEW = ("/api/preview/", ".gif")  # /api/preview/<name>.gif -> app.preview(...)


def get(app, path, query):
    return GETS[path](app, query)


def preview(app, name, query):
    return app.preview(
        name, query.get("theme"), query.get("text"), query.get("color"), query.get("kind")
    )


def post(app, path, body, headers):
    if path.startswith(INTEGRATIONS):
        return app.integration(path.removeprefix(INTEGRATIONS))
    if path not in POSTS:
        raise ApiError(404, "Not found", f"No endpoint at {path}.")
    return POSTS[path](app, body, headers)
