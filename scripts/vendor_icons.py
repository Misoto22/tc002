"""Rebuild the UI's icons: src/tc002/web/static/icons.svg and app-icons.json.

- Interface icons: Lucide (https://lucide.dev, ISC license).
- Brand marks: Simple Icons (https://simpleicons.org, CC0), and for marks it does not
  carry, Iconify sets with permissive licences (Ant Design MIT, IconPark Apache-2.0,
  Material Design Icons Apache-2.0, Bootstrap Icons MIT). The marks remain their owners'
  trademarks and are used only to label those apps.

This script is the only way either file changes: edit the tables below, then run
    uv run python scripts/vendor_icons.py
"""

import json
import re
import urllib.request
from pathlib import Path

LUCIDE = "1.63.0"
SIMPLE_ICONS = "16.36.0"
LOBEHUB = "1.101.0"  # @lobehub/icons-static-svg (MIT): AI brand marks Simple Icons lacks
STATIC = Path(__file__).resolve().parent.parent / "src" / "tc002" / "web" / "static"

UI_ICONS = [
    # navigation
    "layout-dashboard",
    "repeat",
    "blocks",
    "sun",
    "sliders-horizontal",
    "message-square-text",
    "plug",
    "panel-left",
    "list-checks",
    # actions
    "grip-vertical",
    "plus",
    "x",
    "eye",
    "copy",
    "folder-search",
    "scroll-text",
    "hourglass",
    "key-round",
    "user",
    "refresh-cw",
    "send",
    "search",
    "save",
    "undo-2",
    "rotate-ccw",
    "play",
    "pause",
    "external-link",
    "chevron-down",
    "chevron-right",
    "check",
    # status
    "circle-check",
    "triangle-alert",
    "circle-alert",
    "loader-circle",
    "cloud-off",
    "wifi",
    "radio",
    "history",
    "info",
    "power",
    # preferences
    "command",
    "languages",
    "sun-moon",
    "moon",
    "monitor",
    "keyboard",
    "volume-2",
    "sun-dim",
    # content and app glyphs
    "map-pin",
    "clock",
    "cloud-sun",
    "timer",
    "bell",
    "cpu",
    "bot",
    "sparkles",
    "tv",
    "zap",
    "lightbulb",
    "trophy",
    "alarm-clock",
    "battery-medium",
    "audio-lines",
    "network",
    "mail",
    "terminal",
    "gauge",
    "layers",
]

# app key -> how its icon is drawn: `brand` ("si:<slug>" from Simple Icons or
# "iconify:<prefix>/<name>") or `glyph` (a Lucide name). Icons render monochrome in the UI.
APPS = {
    # tc002 screens
    "claude": {"brand": "si:claude"},
    "sys": {"glyph": "cpu"},
    "usage": {"glyph": "gauge"},
    "codex": {"brand": "lobehub:codex"},  # the Codex mark itself, not OpenAI's logo
    # tools
    "clock": {"glyph": "clock"},
    "weather": {"glyph": "cloud-sun"},
    "busy": {"glyph": "lightbulb"},
    "scoreboard": {"glyph": "trophy"},
    "tomato": {"glyph": "timer"},
    "stopwatch": {"glyph": "alarm-clock"},
    "battery": {"glyph": "battery-medium"},
    "soundlight": {"glyph": "audio-lines"},
    "ipshow": {"glyph": "network"},
    # social
    "xhs": {"brand": "si:xiaohongshu"},
    "douyin": {"brand": "si:tiktok"},  # Douyin uses the same note mark
    "bilibili": {"brand": "si:bilibili"},
    "weibo": {"brand": "si:sinaweibo"},
    "youtube": {"brand": "si:youtube"},
    "instagram": {"brand": "si:instagram"},
    "facebook": {"brand": "si:facebook"},
    "tiktok": {"brand": "si:tiktok"},
    "x": {"brand": "si:x"},
    # calendar
    "feishu": {"brand": "iconify:icon-park/lark"},
    "dingding": {"brand": "iconify:ant-design/dingtalk"},
    "wecom": {"brand": "iconify:ant-design/wechat-work-filled"},
    "google": {"brand": "si:googlecalendar"},
    "icloud": {"brand": "si:icloud"},
    "outlook": {"brand": "iconify:mdi/microsoft-outlook"},
}


def _fetch(url):
    # Iconify's API refuses Python's default User-Agent; name this script instead.
    req = urllib.request.Request(
        url, headers={"User-Agent": "tc002-vendor-icons/1 (+github.com/Misoto22/tc002)"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode()


def _view_box(svg):
    return re.search(r'viewBox="([^"]+)"', svg).group(1)


def _brand_url(spec):
    kind, _, ref = spec.partition(":")
    if kind == "si":
        return f"https://unpkg.com/simple-icons@{SIMPLE_ICONS}/icons/{ref}.svg"
    if kind == "iconify":
        return f"https://api.iconify.design/{ref}.svg"
    if kind == "lobehub":
        return f"https://unpkg.com/@lobehub/icons-static-svg@{LOBEHUB}/icons/{ref}.svg"
    raise ValueError(f"unknown brand source {spec!r}")


def _brand_id(spec):
    return "brand-" + re.sub(r"[^a-z0-9]+", "-", spec.split(":", 1)[1].lower())


def _inner(svg):
    root, inner = re.search(r"<svg([^>]*)>(.*)</svg>", svg, re.S).groups()
    inner = re.sub(r"<title>.*?</title>|<!--.*?-->", "", inner, flags=re.S).strip()
    inner = re.sub(r"\s+", " ", inner)
    # a fill rule on the root (LobeHub marks cut shapes out with evenodd) would be lost
    if rule := re.search(r'fill-rule="([^"]+)"', root):
        inner = f'<g fill-rule="{rule.group(1)}">{inner}</g>'
    return inner


def main():
    symbols = [
        f'<symbol id="{name}" viewBox="0 0 24 24">'
        f"{_inner(_fetch(f'https://unpkg.com/lucide-static@{LUCIDE}/icons/{name}.svg'))}</symbol>"
        for name in UI_ICONS
    ]
    brands = sorted({a["brand"] for a in APPS.values() if "brand" in a})
    for spec in brands:
        svg = _fetch(_brand_url(spec))
        symbols.append(
            f'<symbol id="{_brand_id(spec)}" viewBox="{_view_box(svg)}">{_inner(svg)}</symbol>'
        )
    (STATIC / "icons.svg").write_text(
        f"<!-- Lucide {LUCIDE} (ISC), Simple Icons {SIMPLE_ICONS} (CC0), LobeHub {LOBEHUB} "
        "(MIT; brand marks belong "
        "to their owners) and Iconify brand marks (see scripts/vendor_icons.py for each "
        "source and licence); generated by scripts/vendor_icons.py — do not edit -->\n"
        '<svg xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(symbols) + "\n</svg>\n"
    )
    for app in APPS.values():  # every glyph an app uses must exist in the sprite
        assert app.get("glyph") is None or app["glyph"] in UI_ICONS, app
    icons = {
        key: {
            "symbol": _brand_id(a["brand"]) if "brand" in a else a["glyph"],
            "kind": "brand" if "brand" in a else "glyph",
        }
        for key, a in APPS.items()
    }
    (STATIC / "app-icons.json").write_text(json.dumps(icons, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(UI_ICONS)} Lucide {LUCIDE} + {len(brands)} brand marks; {len(APPS)} apps")


if __name__ == "__main__":
    main()
