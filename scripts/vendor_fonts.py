"""Vendor the UI's web fonts (latin subset, woff2) into src/tc002/web/static/fonts/.

The UI is served with a same-origin CSP and must work offline, so fonts cannot load from
Google at runtime. Run again to refresh: `uv run python scripts/vendor_fonts.py`.
Both families are under the SIL Open Font License 1.1; SOURCES.md records where each
file came from.
"""

import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src/tc002/web/static/fonts"
CSS = (
    "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300..600"
    "&family=DM+Mono:wght@400;500&display=swap"
)
# Google serves woff2 with unicode-range subsets only to a modern browser user agent.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Version/17.0 Safari"
BLOCK = re.compile(r"/\* latin \*/\s*@font-face\s*{(.*?)}", re.S)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    css = fetch(CSS).decode()
    rows = []
    for block in BLOCK.findall(css):
        family = re.search(r"font-family: '([^']+)'", block).group(1)
        weight = re.search(r"font-weight: ([\d ]+);", block).group(1)
        url = re.search(r"src: url\(([^)]+)\)", block).group(1)
        name = f"{family.lower().replace(' ', '-')}-{weight.replace(' ', '-')}.woff2"
        (OUT / name).write_bytes(fetch(url))
        rows.append(f"| `{name}` | {family} | {weight} | {url} |")
        print(name)
    (OUT / "SOURCES.md").write_text(
        "# Fonts\n\nLatin subsets from Google Fonts, SIL Open Font License 1.1.\n"
        "Regenerate with `uv run python scripts/vendor_fonts.py`.\n\n"
        "| File | Family | Weight | Source |\n|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )


if __name__ == "__main__":
    main()
