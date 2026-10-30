"""The UI's design system holds: every colour and size comes from tokens.css, every token
used exists and every token defined is used, text passes WCAG AA contrast in both
themes, and layouts break at the listed breakpoints only. See docs/design-system.md."""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "src" / "tc002" / "web" / "static"
TOKENS = (STATIC / "css" / "tokens.css").read_text()
PALETTES = (STATIC / "css" / "palettes.css").read_text()
RULES = {
    name: (STATIC / "css" / name).read_text()
    for name in ("base.css", "components.css", "pages.css", "motion.css")
}
JS = "".join(p.read_text() for p in (STATIC / "js").rglob("*.js"))
BREAKPOINTS = {"640px", "760px", "900px"}  # listed in tokens.css


def _code(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


@pytest.mark.parametrize("name", list(RULES))
def test_rules_take_colours_and_sizes_from_tokens(name):
    problems = []
    for i, line in enumerate(_code(RULES[name]).splitlines(), 1):
        if line.strip().startswith("@media"):
            continue
        if hexes := re.findall(r"#[0-9a-fA-F]{3,8}\b", line):
            problems.append(f"{name}:{i} colour {hexes}")
        sizes = [n for n in re.findall(r"(?<![\w-])(\d+(?:\.\d+)?)px", line) if n not in ("0", "1")]
        if sizes:
            problems.append(f"{name}:{i} size {sizes}px")
    assert not problems, "use a token from tokens.css:\n" + "\n".join(problems)


def test_every_token_used_is_defined_and_every_defined_one_is_used():
    defined = set(re.findall(r"(--[\w-]+):", TOKENS + PALETTES))
    css = "".join(RULES.values()) + TOKENS + PALETTES
    used = set(re.findall(r"var\((--[\w-]+)", css)) | set(re.findall(r"""["'](--[\w-]+)["']""", JS))
    # set inline from data (a message swatch, a segmented control's position)
    per_element = {"--swatch", "--n", "--i", "--p", "--led-aspect", "--reveal-x", "--reveal-y"}
    assert not (used - defined - per_element), f"undefined: {sorted(used - defined - per_element)}"
    assert not (defined - used), f"defined but never used: {sorted(defined - used)}"


def test_breakpoints_are_the_listed_ones():
    css = "".join(RULES.values())
    widths = set(re.findall(r"@media \((?:max|min)-width: (\d+px)\)", css))
    assert widths <= BREAKPOINTS, widths - BREAKPOINTS
    assert all(b in TOKENS for b in BREAKPOINTS)


def _luminance(hex_colour):
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _theme(selector):
    start = TOKENS.index(selector)
    block = TOKENS[start : TOKENS.index("}", start)]
    return dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", block))


@pytest.mark.parametrize("selector", [":root {", ':root[data-theme="dark"]'])
def test_text_passes_aa_on_every_surface(selector):
    theme = _theme(selector)
    failing = [
        f"--{fg} on --{bg}: {_contrast(theme[fg], theme[bg]):.2f}"
        for fg in ("text", "text-2", "muted", "faint", "accent-text", "green", "yellow", "red")
        for bg in ("bg", "panel", "field")
        if _contrast(theme[fg], theme[bg]) < 4.5
    ]
    assert not failing, failing
