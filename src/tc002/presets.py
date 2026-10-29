"""Ready-made rotations. Applying one replaces the rotation's slots and turns on the screens
and built-in apps it needs; names and descriptions are translated by the UI (i18n keys
"preset.<id>.name" and "preset.<id>.desc").
"""

PRESETS = {
    "focus": [("screen", "claude", 45), ("screen", "usage", 15)],
    "developer": [
        ("screen", "claude", 30),
        ("screen", "usage", 15),
        ("screen", "sys", 15),
        ("builtin", "clock", 15),
    ],
    "agents": [("screen", "claude", 30), ("screen", "usage", 30)],
    "ambient": [("builtin", "clock", 30), ("builtin", "weather", 15)],
    "clock": [("builtin", "clock", 60)],
}


def apply(data, preset_id):
    """Return a copy of a tc002.toml document with `preset_id`'s rotation applied."""
    if preset_id not in PRESETS:
        raise ValueError(f"unknown preset {preset_id!r}; known: {', '.join(PRESETS)}")
    slots = [{kind: name, "seconds": seconds} for kind, name, seconds in PRESETS[preset_id]]
    screens = list(data.get("screens", {}).get("enabled", []))
    keep = list(data.get("device", {}).get("keep_builtins", []))
    for kind, name, _ in PRESETS[preset_id]:
        target = screens if kind == "screen" else keep
        if name not in target:
            target.append(name)
    return {
        **data,
        "screens": {**data.get("screens", {}), "enabled": screens},
        "device": {**data.get("device", {}), "keep_builtins": keep},
        "rotation": {"slots": slots},
    }


def describe():
    """For the UI: each preset's slots, in order."""
    return [
        {"id": pid, "slots": [{kind: name, "seconds": s} for kind, name, s in slots]}
        for pid, slots in PRESETS.items()
    ]
