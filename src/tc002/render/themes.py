"""LED colour themes for tc002's own screens.

Screens keep drawing with the named colours in palette.LED ("classic"). A theme recolours
the finished frames just before they are encoded: each lit pixel is matched to the
palette colour it came from (by hue for colours, by brightness for greys) and replaced by
that colour's counterpart in the theme at the same brightness. Dimmed and blended pixels
therefore follow too, and no screen has to know which theme is on. The clock's own
built-in apps are drawn by its firmware and are not affected.

Theme names match the UI's colour palettes, so "match" can follow the interface.
"""

from functools import lru_cache

from .palette import LED

CLASSIC = "classic"
MATCH = "match"  # follow the UI's colour palette (appearance.ui_palette)
UI_PALETTES = ("paper", "matcha", "ai", "sakura", "kohaku")  # css/palettes.css, js/prefs.js

# Overrides of palette.LED per theme; a name not listed keeps its classic colour.
THEMES = {
    CLASSIC: {},
    "paper": {  # warm and a little softer, like the UI's paper
        "white": 0xF4EBDD,
        "soft_white": 0xE6DDCF,
        "label": 0x9C9284,
        "gray": 0x6E665C,
        "green": 0x9BC47F,
        "yellow": 0xF2C960,
        "amber": 0xF0A848,
        "red": 0xEC6A55,
        "blue": 0x6F95D8,
        "sky": 0x7FA6E0,
        "cyan": 0x7CC9C2,
        "violet": 0xB49BDA,
        "orange": 0xE8825A,
        "peach": 0xF7D2BC,
        "teal": 0x5EAE97,
    },
    "matcha": {  # tea greens, cream whites
        "white": 0xEEF3E2,
        "soft_white": 0xE2EAD2,
        "label": 0x93A086,
        "green": 0xA8D46F,
        "sky": 0x79C2A0,
        "cyan": 0x8ED6B8,
        "blue": 0x6FAF9A,
        "violet": 0x9FC28A,
        "yellow": 0xE3D46A,
        "amber": 0xE6A84A,
        "red": 0xE06A52,
        "orange": 0xDE8A55,
        "peach": 0xE9E2B8,
        "teal": 0x4FB389,
    },
    "ai": {  # indigo blues, cool whites
        "white": 0xE8EEFF,
        "soft_white": 0xD9E2F7,
        "label": 0x8B97B5,
        "sky": 0x6F9CFF,
        "blue": 0x4F7DF0,
        "cyan": 0x6CC8F0,
        "green": 0x5DD6A8,
        "violet": 0x9C8CF5,
        "yellow": 0xF2D06B,
        "amber": 0xF2A94A,
        "red": 0xF06A70,
        "orange": 0xF0875A,
        "peach": 0xF4D7D0,
        "teal": 0x3FAFB0,
    },
    "sakura": {  # blossom pinks, pastel accents
        "white": 0xFFEEF3,
        "soft_white": 0xF6E1E8,
        "label": 0xB2949F,
        "sky": 0xA0B4FF,
        "blue": 0x8C9CF0,
        "cyan": 0x9AD4E8,
        "green": 0x8FDDB0,
        "violet": 0xD3A0F0,
        "yellow": 0xFFD98A,
        "amber": 0xFFB070,
        "red": 0xFF6F8F,
        "orange": 0xFF8F80,
        "peach": 0xFFD3DE,
        "teal": 0x7FCFB8,
    },
    "kohaku": None,  # amber monochrome: every colour becomes amber at its own brightness
}
KOHAKU = 0xFFA820
NEUTRAL_SATURATION = 0.18  # below this a pixel is a grey and matches by brightness
# Background shades used only by mock-ups, never recoloured.
_SKIP = {"panel", "off"}


def names():
    """Themes a setting may name, "match" first."""
    return [MATCH, *THEMES]


def resolve(led_theme, ui_palette):
    """The theme actually used: led_theme, or the UI's palette when it says "match"."""
    if led_theme == MATCH:
        return ui_palette if ui_palette in THEMES else CLASSIC
    return led_theme if led_theme in THEMES else CLASSIC


def _rgb(v):
    return (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF


def _saturation(r, g, b):
    hi = max(r, g, b)
    return 0 if hi == 0 else (hi - min(r, g, b)) / hi


def _sources():
    """Classic colours to match against: (name, rgb, is_neutral)."""
    out = []
    for name, value in LED.items():
        if name in _SKIP:
            continue
        rgb = _rgb(value)
        out.append((name, rgb, _saturation(*rgb) < NEUTRAL_SATURATION))
    return out


def _closest(rgb):
    r, g, b = rgb
    neutral = _saturation(r, g, b) < NEUTRAL_SATURATION
    candidates = [(n, c) for n, c, is_neutral in _sources() if is_neutral == neutral]
    if neutral:  # greys differ only in brightness
        return min(candidates, key=lambda nc: abs(max(nc[1]) - max(rgb)))
    norm = max(1e-9, (r * r + g * g + b * b) ** 0.5)

    def cos(nc):
        cr, cg, cb = nc[1]
        return -(r * cr + g * cg + b * cb) / (
            norm * max(1e-9, (cr * cr + cg * cg + cb * cb) ** 0.5)
        )

    return min(candidates, key=cos)


@lru_cache(maxsize=4096)
def recolour(value, theme):
    """One packed RGB pixel in `theme`. Black (off) stays off."""
    if value == 0 or theme == CLASSIC or theme not in THEMES:
        return value
    rgb = _rgb(value)
    if THEMES[theme] is None:  # monochrome
        level = max(rgb) / 255
        return _pack(tuple(c * level for c in _rgb(KOHAKU)))
    name, source = _closest(rgb)
    target = THEMES[theme].get(name, LED[name])
    scale = max(rgb) / max(1, max(source))
    return _pack(tuple(c * scale for c in _rgb(target)))


def _pack(rgb):
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return (r << 16) | (g << 8) | b


def frames(pixel_lists, theme):
    """Recolour whole frames (lists of packed RGB) for `theme`."""
    if theme == CLASSIC or theme not in THEMES:
        return pixel_lists
    return [[recolour(p, theme) for p in px] for px in pixel_lists]
