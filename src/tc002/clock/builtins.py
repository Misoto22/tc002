"""The clock's built-in apps: which ones stay on, and switching to them.

Index numbers come from the protocol reference (section 2.3). Only `enable` flags and
order arrays are ever saved to disk: the full configs also hold social OAuth tokens,
calendar passwords and the weather API key, which must not leave the device.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .device import CATEGORY_ENDPOINTS


@dataclass(frozen=True)
class Builtin:
    category: str
    key: str  # key inside the category's `xxxInfos` object
    index: int  # index used by /switchApp and `xxxOrder`


CATALOGUE = {
    b.key: b
    for b in [
        *(
            Builtin("tools", k, i)
            for i, k in enumerate(
                [
                    "clock",
                    "weather",
                    "busy",
                    "scoreboard",
                    "tomato",
                    "stopwatch",
                    "battery",
                    "soundlight",
                    "ipshow",
                ],
                start=1,
            )
        ),
        *(
            Builtin("social", k, i)
            for i, k in enumerate(
                [
                    "xhs",
                    "douyin",
                    "bilibili",
                    "weibo",
                    "youtube",
                    "instagram",
                    "facebook",
                    "tiktok",
                    "x",
                ],
                start=1,
            )
        ),
        *(
            Builtin("calendar", k, i)
            for i, k in enumerate(
                ["feishu", "dingding", "wecom", "google", "icloud", "outlook"], start=1
            )
        ),
    ]
}


def lookup(name):
    try:
        return CATALOGUE[name]
    except KeyError:
        raise ValueError(
            f"unknown built-in app {name!r}; known: {', '.join(sorted(CATALOGUE))}"
        ) from None


def snapshot(device):
    """Current enable flags and orders of every category (no credentials)."""
    snap = {}
    for category, (_, _, infos_key, order_key) in CATEGORY_ENDPOINTS.items():
        cfg = device.category_config(category)
        snap[category] = {
            "enable": {
                k: bool(v.get("enable"))
                for k, v in cfg.get(infos_key, {}).items()
                if k in CATALOGUE  # skips device bookkeeping such as social "tokens"
            },
            "order": cfg.get(order_key, []),
        }
    return snap


# Platforms this clock's firmware hides (by region): listed in /getSocial as
# `hiddenPlatforms`. They stay `enable: false` whatever is written, and /switchApp to
# one answers 404, so tc002 reports them instead of pretending to turn them on.
HIDDEN_KEY = "hiddenPlatforms"


def hidden_in(cfg):
    """The catalogue apps a category's config says this firmware hides."""
    listed = cfg.get(HIDDEN_KEY) or []
    return {k for k in listed if isinstance(k, str) and k in CATALOGUE}


def hidden(device):
    """Every built-in app this clock's firmware hides (one request per category)."""
    return set().union(*(hidden_in(device.category_config(c)) for c in CATEGORY_ENDPOINTS))


def apply_enabled(device, keep):
    """Enable exactly the built-ins named in `keep`; disable every other one.

    Each category is read in full and written back with only `enable` changed, so
    settings such as the weather city are preserved and the order array stays
    complete (the device rejects a partial order with 400). Returns (changed,
    unavailable): what was switched, and the kept apps this firmware hides, which are
    left alone because they cannot be turned on.
    """
    for name in keep:
        lookup(name)  # fail before touching the device
    changed, unavailable = [], []
    for category, (_, _, infos_key, order_key) in CATEGORY_ENDPOINTS.items():
        cfg = device.category_config(category)
        infos = cfg.get(infos_key, {})
        off_limits = hidden_in(cfg)
        dirty = False
        for key, info in infos.items():
            if key not in CATALOGUE:  # e.g. the social "tokens" cache is not an app
                continue
            if key in off_limits:
                if key in keep:
                    unavailable.append(key)
                continue
            want = key in keep
            if bool(info.get("enable")) != want:
                info["enable"] = want
                changed.append(f"{key}={'on' if want else 'off'}")
                dirty = True
        if dirty:
            order = cfg.get(order_key) or full_order(category)
            device.set_category_config(category, {infos_key: infos, order_key: order})
    return changed, unavailable


def full_order(category):
    return sorted(b.index for b in CATALOGUE.values() if b.category == category)


def restore(device, snap):
    """Write back the enable flags and orders saved by `snapshot`."""
    for category, saved in snap.items():
        _, _, infos_key, order_key = CATEGORY_ENDPOINTS[category]
        cfg = device.category_config(category)
        infos = cfg.get(infos_key, {})
        for key, enabled in saved["enable"].items():
            if key in infos:
                infos[key]["enable"] = enabled
        device.set_category_config(category, {infos_key: infos, order_key: saved["order"]})


ORIGINAL = "original-layout.json"


def save_original(snap, directory):
    """Keep the layout from before tc002 first changed it; later applies never overwrite it,
    so `restore` always returns the clock to how it was before tc002."""
    path = Path(directory) / ORIGINAL
    if path.exists():
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2))
    return path, True


def load_original(directory):
    path = Path(directory) / ORIGINAL
    if not path.exists():
        raise FileNotFoundError(f"no saved original layout at {path}; nothing to restore")
    return path, json.loads(path.read_text())
