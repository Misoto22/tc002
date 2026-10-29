"""Make the clock match tc002.toml, and put it back the way it was.

`apply` is the one place that writes tc002.toml's settings to the device; the CLI
(`tc002 layout apply`) and the web UI both call it. Before the first change it saves the
clock's original layout (flags, orders and non-secret settings only) so `restore` can
undo tc002 entirely.
"""

from . import builtins, device_settings

GLOBAL_KEYS = ["carouselSpeed", "brightness", *device_settings.DISPLAY]


def _original(device):
    current = device.config()
    tools = device.category_config("tools").get("toolsInfos", {})
    return {
        "categories": builtins.snapshot(device),
        "global": {k: current[k] for k in GLOBAL_KEYS if k in current},
        "apps": {
            app: {k: tools[app][k] for k in rules if k in tools.get(app, {})}
            for app, rules in device_settings.APPS.items()
        },
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
    if settings.playlist:
        update["carouselSpeed"] = 0  # the tc002 playlist drives the screen
    changed = {k: v for k, v in update.items() if current.get(k) != v}
    if changed:
        device.set_config(**changed)
        changes += [f"{k} -> {v}" for k, v in changed.items()]

    changes += _apply_apps(device, settings.apps)
    return changes


def _apply_apps(device, apps):
    if not apps:
        return []
    cfg = device.category_config("tools")
    infos = cfg.get("toolsInfos", {})
    changes = []
    for app, fields in apps.items():
        target = infos.setdefault(app, {})
        for key, value in fields.items():
            merged = target.get(key, {}) | value if isinstance(value, dict) else value
            if target.get(key) != merged:
                target[key] = merged
                changes.append(f"{app}.{key} -> {merged}")
    if changes:
        order = cfg.get("toolsOrder") or list(range(1, 10))
        device.set_category_config("tools", {"toolsInfos": infos, "toolsOrder": order})
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
