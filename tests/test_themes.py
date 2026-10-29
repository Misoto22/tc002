"""LED colour themes: recolouring finished frames, and choosing the theme from settings."""

import pytest

from tc002 import config
from tc002.render import themes
from tc002.render.canvas import dim
from tc002.render.palette import LED
from tc002.screens import usage


def test_classic_and_black_are_left_alone():
    assert themes.recolour(LED["green"], themes.CLASSIC) == LED["green"]
    assert themes.recolour(0, "sakura") == 0


def test_a_palette_colour_becomes_its_counterpart():
    assert themes.recolour(LED["green"], "matcha") == themes.THEMES["matcha"]["green"]
    assert themes.recolour(LED["white"], "paper") == themes.THEMES["paper"]["white"]


def test_dimmed_pixels_keep_their_brightness():
    half = dim(LED["sky"], 0.5)
    out = themes.recolour(half, "ai")
    target = themes.THEMES["ai"]["sky"]
    assert abs(max(themes._rgb(out)) - max(themes._rgb(target)) * 0.5) <= 3


def test_kohaku_is_amber_only():
    for name in ("green", "sky", "red", "white"):
        r, g, b = themes._rgb(themes.recolour(LED[name], "kohaku"))
        assert r >= g >= b  # amber: red over green over blue


def test_match_follows_the_ui_palette():
    assert themes.resolve("match", "sakura") == "sakura"
    assert themes.resolve("ai", "sakura") == "ai"
    assert themes.resolve("nonsense", "paper") == themes.CLASSIC


def test_settings_default_to_matching_the_ui_and_reject_unknown_themes():
    assert config.parse({}).led_theme == "paper"
    with pytest.raises(config.ConfigError):
        config.parse({"appearance": {"led_theme": "rainbow"}})


@pytest.mark.parametrize("theme", list(themes.THEMES))
def test_every_theme_still_fits_the_clock(theme):
    anim = usage.render(usage.State((usage.Row("claude", 62, 38), usage.Row("codex", 14, 61))))
    anim.payload(theme=theme)  # raises when over the firmware's size limits
