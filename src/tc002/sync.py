"""Make the clock match tc002.toml, and put it back the way it was.

`apply` is the one place that writes tc002.toml's settings to the device; the CLI
(`tc002 layout apply`) and the web UI both call it. Before the first change it saves the
clock's original layout (flags, orders and non-secret settings only) so `restore` can
undo tc002 entirely.
"""

from . import builtins, device_settings
from .device import CATEGORY_ENDPOINTS

GLOBAL_KEYS = ["carouselSpeed", "brightness", *device_settings.DISPLAY]


def _infos(device, category):
    _, _, infos_key, _ = CATEGORY_ENDPOINTS[category]
    return device.category_config(category).get(infos_key, {})


def _original(device):
    current = device.config()
    infos = {c: _infos(device, c) for c in CATEGORY_ENDPOINTS}
    apps = {}
    for app, rules in device_settings.APPS.items():
        stored = infos[builtins.lookup(app).category].get(app, {})
        apps[app] = {k: stored[k] for k in rules if k in stored}  # rules hold no secrets
    return {
        "categories": builtins.snapshot(device),
        "global": {k: current[k] for k in GLOBAL_KEYS if k in current},
        "apps": apps,
    }


def apply(device, settings, state_dir):
    """Push tc002.toml to the clock; returns human-readable changes."""
    changes = []
    path, saved = builtins.save_original(_original(device), state_dir)
    if saved:
        changes.append(f"saved original layout to {path}")

    off_on = builtins.apply_enabled(device, set(settings.keep_builtins))
    changes += [f"built-in {c}" for c in off_on]

    current = device.config()
    update = dict(settings.display)
    if "brightness" in update and isinstance(current.get("brightness"), dict):
        # send the whole object: the device wants low < mid < high every time
        update["brightness"] = current["brightness"] | update["brightness"]
    if settings.rotation:
        update["carouselSpeed"] = 0  # the tc002 rotation drives the screen
    changed = {k: v for k, v in update.items() if current.get(k) != v}
    if changed:
        device.set_config(**changed)
        changes += [f"{k} -> {v}" for k, v in changed.items()]

    changes += _apply_apps(device, settings.apps)
    return changes


def _apply_apps(device, apps):
    """Write [apps.*] settings, one request per category that changed."""
    changes = []
    for category, (_, _, infos_key, order_key) in CATEGORY_ENDPOINTS.items():
        mine = {a: f for a, f in apps.items() if builtins.lookup(a).category == category}
        if not mine:
            continue
        cfg = device.category_config(category)
        infos = cfg.get(infos_key, {})
        before = len(changes)
        for app, fields in mine.items():
            target = infos.setdefault(app, {})
            for key, value in fields.items():
                merged = target.get(key, {}) | value if isinstance(value, dict) else value
                if target.get(key) != merged:
                    target[key] = merged
                    changes.append(f"{app}.{key} -> {merged}")
        if len(changes) > before:
            order = cfg.get(order_key) or builtins.full_order(category)
            device.set_category_config(category, {infos_key: infos, order_key: order})
    return changes


def restore(device, state_dir):
    """Return the clock to the layout saved before tc002 first changed it."""
    path, snap = builtins.load_original(state_dir)
    builtins.restore(device, snap["categories"])
    if snap.get("global"):
        device.set_config(**snap["global"])
    if snap.get("apps"):
        _apply_apps(device, snap["apps"])
    return path
