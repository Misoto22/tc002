"""What the clock reports that tc002 manages, and where it differs from tc002.toml.

Credentials stored on the clock are never read out: only their presence is reported."""

from concurrent.futures import ThreadPoolExecutor

from ..clock import builtins, device_settings, tz
from ..clock.device import CATEGORY_ENDPOINTS, DeviceError

SECRET_KEYS = {"token", "password", "username", "url", "tokens"}


def clock_state(dev, host, settings):
    # six independent reads: asked at once, the caller waits for the slowest, not the sum
    calls = {"base": dev.base_info, "config": dev.config, "apps": dev.apps}
    calls |= {c: (lambda c=c: dev.category_config(c)) for c in CATEGORY_ENDPOINTS}
    try:
        with ThreadPoolExecutor(len(calls)) as pool:
            futures = {name: pool.submit(call) for name, call in calls.items()}
            got = {name: f.result() for name, f in futures.items()}
        base, cfg, apps = got["base"], got["config"], got["apps"]
        categories = {c: got[c] for c in CATEGORY_ENDPOINTS}
    except DeviceError as exc:
        return {"online": False, "host": host, "error": str(exc)}
    enabled = {}
    for category, (_, _, infos_key, _) in CATEGORY_ENDPOINTS.items():
        hidden = builtins.hidden_in(categories[category])
        for key, info in categories[category].get(infos_key, {}).items():
            if key in builtins.CATALOGUE:
                enabled[key] = {
                    "enabled": bool(info.get("enable")),
                    "credentials": any(info.get(s) for s in SECRET_KEYS & set(info)),
                    "hidden": key in hidden,  # this firmware hides it: it can never be on
                }

    def stored(app):
        _, _, infos_key, _ = CATEGORY_ENDPOINTS[builtins.lookup(app).category]
        return categories[builtins.lookup(app).category].get(infos_key, {}).get(app, {})

    # only the settings tc002 manages: never a token, password or key
    app_settings = {
        app: {k: stored(app).get(k) for k in rules} for app, rules in device_settings.APPS.items()
    }
    return {
        "online": True,
        "host": host,
        "base": base,
        "settings": cfg,
        "builtins": enabled,
        "apps": app_settings,
        "customApps": apps,
        "drift": drift(settings, cfg, app_settings, enabled),
        "unavailable": unavailable(settings, enabled),
    }


def wanted_builtins(settings):
    """Built-in apps tc002.toml asks for: kept, or shown by the rotation."""
    return set(settings.keep_builtins) | {s.builtin for s in settings.schedule if s and s.builtin}


def unavailable(settings, enabled):
    """Built-in apps tc002.toml asks for that this clock's firmware hides."""
    return sorted(k for k in wanted_builtins(settings) if enabled.get(k, {}).get("hidden"))


def drift(settings, cfg, app_settings, enabled):
    """Where the clock differs from tc002.toml (e.g. changed on the device itself)."""
    found = []
    for key, value in settings.display.items():
        current = cfg.get(key)
        if key == "timezone" and value == "auto":
            if not _follows_this_mac(cfg.get("timezoneEx")):
                found.append("display.timezone")
            continue
        if isinstance(value, dict) and isinstance(current, dict):
            if any(current.get(k) != v for k, v in value.items()):
                found.append(f"display.{key}")
        elif current != value:
            found.append(f"display.{key}")
    for app, fields in settings.apps.items():
        for key, value in fields.items():
            current = app_settings.get(app, {}).get(key)
            if isinstance(value, dict):  # e.g. weather.displayInfo may list only some flags
                same = isinstance(current, dict) and all(
                    current.get(k) == v for k, v in value.items()
                )
            else:
                same = current == value
            if not same:
                found.append(f"apps.{app}.{key}")
    for key, state in enabled.items():
        if state.get("hidden"):  # cannot match: reported in "unavailable" instead
            continue
        if state["enabled"] != (key in settings.keep_builtins):
            found.append(f"builtin.{key}")
    if settings.schedule and cfg.get("carouselSpeed"):
        found.append("display.carouselSpeed")
    return found


def _follows_this_mac(ex):
    """Whether the clock's timezoneEx is this Mac's zone rule (timezone = "auto")."""
    try:
        _, rule = tz.mac_zone()
    except ValueError:
        return True  # this Mac's zone cannot be read: nothing to compare against
    ex = ex or {}
    return bool(ex.get("customPosixEnabled")) and ex.get("customPosix") == rule
