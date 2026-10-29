"""The LED palette: the single owner of every colour drawn on the clock.

Screens, the LED mock-ups and the web UI's simulators (served by /api/led) all take
colours from here by name, so a colour is changed in one place.
"""

LED = {
    # neutrals
    "white": 0xFFFFFF,
    "soft_white": 0xE9EBEE,
    "label": 0x8A929D,
    "gray": 0x5B626D,
    "dim": 0x2A3038,
    "track": 0x1E242C,
    "grid": 0x1A1F26,
    # hues
    "green": 0x3EE08A,
    "yellow": 0xFFD000,
    "amber": 0xFFB020,
    "red": 0xFF5A52,
    "blue": 0x4285F4,
    "sky": 0x5B8DEF,
    "cyan": 0x00E5FF,
    "violet": 0xA78BFA,
    "orange": 0xD97757,  # Claude
    "peach": 0xFFD9C7,
    "teal": 0x10A37F,  # Codex
    # the clock itself, for mock-ups
    "panel": 0x0B0C0E,
    "off": 0x16181C,
}

# Colours offered by name for messages (`tc002 text --color green`).
MESSAGE_COLORS = ("white", "green", "yellow", "red", "blue", "orange", "cyan")


def hex_palette():
    """The palette as "#RRGGBB" strings, for the browser."""
    return {name: f"#{value:06X}" for name, value in LED.items()}
